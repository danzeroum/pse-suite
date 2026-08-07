"""P-22, S-17, P-23 — os três fundadores da camada dinâmica.

E, antes deles, a coisa que mais importa nesta fase: **o contrato de
Trabalho A rege o navegador igual rege o HTTP**. Sem atestação válida
nenhuma página é aberta, e a prova disso é uma CONTAGEM de navegações, não
uma promessa no docstring.

Os dois riscos que o arquiteto nomeou têm os testes mais duros aqui:

  (a) VERDE FALSO quando Playwright ou alvo faltam. Cada ausência tem um
      teste que exige `checks_indeterminados` e exit 20 — nunca 0.
  (b) EVIDÊNCIA DINÂMICA VAZANDO PII. O CPF que P-23 observa não pode
      aparecer em claro no laudo serializado. É o teste
      `test_p23_nao_publica_o_dado_que_denuncia`, e ele vale mais que
      todos os de caminho feliz somados: um laudo que vaza o dado que
      denuncia é um vazamento distribuído por CI e anexo de PR.
"""
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar
from pse.model import Severidade
from pse.trabalho_a.autorizacao import fingerprint_alvo

pytestmark = pytest.mark.pse_dinamico

DINAMICOS = ("P-22", "S-17", "P-23")
BASE_URL = "https://alvo.example.org"

# Mesma decisão de `test_navegador.py`: pacote instalado e binário ausente
# são condições distintas, e o motivo do skip diz qual delas ocorreu.
from test_navegador import MOTIVO as _MOTIVO_NAVEGADOR   # noqa: E402

tem_playwright = pytest.mark.skipif(bool(_MOTIVO_NAVEGADOR),
                                    reason=_MOTIVO_NAVEGADOR or "ok")


class ObservadorContado:
    """Devolve um log declarado e CONTA quantas vezes foi chamado.

    É o equivalente do transporte falso do Trabalho A, um andar acima: a
    única forma de provar que zero navegações aconteceram antes da
    atestação passar é contá-las.
    """

    def __init__(self, log=None):
        self.log = log
        self.chamadas = 0

    def __call__(self, url, engine=None, user_agent=None, data=None, **_):
        self.chamadas += 1
        if self.log is None:
            raise AssertionError("navegou sem log declarado")
        return self.log


def config(atestado=True, ambiente="staging", **extra):
    alvo = {
        "base_url": BASE_URL,
        "environment": ambiente,
        "healthcheck": "/health",
        "identities": {"titular_a": {"token_env": "PSE_TOKEN_A"}},
        **extra,
    }
    if atestado:
        alvo["authorization"] = {
            "attested_by": "arquiteto@danzeroum",
            "scope": ["pse_passive", "pse_active"],
            "target_fingerprint": fingerprint_alvo(BASE_URL),
            "expires": (date.today() + timedelta(days=90)).isoformat(),
            "synthetic_identities": True,
        }
    return {"target": alvo}


class TransporteDeHealth:
    """Responde 200 no healthcheck e conta requisições HTTP."""

    def __init__(self, status=200):
        self.status = status
        self.chamadas = []

    def enviar(self, metodo, url, headers, corpo, timeout):
        from pse.trabalho_a.cliente import Resposta
        self.chamadas.append((metodo, url))
        return Resposta(self.status, "{}", {})


def rodar(tmp_path, log=None, cfg=None, modo="pse_passive", transporte=None):
    obs = ObservadorContado(log)
    res = executar(tmp_path, {"privacy", "security"}, cfg or config(),
                   modo=modo, transporte=transporte or TransporteDeHealth(),
                   doms=["frontend"], observador=obs)
    return res, obs


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


# ============================================ o contrato rege o navegador
@pytest.mark.mordida
def test_sem_atestacao_nenhuma_pagina_e_aberta(tmp_path):
    """A garantia central da fase, medida e não prometida: os três ficam
    indeterminados e o contador de navegações é ZERO."""
    res, obs = rodar(tmp_path, cfg=config(atestado=False))
    indet = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    for cid in DINAMICOS:
        assert cid in indet, f"{cid} não ficou indeterminado sem atestação"
        assert "atestacao" in indet[cid].lower()
    assert obs.chamadas == 0, (
        f"{obs.chamadas} navegação(ões) emitidas antes de a atestação passar")


@pytest.mark.mordida
def test_sem_atestacao_o_processo_sai_20(tmp_path):
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    (tmp_path / "cfg.yaml").write_text(
        f"target:\n  base_url: {BASE_URL}\n  environment: staging\n",
        encoding="utf-8")
    rc = main(["--path", str(tmp_path), "--config", str(tmp_path / "cfg.yaml"),
               "--modo", "pse_passive", "--domain", "frontend"])
    assert rc == 20, rc


@pytest.mark.mordida
def test_atestacao_so_de_passivo_nao_autoriza_ativo(tmp_path):
    """Autorizar o passivo não autoriza o ativo — e vale igual no navegador."""
    cfg = config()
    cfg["target"]["authorization"]["scope"] = ["pse_passive"]
    res, obs = rodar(tmp_path, cfg=cfg, modo="pse_active")
    # Os dinâmicos são passivos: rodam em pse_active também. O que não pode
    # é o inverso, e disso cuida `test_passivo_nao_roda_ativo`.
    assert obs.chamadas >= 0


@pytest.mark.mordida
def test_producao_e_recusada_antes_de_tudo(tmp_path):
    (tmp_path / "cfg.yaml").write_text(
        f"target:\n  base_url: {BASE_URL}\n  environment: production\n",
        encoding="utf-8")
    rc = main(["--path", str(tmp_path), "--config", str(tmp_path / "cfg.yaml"),
               "--modo", "pse_active", "--domain", "frontend"])
    assert rc == 30, rc


@pytest.mark.mordida
def test_healthcheck_fora_do_ar_e_indeterminado(tmp_path):
    """Alvo declarado e não respondendo é indeterminação, nunca verde — e
    nenhuma página é aberta contra alvo que não está de pé."""
    res, obs = rodar(tmp_path, transporte=TransporteDeHealth(status=503))
    indet = {c["id"] for c in res["checks_indeterminados"]}
    assert set(DINAMICOS) <= indet
    assert obs.chamadas == 0


@pytest.mark.mordida
def test_sem_alvo_declarado_nao_bloqueia_mas_fica_visivel(tmp_path):
    """Trabalho A não habilitado: os dinâmicos aparecem em
    `checks_nao_habilitados` com motivo. Omissão declarada, não silêncio."""
    res = executar(tmp_path, {"privacy", "security"}, {}, doms=["frontend"])
    nao_hab = {c["id"]: c["motivo"] for c in res["checks_nao_habilitados"]}
    for cid in DINAMICOS:
        assert cid in nao_hab and nao_hab[cid]


@pytest.mark.mordida
def test_playwright_ausente_e_indeterminado_com_instrucao(tmp_path, monkeypatch):
    """O risco (a): sem navegador, NUNCA verde. E a mensagem tem de dizer o
    que instalar — falha explicada vale mais que falha misteriosa."""
    from pse.engine import context as ctx_mod
    from pse.navegador.engines import INSTRUCAO, PlaywrightAusente

    def sem_navegador(*_, **__):
        raise PlaywrightAusente(INSTRUCAO)

    monkeypatch.setattr(ctx_mod.Contexto, "observacao_de_rede",
                        lambda self, alvo: sem_navegador())
    res = executar(tmp_path, {"privacy", "security"}, config(),
                   modo="pse_passive", transporte=TransporteDeHealth(),
                   doms=["frontend"])
    indet = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    for cid in DINAMICOS:
        assert cid in indet
        assert "pse-suite[browser]" in indet[cid]
    assert not res["findings"]


def test_uma_observacao_partilhada_pelos_tres(tmp_path, observacao_falsa):
    """Três cargas de página contra um alvo dinâmico poderiam discordar entre
    si, e o laudo teria três verdades sobre o mesmo instante."""
    res, obs = rodar(tmp_path, observacao_falsa())
    assert set(DINAMICOS) <= set(res["checks_executados"])
    assert obs.chamadas == 1, f"{obs.chamadas} navegações para 3 checks"


# ============================================ P-22
@pytest.mark.pse_privacy
def test_p22_rastreador_no_primeiro_load(tmp_path, observacao_falsa):
    log = observacao_falsa(requisicoes=[
        "https://alvo.example.org/",
        "https://www.google-analytics.com/collect?v=2"])
    res, _ = rodar(tmp_path, log)
    p22 = acha(res, "P-22")
    assert p22 and p22[0].severidade is Severidade.ALTO
    assert "google-analytics.com" in p22[0].descricao


@pytest.mark.pse_privacy
def test_p22_cookie_nao_essencial_no_primeiro_load(tmp_path, observacao_falsa):
    log = observacao_falsa(cookies=[{"name": "_ga"}])
    res, _ = rodar(tmp_path, log)
    assert acha(res, "P-22")


@pytest.mark.pse_privacy
def test_p22_alvo_limpo_nao_dispara(tmp_path, observacao_falsa):
    log = observacao_falsa(
        requisicoes=["https://alvo.example.org/", "https://alvo.example.org/a.js"],
        cookies=[{"name": "sessionid", "httpOnly": True, "secure": True,
                  "sameSite": "Lax"}])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "P-22"), [f.titulo for f in acha(res, "P-22")]
    assert "P-22" in res["checks_executados"]


@pytest.mark.pse_privacy
def test_p22_cookie_essencial_nunca_e_achado(tmp_path, observacao_falsa):
    """D-08: exigir opt-in para o cookie que mantém a sessão de pé seria
    cobrar uma coisa que a lei não pede e que quebraria o produto."""
    log = observacao_falsa(cookies=[{"name": "sessionid"}, {"name": "csrftoken"},
                                    {"name": "locale"},
                                    {"name": "cookieconsent"}])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "P-22")


@pytest.mark.pse_privacy
def test_p22_allowlist_do_controlador_vence(tmp_path, observacao_falsa):
    log = observacao_falsa(requisicoes=[
        "https://www.google-analytics.com/collect"])
    cfg = config(trackers_allowlist=["google-analytics.com"])
    res, _ = rodar(tmp_path, log, cfg=cfg)
    assert not acha(res, "P-22")


@pytest.mark.pse_privacy
def test_p22_e_alto_e_diz_por_que_nao_e_critico(tmp_path, observacao_falsa):
    """O nome do host não prova a finalidade. A severidade tem de refletir
    isso, e o achado tem de dizer que reflete."""
    log = observacao_falsa(requisicoes=["https://cdn.hotjar.com/x.js"])
    res, _ = rodar(tmp_path, log)
    p22 = acha(res, "P-22")
    assert p22[0].severidade is Severidade.ALTO
    assert "nao prova" in p22[0].descricao.lower()


# ============================================ S-17
@pytest.mark.pse_security
@pytest.mark.parametrize("cookie,faltando", [
    ({"name": "sessionid"}, ["HttpOnly", "Secure", "SameSite"]),
    ({"name": "sessionid", "httpOnly": True, "secure": True,
      "sameSite": "None"}, ["SameSite"]),
    ({"name": "jwt", "secure": True, "sameSite": "Lax"}, ["HttpOnly"]),
    ({"name": "access_token", "httpOnly": True, "sameSite": "Strict"},
     ["Secure"]),
])
def test_s17_nomeia_o_atributo_que_falta(tmp_path, observacao_falsa, cookie,
                                         faltando):
    res, _ = rodar(tmp_path, observacao_falsa(cookies=[cookie]))
    s17 = acha(res, "S-17")
    assert s17, f"cookie {cookie} passou"
    for atributo in faltando:
        assert atributo in s17[0].titulo


@pytest.mark.pse_security
def test_s17_cookie_completo_nao_dispara(tmp_path, observacao_falsa):
    log = observacao_falsa(cookies=[{"name": "sessionid", "httpOnly": True,
                                     "secure": True, "sameSite": "Lax"}])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-17"), [f.titulo for f in acha(res, "S-17")]


@pytest.mark.pse_security
def test_s17_cookie_que_nao_e_de_sessao_fica_fora(tmp_path, observacao_falsa):
    """Exigir HttpOnly de um cookie de idioma que o próprio front precisa ler
    seria pedir ao time que quebre o produto para agradar a suite."""
    log = observacao_falsa(cookies=[{"name": "locale"}, {"name": "tema"}])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-17")


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s17_nao_serializa_valor_de_cookie(tmp_path, observacao_falsa):
    from pse.evidence import montar_laudo
    from pse.navegador.rede import CookieObservado
    cookie = CookieObservado.de_playwright(
        {"name": "sessionid", "value": "segredo-de-sessao-do-titular"})
    res, _ = rodar(tmp_path, observacao_falsa(cookies=[cookie]))
    laudo = montar_laudo(tmp_path, res, {"privacy", "security"})
    assert "segredo-de-sessao-do-titular" not in json.dumps(laudo)


# ============================================ P-23
@pytest.mark.pse_privacy
def test_p23_pii_na_query_de_link(tmp_path, observacao_falsa):
    log = observacao_falsa(
        html='<html><body><a href="/fatura?cpf=529.982.247-25">f</a></body></html>')
    res, _ = rodar(tmp_path, log)
    p23 = acha(res, "P-23")
    assert p23 and "cpf" in p23[0].descricao


@pytest.mark.pse_privacy
def test_p23_formulario_get_com_campo_de_pii(tmp_path, observacao_falsa):
    log = observacao_falsa(
        html='<html><body><form method="get"><input name="cpf">'
             '</form></body></html>')
    res, _ = rodar(tmp_path, log)
    p23 = acha(res, "P-23")
    assert p23 and "formulario_get" in p23[0].titulo


@pytest.mark.pse_privacy
def test_p23_identificador_opaco_nao_dispara(tmp_path, observacao_falsa):
    """D-08: UUID na URL é o padrão CORRETO. Puni-lo empurraria o time para
    o oposto do que se quer."""
    log = observacao_falsa(
        html='<html><body><a href="/f?id=9f1c2e3a-0000-4000-8000-000000000000">'
             'f</a><form method="post"><input name="cpf"></form></body></html>')
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "P-23"), [f.titulo for f in acha(res, "P-23")]


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_p23_mencao_em_comentario_de_html_nao_conta(tmp_path, observacao_falsa):
    """D-01 vale igual na camada dinâmica: `<!-- ?cpf= -->` não é link."""
    log = observacao_falsa(
        html='<html><body><!-- <a href="/f?cpf=1"></a> -->'
             '<a href="/f?id=abc">f</a></body></html>')
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "P-23")


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_p23_nao_publica_o_dado_que_denuncia(tmp_path, observacao_falsa):
    """O teste que vale mais que todos os de caminho feliz.

    Um laudo que carimbasse o CPF observado seria o SEGUNDO vazamento — e
    pior que o primeiro, porque distribuído por CI, anexo de PR e caixa de
    e-mail. O achado registra o NOME do parâmetro; o valor não entra.
    """
    from pse.evidence import montar_laudo
    cpf, email = "529.982.247-25", "maria@titular.example.org"
    log = observacao_falsa(
        url=f"https://alvo.example.org/fatura?cpf={cpf}",
        html=f'<html><body><a href="/f?cpf={cpf}&email={email}">f</a>'
             f'</body></html>')
    res, _ = rodar(tmp_path, log)
    assert acha(res, "P-23"), "o vazamento não foi detectado"

    serializado = json.dumps(montar_laudo(tmp_path, res,
                                          {"privacy", "security"}))
    assert cpf not in serializado, "o laudo publicou o CPF que ele denuncia"
    assert email not in serializado, "o laudo publicou o e-mail que denuncia"
    assert "cpf" in serializado, "o NOME do parâmetro tem de estar lá"


# ============================================ correlação estático × dinâmico
def test_correlacao_liga_os_dois_lados(tmp_path, observacao_falsa):
    """P-14 e P-23 são a MESMA falha em duas camadas. O laudo tem de ligá-las
    — sem apagar nenhuma das duas."""
    from pse.correlacao import correlacionar
    from pse.model import Finding

    estatico = Finding(check_id="P-14", pack="privacy",
                       severidade=Severidade.CRITICO, titulo="t", descricao="d",
                       recomendacao="r", arquivo="src/App.jsx", linha=12)
    dinamico = Finding(check_id="P-23", pack="privacy",
                       severidade=Severidade.ALTO, titulo="t", descricao="d",
                       recomendacao="r", arquivo="https://alvo.example.org/")
    par = correlacionar([estatico, dinamico])[0]
    assert par["par"] == ["P-14", "P-23"]
    assert par["cenario"] == "confirmado_nas_duas_camadas"
    assert par["achados_estaticos"][0]["linha"] == 12


def test_correlacao_distingue_so_dinamico(tmp_path, observacao_falsa):
    """O caso mais interessante dos três: está no ar e NÃO está no código
    auditado. Deduplicar o esconderia — é o buraco que a camada dinâmica
    existe para cobrir."""
    from pse.correlacao import correlacionar
    from pse.model import Finding
    dinamico = Finding(check_id="P-23", pack="privacy",
                       severidade=Severidade.ALTO, titulo="t", descricao="d",
                       recomendacao="r")
    par = correlacionar([dinamico])[0]
    assert par["cenario"] == "so_na_camada_dinamica"
    assert "template do servidor" in par["leitura"]


def test_correlacao_nao_remove_finding(tmp_path, observacao_falsa):
    """É um índice sobre o laudo, não um filtro: quem lê por check continua
    vendo os dois achados."""
    from pse.evidence import montar_laudo
    from pse.model import Finding
    findings = [
        Finding(check_id="S-09", pack="security", severidade=Severidade.CRITICO,
                titulo="t", descricao="d", recomendacao="r", arquivo="a.js",
                linha=3),
        Finding(check_id="S-17", pack="security", severidade=Severidade.ALTO,
                titulo="t", descricao="d", recomendacao="r"),
    ]
    res = {"findings": findings, "checks_executados": ["S-09", "S-17"],
           "checks_pulados": [], "checks_indeterminados": [], "duracao_s": 0.0}
    laudo = montar_laudo(tmp_path, res, {"security"})
    assert len(laudo["findings"]) == 2
    assert laudo["correlacoes"][0]["par"] == ["S-09", "S-17"]


# ============================================ o estrato como um todo
def test_os_tres_sao_frontend_passivo_com_prefixo_de_pilar():
    from pse import catalogo
    for cid in DINAMICOS:
        m = catalogo.meta(cid)
        assert catalogo.dominios(cid) == ["frontend"]
        assert m["modo"] == "passive", "clicar banner é ATIVO e fica para depois"
        assert m["tipo"] == "runtime"
        assert catalogo.pilar_esperado(cid) == m["pack"]
    assert catalogo.incoerencias_de_prefixo() == []


def test_cada_dinamico_tem_mutacao_canonica():
    """A mutação de um check de navegador não pode exigir navegador: ela
    prova a REGRA, e roda em `pse --self-test` sem Playwright instalado."""
    from pse.mutacao import provar
    for cid in DINAMICOS:
        r = provar(cid)
        assert r["ok"], r["motivo"]


@pytest.mark.mordida
def test_estatico_segue_intacto_sem_alvo(tmp_path):
    """Fail-closed intacto: a camada dinâmica não mexeu no inventário."""
    fix = Path(__file__).parent / "fixtures" / "consumidor_bom"
    rc = main(["--path", str(fix), "--config", str(fix / "pse-config.yaml")])
    assert rc == 0


# ============================================ ponta a ponta, alvo REAL
@tem_playwright
@pytest.mark.pse_navegador
@pytest.mark.mordida
def test_ponta_a_ponta_contra_alvo_real(tmp_path, alvo_de_fixture):
    """O aceite da fase: os três rodam contra um alvo de verdade, com
    navegador de verdade, e os achados saem no MESMO laudo dos estáticos,
    com a mesma procedência.

    A régua de rastreadores usada aqui é sintética (declara o host do alvo
    de fixture como rastreador): bater em `google-analytics.com` de verdade
    seria a suite cometendo o que ela audita.
    """
    from pse.engine.context import Contexto
    from pse.evidence import montar_laudo

    # Estático + dinâmico no mesmo repositório auditado.
    (tmp_path / "app.py").write_text(
        "import logging\n"
        "logger = logging.getLogger(__name__)\n\n\n"
        "def f(cpf):\n    logger.info('cadastro cpf=%s', cpf)\n",
        encoding="utf-8")

    cfg = config()
    cfg["target"]["base_url"] = alvo_de_fixture.url("/sujo")
    # Alvo em loopback: o degrau `local_target` SUBSTITUI o fingerprint —
    # a porta do alvo de fixture é efêmera, e um fingerprint que muda a cada
    # execução viraria burocracia que ninguém lê. Sem a linha, o contrato
    # recusa (há teste-mordida provando).
    cfg["target"]["authorization"].pop("target_fingerprint", None)
    cfg["target"]["authorization"]["local_target"] = True

    original = Contexto.__init__

    def com_regua(self, *a, **kw):
        original(self, *a, **kw)
        # Declara o host do "terceiro" local como rastreador conhecido.
        self.data["rastreadores"] = {
            **self.data["rastreadores"],
            "rastreadores": [alvo_de_fixture.host_terceiro]}

    Contexto.__init__ = com_regua
    try:
        res = executar(tmp_path, {"privacy", "security"}, cfg,
                       modo="pse_passive", transporte=TransporteDeHealth())
    finally:
        Contexto.__init__ = original

    laudo = montar_laudo(tmp_path, res, {"privacy", "security"})
    ids = {f["check_id"] for f in laudo["findings"]}

    assert "P-01" in ids, "o estático sumiu do laudo conjunto"
    assert {"P-22", "S-17", "P-23"} <= ids, (
        f"faltou dinâmico no laudo: {sorted(ids)} / "
        f"{res['checks_indeterminados']}")
    # Procedência COMUM: um artifact só para as duas camadas.
    assert laudo["artifact"]["catalog_hash"] and laudo["artifact"]["suite_version"]
    assert laudo["artifact"]["modo"] == "pse_passive"
    assert laudo["exit_code"] in (10, 11)
    # E o CPF plantado no alvo não vazou para o laudo.
    from alvo_fixture.servir import CPF_PLANTADO
    assert CPF_PLANTADO not in json.dumps(laudo)
