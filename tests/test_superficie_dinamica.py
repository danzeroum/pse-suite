"""A camada dinamica observa UMA superficie, e o laudo tem de dizer qual.

O btv serve DUAS SPAs na mesma origem — o produto na raiz e um console de
desenvolvedor em `/dev` (confirmado no `infra/docker/Dockerfile`: dois
estagios de build, `BTV_WEB_DIR` e `BTV_DEV_WEB_DIR`, e
`router.nest_service("/dev", svc)` no `btv-server`).

Todas as medicoes dinamicas carregaram a RAIZ. O console nunca foi
observado, e o laudo nao registrava esse silencio: os sete checks dinamicos
afirmavam algo sobre uma superficie e nada sobre a outra, sem distinguir as
duas. E o mesmo verde falso que o bloco `alcance` impede no estatico, uma
camada acima.

E um segundo problema que a medicao das duas superficies expos: o que a
camada dinamica ve depende inteiramente de QUEM serviu. Um dev server
entrega modulo sem minificar, com sourcemap embutido e sem cabecalho de
borda — comportamento normal do modo, e nao propriedade do artefato
publicado.
"""
import tempfile
from pathlib import Path

import pytest

from pse.engine.context import Contexto
from pse.navegador import analise
from pse.navegador.rede import NetworkLog, RecursoObservado, RequisicaoObservada

MARCAS = ("/@vite/client", "/@react-refresh", "node_modules/.vite/",
          "__webpack_hmr", "hot-update.js")


def _log(url, urls_de_recurso=()):
    req = tuple(RequisicaoObservada(url=u) for u in (url,) + tuple(urls_de_recurso))
    rec = tuple(RecursoObservado(url=u, status=200, da_origem=True)
                for u in (url,) + tuple(urls_de_recurso))
    return NetworkLog(url=url, requisicoes=req, recursos=rec, engine="chromium")


# ======================================= a superficie observada e NOMEADA
def test_o_laudo_nomeia_a_superficie_observada():
    """Medir uma rota e calar sobre as outras e meia cobertura apresentada
    como inteira."""
    d = _log("http://127.0.0.1:5178/").sanitizado(MARCAS)
    assert d["superficie_observada"]
    assert "5178" in d["superficie_observada"]
    assert "Nenhuma outra" in d["nota_de_superficie"]
    assert "base_url" in d["nota_de_superficie"]


def test_duas_superficies_produzem_dois_relatorios_distintos():
    """Raiz e `/dev` sao SPAs diferentes na mesma origem. Um relatorio que
    nao as distinguisse deixaria o leitor somar as duas."""
    raiz = _log("http://127.0.0.1:5178/").sanitizado(MARCAS)
    dev = _log("http://127.0.0.1:5178/dev").sanitizado(MARCAS)
    assert raiz["superficie_observada"] != dev["superficie_observada"]


# ================================= quem serviu muda o que se pode afirmar
def test_dev_server_e_declarado_com_indicios():
    """`/@vite/client` e `node_modules/.vite/` nao sao o bundle entregue: sao
    encanamento do modo de desenvolvimento."""
    d = _log("http://127.0.0.1:5179/",
             ["http://127.0.0.1:5179/@vite/client",
              "http://127.0.0.1:5179/node_modules/.vite/deps/react.js"]
             ).sanitizado(MARCAS)
    assert d["servidor_de_desenvolvimento"] is True
    assert "/@vite/client" in d["indicios_de_dev_server"]
    assert "node_modules/.vite/" in d["indicios_de_dev_server"]
    assert "producao" in d["nota_de_dev_server"]


def test_servidor_comum_nao_e_marcado_como_dev():
    """A mordida: se tudo virasse 'dev server', a qualificacao nao
    qualificaria nada."""
    d = _log("https://app.exemplo.test/",
             ["https://app.exemplo.test/assets/main-a1b2.js"]).sanitizado(MARCAS)
    assert d["servidor_de_desenvolvimento"] is False
    assert "indicios_de_dev_server" not in d


def test_sem_regua_nao_inventa_qualificacao():
    """Chamada sem marcas nao pode AFIRMAR que nao e dev server por
    omissao — mas tambem nao pode quebrar. Devolve o campo em False, que e o
    que a suite consegue dizer sem a regua."""
    d = _log("http://127.0.0.1:5179/",
             ["http://127.0.0.1:5179/@vite/client"]).sanitizado()
    assert d["servidor_de_desenvolvimento"] is False


def test_a_marca_e_de_CAMINHO_e_nao_de_cabecalho():
    """`X-Powered-By` some atras de proxy; o caminho do modulo nao."""
    log = _log("http://x/", ["http://x/src/main.tsx"])
    assert log.indicios_de_dev_server(MARCAS) == []
    log2 = _log("http://x/", ["http://x/@vite/client?t=1"])
    assert log2.indicios_de_dev_server(MARCAS) == ["/@vite/client"]


# ================================ a qualificacao chega ao laudo de verdade
def test_todos_os_checks_dinamicos_usam_o_relator_qualificado():
    """Esquecer a regua num dos sete produziria um laudo que diz a verdade
    em seis relatorios e cala no setimo — e qual apareceria dependeria da
    ordem de execucao."""
    raiz = Path(__file__).resolve().parent.parent / "pse" / "checks"
    faltando = []
    for p in raiz.rglob("*.py"):
        texto = p.read_text(encoding="utf-8")
        if 'ctx.relatorio("observacao_de_rede"' in texto:
            faltando.append(p.name)
    assert not faltando, (
        f"check(s) montando `observacao_de_rede` a mao em vez de usar "
        f"`analise.relatar_observacao`: {faltando}")


def test_o_relator_le_a_regua_do_contexto(tmp_path):
    """D-13: as marcas moram em `pse/data/`, nunca no `.py` do check."""
    ctx = Contexto(tmp_path)
    assert ctx.data["servido-ao-cliente"]["marcas_de_dev_server"]
    analise.relatar_observacao(
        ctx, _log("http://127.0.0.1:5179/",
                  ["http://127.0.0.1:5179/@vite/client"]))
    rel = ctx.relatorios["observacao_de_rede"]
    assert rel["servidor_de_desenvolvimento"] is True
    assert rel["superficie_observada"]


def test_a_regua_de_dev_server_cobre_os_bundlers_correntes(tmp_path):
    marcas = {str(m).lower()
              for m in Contexto(tmp_path).data["servido-ao-cliente"]
              ["marcas_de_dev_server"]}
    for esperado in ("/@vite/client", "node_modules/.vite/", "__webpack_hmr",
                     "hot-update.js"):
        assert esperado in marcas, (
            f"marca `{esperado}` removida da regua: o laudo volta a nao "
            f"distinguir dev server de producao, em silencio")


def test_a_url_da_superficie_passa_pelo_sanitizador():
    """A superficie observada e uma URL, e URL carrega PII em query string.
    Vale a mesma regra do resto da evidencia dinamica."""
    d = _log("https://app.exemplo.test/busca?cpf=12345678901").sanitizado(MARCAS)
    assert "12345678901" not in d["superficie_observada"]
    assert "cpf" in d["superficie_observada"]


# =========================================================================
# ARTEFATO DECLARADO x ARTEFATO OBSERVADO
#
# A licao que a medicao de producao fechou: dev server e producao sao alvos
# DIFERENTES, e os achados de um nao valem para o outro. Contra o btv real:
#
#   S-21 sourcemap    dev 107 e 84  ->  producao 0 e 0   (era andaime)
#   S-19 cabecalhos   dev ALTO      ->  producao ALTO    (era real)
#   requisicoes       dev 119 e 93  ->  producao 7 e 4
#
# Sem a distincao, os dois achados teriam o mesmo peso — e um deles nao
# existia.
# =========================================================================

def test_declarado_e_observado_sao_campos_SEPARADOS():
    """A suite NAO consegue descobrir sozinha se mediu producao: um `vite
    preview` e um deploy real servem bundle igualmente minificado. O que ela
    sabe e o que OBSERVOU; o resto e declaracao do operador."""
    d = _log("https://app.exemplo.test/").sanitizado(MARCAS, "producao")
    assert d["artefato_declarado"] == "producao"
    assert d["servidor_de_desenvolvimento"] is False


def test_producao_declarada_com_indicio_de_dev_e_CONTRADICAO():
    """A trava. Quem apontou a atestacao de producao para um `vite dev`
    precisa saber ANTES de ler os achados como propriedade do artefato."""
    d = _log("http://127.0.0.1:5178/",
             ["http://127.0.0.1:5178/@vite/client"]).sanitizado(
                 MARCAS, "producao")
    assert "contradicao_de_artefato" in d
    assert "/@vite/client" in d["contradicao_de_artefato"]
    assert d["servidor_de_desenvolvimento"] is True


def test_sem_contradicao_a_nota_de_producao_nao_promete_o_que_nao_viu():
    """Declarar producao e nao ver indicio contrario NAO e verificar a
    declaracao. O que ficou fora da observacao (ingress, proxy, WAF, CDN)
    segue sem ser observado."""
    d = _log("https://app.exemplo.test/").sanitizado(MARCAS, "producao")
    assert "contradicao_de_artefato" not in d
    assert "NAO verifica a declaracao" in d["nota_de_producao"]
    assert "ingress" in d["nota_de_producao"]


def test_sem_declaracao_o_laudo_nao_infere_producao():
    """Inferir `producao` da ausencia de indicio seria a suite inventando um
    fato sobre o alvo — o oposto do que este bloco existe para fazer."""
    d = _log("https://app.exemplo.test/").sanitizado(MARCAS)
    assert d["artefato_declarado"] == "nao_declarado"
    assert "nota_de_artefato" in d
    assert "nao afirma" in d["nota_de_artefato"]


def test_desenvolvimento_declarado_nao_produz_contradicao():
    """Declarar o que se esta medindo e o caso honesto, e ele nao pode ser
    punido: dev declarado + dev observado e coerencia, nao conflito."""
    d = _log("http://127.0.0.1:5178/",
             ["http://127.0.0.1:5178/@vite/client"]).sanitizado(
                 MARCAS, "desenvolvimento")
    assert "contradicao_de_artefato" not in d
    assert d["artefato_declarado"] == "desenvolvimento"
    assert d["servidor_de_desenvolvimento"] is True


# ------------------------------------------- o valor declarado e fechado
def test_artefato_desconhecido_e_entrada_invalida():
    """Um typo (`prod`, `producao ` com espaco) que passasse silenciosamente
    faria o laudo dizer `artefato_declarado: prod` e ninguem cruzaria nada —
    a declaracao viraria decoracao."""
    from pse.model import EntradaInvalida
    from pse.trabalho_a.autorizacao import validar_config
    for ruim in ("prod", "production", "dev", "", "producao!"):
        with pytest.raises(EntradaInvalida) as e:
            validar_config({"target": {"base_url": "https://a.test",
                                       "environment": "staging",
                                       "artefato": ruim}}, "pse_passive")
        assert "artefato" in str(e.value), ruim


def test_os_dois_valores_aceitos_passam():
    from pse.trabalho_a.autorizacao import ARTEFATOS, validar_config
    assert set(ARTEFATOS) == {"producao", "desenvolvimento"}
    for bom in ARTEFATOS:
        validar_config({"target": {
            "base_url": "https://a.test", "environment": "staging",
            "artefato": bom,
            "authorization": {"attested_by": "dono@exemplo.test",
                              "scope": ["pse_passive"],
                              "expires": "2030-01-01"}}}, "pse_passive")


def test_ausencia_de_artefato_continua_valida():
    """Campo NOVO e OPCIONAL: config existente nao pode quebrar."""
    from pse.trabalho_a.autorizacao import validar_config
    validar_config({"target": {
        "base_url": "https://a.test", "environment": "staging",
        "authorization": {"attested_by": "dono@exemplo.test",
                          "scope": ["pse_passive"],
                          "expires": "2030-01-01"}}}, "pse_passive")


def test_o_relator_propaga_a_declaracao_do_alvo(tmp_path):
    ctx = Contexto(tmp_path, config={"target": {"artefato": "producao"}})
    analise.relatar_observacao(ctx, _log("https://app.exemplo.test/"))
    assert ctx.relatorios["observacao_de_rede"]["artefato_declarado"] == "producao"
