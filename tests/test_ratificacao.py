"""As quinze ratificações, seladas pelo COMPORTAMENTO e não pela prosa.

`docs/RATIFICACOES.md` afirma que quinze decisões de contrato estão fechadas.
Uma tabela que afirma isso e não é verificada é pior que tabela nenhuma: ela
parece autoridade. Cada linha daquele documento tem aqui o teste que a torna
verdadeira — se o comportamento mudar, a linha vira falsa e este arquivo
reprova.

Nenhum destes testes é novo em substância: os comportamentos já tinham
prova nos módulos de origem. O que muda é o ENDEREÇO — a partir daqui, quem
quiser saber o que foi ratificado lê um documento e roda um arquivo.
"""
import re
import tempfile
from pathlib import Path

import pytest

from pse import catalogo
from pse.checks import _credencial
from pse.engine import scan
from pse.engine.context import Contexto
from pse.engine.runner import executar
from pse.model import CheckIndeterminado, Severidade
from pse.trabalho_a.autorizacao import e_loopback, host_e_loopback

RAIZ = Path(__file__).resolve().parent.parent
LEDGER = RAIZ / "docs" / "RATIFICACOES.md"
CATALOGO_CIFRADO = (
    "tables:\n  t:\n    fields:\n      cpf:\n        class: sensitive\n"
    "        encryption:\n          algorithm: aes-256-gcm\n"
    "          key_management: aws-kms\n")


def escrever(arquivos, cfg=None):
    d = Path(tempfile.mkdtemp())
    for nome, corpo in arquivos.items():
        alvo = d / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return executar(d, {"privacy", "security"}, cfg or {})


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


# ------------------------------------------------------------ 1 e 2
def test_r02_loopback_casa_host_exato_nunca_substring():
    """Ratificação 2. `http://` só é aceito com host de loopback EXATO."""
    for bom in ("http://127.0.0.1:5178/", "http://localhost:8000/",
                "http://[::1]:9000/"):
        assert e_loopback(bom), bom
    for mau in ("http://127.0.0.1.atacante.com/", "http://localhost.evil.io/",
                "https://api.exemplo.com/"):
        assert not e_loopback(mau), mau


def test_r02_o_host_de_loopback_independe_do_esquema():
    assert host_e_loopback("https://127.0.0.1:8443/")
    assert not host_e_loopback("https://127.0.0.1.exemplo.com/")


def _config(base_url, **auth):
    att = {"attested_by": "dono@exemplo.test", "scope": ["pse_passive"],
           "expires": "2030-01-01"}
    att.update(auth)
    return {"target": {"base_url": base_url, "environment": "staging",
                       "authorization": att}}


def test_r01_local_target_e_exigido_em_loopback():
    """Ratificação 1. Sem o degrau, loopback é indeterminado — nunca uma
    porta aberta sem registro."""
    from pse.trabalho_a.autorizacao import validar_atestacao
    with pytest.raises(CheckIndeterminado) as e:
        validar_atestacao(_config("http://127.0.0.1:7878"), "pse_passive")
    assert "local_target" in str(e.value)


def test_r01_local_target_em_alvo_publicado_e_entrada_invalida():
    from pse.model import EntradaInvalida
    from pse.trabalho_a.autorizacao import validar_config
    with pytest.raises(EntradaInvalida):
        validar_config(_config("https://app.exemplo.com", local_target=True),
                       "pse_passive")


def test_r01_loopback_COM_o_degrau_passa():
    """A mordida: se o degrau não abrisse caminho nenhum, ele seria só um
    bloqueio, e a camada dinâmica não teria como rodar contra alvo local."""
    from pse.trabalho_a.autorizacao import validar_atestacao
    validar_atestacao(_config("http://127.0.0.1:7878", local_target=True),
                      "pse_passive")


# ------------------------------------------------------------ 3 e 4
def test_r03_p24_e_do_pilar_privacy():
    from pse import catalogo
    assert catalogo.CATALOGO["P-24"]["pack"] == "privacy"


def test_r04_s14_e_s15_permanecem_alto():
    """Ratificação 4. `CRÍTICO` fica reservado ao que já é exposição
    consumada; dump entre ambientes e GRANT amplo são graves e não são
    isso."""
    from pathlib import Path as _P
    for arq in ("s14_dump_de_producao.py", "s15_grant_excessivo.py"):
        fonte = (RAIZ / "pse" / "checks" / "security" / arq).read_text(
            encoding="utf-8")
        assert "Severidade.CRITICO" not in fonte, arq
        assert "Severidade.ALTO" in fonte, arq


# ------------------------------------------------------------ 5 e 6
def test_r05_env_bang_bloqueia_e_env_var_decide():
    ind = escrever({"src/a.rs": 'fn f() { let api_key = env!("K"); }\n'})
    assert "S-06" in {c["id"] for c in ind["checks_indeterminados"]}
    assert not acha(ind, "S-06")

    ok = escrever({"src/a.rs":
                   'fn f() { let api_key = std::env::var("K").unwrap(); }\n'})
    assert "S-06" not in {c["id"] for c in ok["checks_indeterminados"]}
    assert not acha(ok, "S-06")


def test_r06_critico_textual_so_com_formato_conhecido():
    conhecido = escrever({"src/a.rs":
                          'fn f() { let api_key = "AKIAQ4F7X2VNBM3JZR5T"; }\n'})
    assert any(f.severidade == Severidade.CRITICO
               for f in acha(conhecido, "S-06"))

    desconhecido = escrever({"src/a.rs": 'fn f() { let api_secret = "'
                             + "9f3b" * 12 + '"; }\n'})
    achados = acha(desconhecido, "S-06")
    assert achados and all(f.severidade == Severidade.ALTO for f in achados)


# ------------------------------------------------------------ 7
def test_r07_embrulho_de_cifra_opaco_bloqueia():
    res = escrever({
        "catalog.yaml": CATALOGO_CIFRADO,
        "src/a.rs": 'fn to_ciphertext(v: &str) -> Vec<u8> { v.as_bytes().to_vec() }\n'
                    'fn g(p: &PgPool, t: &Titular) {\n'
                    '    let blob = to_ciphertext(&t.cpf);\n'
                    '    sqlx::query("INSERT INTO t (cpf) VALUES ($1)")'
                    '.bind(&blob).execute(p);\n}\n'},
        cfg={"catalog_path": "catalog.yaml"})
    assert "P-18" in {c["id"] for c in res["checks_indeterminados"]}
    assert not acha(res, "P-18")


# ------------------------------------------------------------ 8
def test_r08_achado_e_indeterminacao_coexistem():
    res = escrever({
        "src/quebrado.ts": "export const x = <<<>>> ;;;\n",
        "src/Tela.tsx": "export function T({ cpf }: { cpf: string }) {\n"
                        "  localStorage.setItem('cpf', cpf);\n"
                        "  return <div/>;\n}\n"})
    assert acha(res, "P-14"), "o achado do arquivo legível se perdeu"
    assert "P-14" in {c["id"] for c in res["checks_indeterminados"]}


def test_r08_a_excecao_carrega_os_achados():
    assert CheckIndeterminado("x").achados == []
    assert CheckIndeterminado("y", achados=[1]).achados == [1]


# ------------------------------------------------------------ 9
def test_r09_a_observacao_declara_superficie_e_quem_serviu():
    from pse.navegador.rede import NetworkLog, RecursoObservado
    marcas = ("/@vite/client",)
    log = NetworkLog(url="http://127.0.0.1:5179/", engine="chromium",
                     recursos=(RecursoObservado(
                         url="http://127.0.0.1:5179/@vite/client", status=200),))
    d = log.sanitizado(marcas)
    assert d["superficie_observada"]
    assert d["servidor_de_desenvolvimento"] is True


# ------------------------------------------------------------ 10
def test_r10_declarado_e_observado_sao_campos_separados():
    """Ratificação 10. A suíte NÃO descobre sozinha contra que artefato mede."""
    from pse.navegador.rede import NetworkLog, RecursoObservado
    limpo = NetworkLog(url="https://app.exemplo.test/", engine="chromium")
    d = limpo.sanitizado(("/@vite/client",), "producao")
    assert d["artefato_declarado"] == "producao"
    assert d["servidor_de_desenvolvimento"] is False
    assert "contradicao_de_artefato" not in d


def test_r10_producao_declarada_sobre_dev_observado_e_contradicao():
    from pse.navegador.rede import NetworkLog, RecursoObservado
    log = NetworkLog(url="http://127.0.0.1:5178/", engine="chromium",
                     recursos=(RecursoObservado(
                         url="http://127.0.0.1:5178/@vite/client", status=200),))
    assert "contradicao_de_artefato" in log.sanitizado(("/@vite/client",),
                                                       "producao")


def test_r10_valor_fora_da_lista_e_exit_30():
    from pse.model import EntradaInvalida
    from pse.trabalho_a.autorizacao import validar_config
    with pytest.raises(EntradaInvalida):
        validar_config({"target": {"base_url": "https://a.test",
                                   "environment": "staging",
                                   "artefato": "prod"}}, "pse_passive")


def test_r10_nada_declarado_nao_vira_producao_por_inferencia():
    from pse.navegador.rede import NetworkLog
    d = NetworkLog(url="https://app.exemplo.test/",
                   engine="chromium").sanitizado(("/@vite/client",))
    assert d["artefato_declarado"] == "nao_declarado"


# ------------------------------------------ o documento e o código não divergem
def _linhas_numeradas():
    texto = LEDGER.read_text(encoding="utf-8")
    return [l for l in texto.splitlines()
            if l.startswith("| ") and l.split("|")[1].strip().isdigit()]


def test_o_ledger_lista_exatamente_as_quinze():
    tabela = _linhas_numeradas()
    assert len(tabela) == 15, f"o ledger tem {len(tabela)} linhas numeradas"
    numeros = [int(l.split("|")[1].strip()) for l in tabela]
    assert numeros == list(range(1, 16)), numeros


def test_toda_linha_do_ledger_tem_teste_que_a_sela():
    """A tabela é uma promessa até que cada linha tenha comportamento
    provado. Linha nova sem teste torna o documento propaganda."""
    fonte = Path(__file__).read_text(encoding="utf-8")
    for linha in _linhas_numeradas():
        n = int(linha.split("|")[1].strip())
        assert re.search(rf"^def test_r0?{n}_", fonte, re.M), (
            f"ratificação {n} não tem teste que a sele")


def test_cada_ratificacao_nomeia_a_versao_de_origem():
    """Ratificação sem versão de origem perde a rastreabilidade: não se sabe
    o que estava em jogo quando a decisão foi tomada."""
    import re
    texto = LEDGER.read_text(encoding="utf-8")
    tabela = [l for l in texto.splitlines()
              if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
    for linha in tabela:
        assert re.search(r"v0\.\d+\.\d+", linha), linha


def test_o_ledger_nao_apaga_a_pendencia_do_manifesto():
    """Manifesto é o registro do que se sabia naquele momento. Apagar dele a
    seção de pendências — para "não repetir" o que o ledger já diz —
    falsificaria a história que ele existe para guardar.

    (O manifesto PODE conter a palavra "ratificado" em outros contextos: a
    v0.11.0 fala de `CONTRATO RATIFICADO` sobre outra coisa. O que se vigia
    é a seção, não a palavra.)
    """
    com_secao = [m.name for m in RAIZ.glob("MANIFESTO-v*.md")
                 if "PENDENCIAS DE RATIFICACAO" in
                 m.read_text(encoding="utf-8")]
    assert len(com_secao) >= 5, (
        f"só {len(com_secao)} manifesto(s) mantêm a seção de pendências — "
        f"o histórico está sendo reescrito")


def test_o_que_segue_pendente_nao_esta_vazio():
    """Zero pendência num projeto vivo é sinal de que alguém parou de
    registrar, não de que tudo foi decidido."""
    texto = LEDGER.read_text(encoding="utf-8")
    corpo = texto.split("## O que segue pendente")[-1]
    assert corpo.count("|") > 6, "seção de pendências vazia"




# --------------------------------------------------------------------- 11-15
# Helpers proprios. `escrever` (acima) cria o diretorio; estes recebem o
# diretorio de fora, porque as ratificacoes 12 e 15 precisam de DOIS repos no
# mesmo teste — com e sem o comentario de intencao, com dominio reservado e
# com dominio vivo — e comparar os dois so faz sentido se quem chama controla
# os caminhos.
CFG_CONSERTO = {"catalog_path": "catalog.yaml"}


def escrever_em(base, arquivos, packs=("privacy", "security")):
    for nome, corpo in arquivos.items():
        alvo = base / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return executar(base, set(packs), CFG_CONSERTO)


def de(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


@pytest.fixture
def ctx_vazio(tmp_path):
    return Contexto(tmp_path)

# ===========================================================================
# 11 a 15 — a rodada de conserto, medida contra 6 alvos reais
#
# As dez primeiras nasceram do desenvolvimento contra o `btv`. Estas cinco
# nasceram de defeitos da PRÓPRIA suíte que só apareceram contra repositórios
# de verdade: 18 dos 19 CRÍTICOs de credencial eram fixtures, 281 arquivos
# React eram invisíveis, e a régua dizia coisas opostas sobre `example.com`
# dependendo de qual check a lia.
# ===========================================================================
# ============================================================ ratificação 11
@pytest.mark.pse_security
def test_r11_credencial_em_teste_e_medio_e_nao_some(tmp_path):
    res = escrever_em(tmp_path, {"tests/test_x.py": 'password = "test-secret"\n'})
    achados = de(res, "P-06")
    assert achados, "supressão não é o conserto — o achado tem de continuar lá"
    assert achados[0].severidade.value == "MEDIO"
    assert "REBAIXADA" in achados[0].descricao, (
        "achado rebaixado sem motivo escrito é pior que não rebaixado: o "
        "leitor vê MÉDIO e não sabe se a suíte julgou ou desistiu")


# ============================================================ ratificação 12
#
# A que parece uma exceção e não é. Um teste que prova que a API recusa token
# inválido PRECISA de um token inválido escrito ali — é o caso mais simpático
# que existe, e a tentação é criar uma categoria "não-credencial" e sumir com
# o achado. Isso seria crer na intenção declarada, que é o D-01 ao contrário.
@pytest.mark.pse_security
def test_r12_token_para_rejeicao_e_medio(tmp_path):
    res = escrever_em(tmp_path, {
        "tests/test_api_security.py":
            'def test_recusa_token_invalido():\n'
            '    api_key = "invalid-token-para-provar-a-recusa"\n'
            '    assert cliente.get("/x", token=api_key).status == 401\n'})
    achados = de(res, "S-06")
    assert achados, "o achado não pode sumir por intenção declarada"
    assert achados[0].severidade.value == "MEDIO"


@pytest.mark.pse_security
@pytest.mark.mordida
def test_r12_comentario_de_intencao_nao_muda_nada(tmp_path):
    """O selo da ratificação 2. Com e sem o comentário, o veredito é o mesmo:
    a suíte não lê intenção. Se um dia o comentário passar a rebaixar (ou a
    suprimir), este teste reprova — e é ele que impede a categoria
    'não-credencial' de nascer pela porta dos fundos."""
    corpo_sem = ('def test_recusa():\n'
                 '    api_key = "Kp7xR2mQvLt9Wz4Ny6Bd"\n')
    corpo_com = ('def test_recusa():\n'
                 '    # intentionally invalid — exists only to be rejected\n'
                 '    api_key = "Kp7xR2mQvLt9Wz4Ny6Bd"\n')
    sem = de(escrever_em(tmp_path / "a", {"tests/test_s.py": corpo_sem}), "S-06")
    com = de(escrever_em(tmp_path / "b", {"tests/test_s.py": corpo_com}), "S-06")
    assert len(sem) == len(com) == 1, "o comentário mudou a existência do achado"
    assert sem[0].severidade.value == com[0].severidade.value == "MEDIO"


@pytest.mark.pse_security
@pytest.mark.mordida
def test_r12_intencao_nao_rebaixa_fora_de_teste(tmp_path):
    """A outra ponta: o comentário não pode rebaixar credencial de produção.
    Se rebaixasse, mover o segredo seria desnecessário — bastaria escrever a
    frase certa ao lado dele."""
    res = escrever_em(tmp_path, {
        "app/config.py":
            '# intentionally invalid, only used in the rejection test\n'
            'secret_key = "Kp7xR2mQvLt9Wz4Ny6Bd"\n'})
    assert de(res, "P-06")[0].severidade.value == "CRITICO"


def test_r12_nao_existe_categoria_nao_credencial():
    """A garantia estrutural: `_credencial.severidade` só devolve CRITICO ou
    MEDIO. Não há `None`, não há `INFO`, não há ramo que faça o achado
    desaparecer — e a régua não tem grupo de supressão."""
    import inspect
    fonte = inspect.getsource(_credencial.severidade)
    assert "return None" not in fonte
    assert "INFO" not in fonte and "BAIXO" not in fonte


# ============================================================ ratificação 13
@pytest.mark.pse_security
@pytest.mark.mordida
def test_r13_o_decimo_nono_caso_segue_critico(tmp_path):
    """O caso que a correção cegou duas vezes antes de passar. Valor real,
    copiado do alvo: fixture inventada prova o que quem a escreveu imaginava."""
    res = escrever_em(tmp_path, {
        "scripts/generate_test_password.py":
            'password = "SecurePassword123!"\n'})
    assert de(res, "P-06")[0].severidade.value == "CRITICO"


def test_r13_a_posicao_e_a_fronteira_estao_declaradas(ctx_vazio):
    assert not _credencial.caminho_de_teste(ctx_vazio, "scripts/generate_test_password.py")
    assert _credencial.caminho_de_teste(ctx_vazio, "tests/test_login.py")
    assert not _credencial.valor_sintetico(ctx_vazio, 'p = "SecurePassword123!"')
    assert _credencial.valor_sintetico(ctx_vazio, 'p = "test-secret"')


# ============================================================ ratificação 14
@pytest.mark.pse_privacy
def test_r14_tsx_e_jsx_no_alcance(tmp_path):
    res = escrever_em(tmp_path, {
        "src/A.tsx": 'console.log("u", user.cpf);\n',
        "src/B.jsx": 'console.log("u", user.email);\n'})
    arquivos = {f.arquivo for f in de(res, "P-01")}
    assert any(a.endswith(".tsx") for a in arquivos), arquivos
    assert any(a.endswith(".jsx") for a in arquivos), arquivos


def test_r14_a_familia_vive_num_lugar_so():
    assert {".js", ".jsx", ".ts", ".tsx"} <= scan.ECMASCRIPT


# ============================================================ ratificação 15
@pytest.mark.pse_privacy
def test_r15_email_reservado_nao_dispara_e_o_vivo_dispara(tmp_path):
    reservado = escrever_em(tmp_path / "a", {
        "seed.py": 'import logging\nlogging.info("u test@example.com")\n'})
    vivo = escrever_em(tmp_path / "b", {
        "seed.py": 'import logging\nlogging.info("u joao@bancoreal.com.br")\n'})
    assert not de(reservado, "P-01")
    assert de(vivo, "P-01"), "e-mail real parou de disparar — afrouxou demais"


# ======================================= nada implementado no escuro (A-01/A-02)
#
# A prova de que a pendência é real, e não uma frase. Se um destes reprovar, ou
# o check foi implementado sem a resposta do dono, ou a resposta chegou e
# `docs/RATIFICACOES.md` não foi atualizado — e as duas exigem revisão humana.
# `S-09` saiu da lista: nesta linhagem o ID EXISTE (token no cliente), e a
# alternativa de D-05 sumiu por fato — o check de PAN, quando A-01 for
# respondida, só pode ser `P-12`. Ver o fim de docs/RATIFICACOES.md.
CHECKS_BLOQUEADOS = ("P-12",)

# A trava de órfão reprova todo teste que cite ID fora do catálogo — é assim
# que se pega o teste que ficou para trás depois de um check ser renomeado.
# Aqui os IDs inexistentes SÃO o corpo de prova: eles existem para provar que
# os dois checks bloqueados não foram implementados. A exceção fica declarada,
# com motivo, e some no dia em que os checks entrarem.
CHECKS_FORA_DO_CATALOGO = {
    "P-12": "check de PAN, bloqueado por A-01 — citado aqui para provar que "
            "NÃO está no catálogo",
}


@pytest.mark.mordida
def test_checks_bloqueados_por_pergunta_do_dono_nao_existem():
    """PAN (A-01) e sigilo em LLM (A-02 + D-07) seguem não implementados.

    Um check que nasce sem alvo real provando que dispara é hipótese, e a
    severidade dele é chute. PAN sem saber se é logado, e sigilo sem saber o
    provider, seriam exatamente isso."""
    for cid in CHECKS_BLOQUEADOS:
        assert cid not in catalogo.CATALOGO, (
            f"{cid} entrou no catálogo. Se A-01/A-02/D-07 foram respondidas, "
            f"atualize docs/RATIFICACOES.md e este teste no mesmo commit; "
            f"senão, o check nasceu no escuro.")


@pytest.mark.mordida
def test_e11_nao_ganhou_refino_de_sigilo_sem_a_declaracao():
    """O refino de sigilo depende de `llm_egress` no config (D-07), cuja
    omissão tem de levar a INDETERMINADO. Enquanto a declaração não existir no
    schema, o refino não pode existir no código — senão ele decide no
    silêncio, que é o oposto do que a especificação pede."""
    regua = RAIZ / "pse" / "data"
    assert not (regua / "sigilo.yaml").exists(), "régua de sigilo sem D-07"
    schema = (RAIZ / "pse" / "schemas").glob("*.json")
    for s in schema:
        assert "llm_egress" not in s.read_text(encoding="utf-8"), (
            f"`llm_egress` apareceu em {s.name} sem D-07 respondida")


def test_as_pendencias_estao_escritas_onde_alguem_acha():
    """Decisão que ninguém encontra não foi tomada — e pendência também não."""
    doc = LEDGER.read_text(encoding="utf-8")
    for marca in ("A-01", "A-02", "D-07"):
        assert marca in doc, f"{marca} sumiu de RATIFICACOES.md"
    pend = (RAIZ / "docs" / "reconhecimento" / "PENDENCIAS-DO-DONO.md")
    assert pend.is_file() and "A-01" in pend.read_text(encoding="utf-8")


