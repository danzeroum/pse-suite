"""O MOTOR da camada dinâmica — antes de qualquer check existir.

Motor primeiro, checks depois. Um check dinâmico escrito antes de o
NetworkLog estar de pé seria um check cuja prova depende de uma peça que
ninguém provou.

Este módulo cobre três coisas distintas, e a distinção importa:

  1. A SELEÇÃO DE ENGINE — pura, sem navegador. Engine desconhecida é erro
     fail-closed: um typo que degenerasse em "rodou zero engines e passou"
     seria a pior forma de verde falso.
  2. O CONTRATO DO NetworkLog — imutabilidade, casamento de host por sufixo
     de rótulo, e a sanitização. Roda em qualquer máquina.
  3. A OBSERVAÇÃO REAL — Playwright abrindo um navegador de verdade contra
     um servidor de verdade. É a única prova de que o motor observa; as
     outras duas provariam um motor que nunca abriu página.

A lição do `dist/` no .gitignore, invertida: *working tree verde* não provou
reprodutibilidade, e *NetworkLog fabricado verde* não prova observação.
Ambiente local de pé e alvo presumido no ar são as duas faces do mesmo erro.
"""
import dataclasses
import importlib.util
import os

import pytest

from pse.model import EntradaInvalida
from pse.navegador import engines, rede, sessao
from pse.navegador.rede import (CookieObservado, NetworkLog, RequisicaoObservada,
                                host_casa, host_de)

pytestmark = pytest.mark.pse_dinamico

REGUA_SINTETICA = {"rastreadores": {
    "engines_validas": ["chromium", "firefox", "webkit"]}}

# O binário pode viver fora do registro do Playwright (imagem de container).
# Sem Playwright instalado, os testes marcados `pse_navegador` são pulados —
# e os de contrato, que são a maioria, seguem rodando.
def _motivo_de_pular() -> str:
    """"" se dá para observar; a instrução, se não dá.

    Duas condições distintas, e a mensagem diz qual falhou: o PACOTE pode
    estar instalado e o BINÁRIO não (é o caso de toda imagem onde alguém
    instalou `playwright` sem rodar `playwright install`). Skip anônimo
    faria as duas sumirem na mesma linha — e a suite inteira existe para
    não confundir "não olhei" com "olhei e estava bem".
    """
    if importlib.util.find_spec("playwright") is None:
        return ("Playwright ausente — a camada dinâmica é opcional: "
                "pip install 'pse-suite[browser]'")
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            executavel = os.environ.get(sessao.ENV_EXECUTAVEL) or None
            navegador = p.chromium.launch(
                **({"executable_path": executavel} if executavel else {}))
            navegador.close()
        return ""
    except Exception as e:
        return (f"binário de navegador indisponível ({str(e).splitlines()[0][:110]}) "
                f"— rode `python -m playwright install chromium`, ou aponte "
                f"{sessao.ENV_EXECUTAVEL} para um binário existente")


MOTIVO = _motivo_de_pular()
tem_playwright = pytest.mark.skipif(bool(MOTIVO), reason=MOTIVO or "ok")


# ==================================================== 1. seleção de engine
def test_default_e_so_chromium():
    assert engines.engines_configurados({}, REGUA_SINTETICA) == ("chromium",)


def test_lista_declarada_preserva_ordem_e_unicidade():
    env = {engines.ENV_ENGINES: "webkit, chromium ,webkit"}
    assert engines.engines_configurados(env, REGUA_SINTETICA) == \
        ("webkit", "chromium")


@pytest.mark.mordida
def test_engine_desconhecida_e_erro_fail_closed():
    """O ponto que a qa-suite fixou e que não pode se perder: filtrar em
    silêncio faria a execução terminar sem ter aberto navegador nenhum, e
    passar. Verde por não ter olhado, com o agravante de o operador achar
    que a matriz completa rodou."""
    env = {engines.ENV_ENGINES: "chromiun"}
    with pytest.raises(EntradaInvalida) as e:
        engines.engines_configurados(env, REGUA_SINTETICA)
    assert "chromiun" in str(e.value)
    assert "silencio" in str(e.value).lower() or "silêncio" in str(e.value).lower()


@pytest.mark.mordida
def test_engine_invalida_no_meio_da_lista_tambem_reprova():
    """Uma válida antes da inválida não pode 'salvar' a execução."""
    env = {engines.ENV_ENGINES: "chromium,opera"}
    with pytest.raises(EntradaInvalida):
        engines.engines_configurados(env, REGUA_SINTETICA)


def test_vocabulario_de_engine_vem_da_regua():
    """Não há lista de engines hardcoded no módulo: ela vive na régua, como
    tudo que é curado (D-13)."""
    from pathlib import Path
    fonte = Path(engines.__file__).read_text(encoding="utf-8")
    for proibida in ('"firefox"', "'firefox'", '"webkit"', "'webkit'"):
        assert proibida not in fonte, f"{proibida} hardcoded em engines.py"


# ==================================================== 2. contrato do NetworkLog
def test_network_log_e_imutavel():
    """Os três checks compartilham UMA observação. Log mutável deixaria o
    primeiro a rodar alterar o que o segundo enxerga — bug silencioso e
    dependente de ordem, a pior combinação num artefato que é prova."""
    log = NetworkLog(url="https://a.example.org/")
    with pytest.raises(dataclasses.FrozenInstanceError):
        log.url = "https://outro.example.org/"
    with pytest.raises(dataclasses.FrozenInstanceError):
        RequisicaoObservada("https://x.example.org/").url = "y"
    with pytest.raises(dataclasses.FrozenInstanceError):
        CookieObservado("s").httpOnly = True


@pytest.mark.parametrize("host,dominio,esperado", [
    ("google-analytics.com", "google-analytics.com", True),
    ("www.google-analytics.com", "google-analytics.com", True),
    ("ssl.google-analytics.com", "google-analytics.com", True),
    # A trava: casamento por SUFIXO DE RÓTULO, nunca por substring.
    ("meugoogle-analytics.com", "google-analytics.com", False),
    ("google-analytics.com.br", "google-analytics.com", False),
    ("", "google-analytics.com", False),
    ("alvo.example.org", "", False),
])
def test_host_casa_por_sufixo_de_rotulo(host, dominio, esperado):
    assert host_casa(host, dominio) is esperado


@pytest.mark.parametrize("url,esperado", [
    ("https://Alvo.Example.ORG/x?y=1", "alvo.example.org"),
    ("http://127.0.0.1:8080/", "127.0.0.1"),
    ("data:text/html,<p>", ""),
    ("about:blank", ""),
    ("blob:https://a.example.org/uuid", ""),
])
def test_host_de(url, esperado):
    assert host_de(url) == esperado


def test_log_distingue_vazio_de_nao_observado():
    """Log vazio e log-que-não-foi-feito nunca podem se confundir: o
    primeiro é 'olhei e não havia nada', o segundo é 'não olhei'."""
    vazio = NetworkLog(url="https://a.example.org/")
    nao_feito = sessao.ausente("https://a.example.org/", "Playwright ausente")
    assert vazio.observou is True
    assert nao_feito.observou is False
    assert nao_feito.motivo_de_ausencia


def test_cookie_de_playwright_descarta_o_valor():
    """Um cookie de sessão É uma credencial. Guardá-lo em memória para depois
    lembrar de não serializá-lo seria confiar na disciplina do próximo
    consumidor de `executar()`; aqui ele não existe."""
    bruto = {"name": "sessionid", "value": "segredo-do-titular-123",
             "httpOnly": True, "secure": True, "sameSite": "Lax"}
    cookie = CookieObservado.de_playwright(bruto)
    assert cookie.name == "sessionid"
    assert cookie.valor_presente is True
    assert "segredo-do-titular-123" not in repr(cookie)
    assert not hasattr(cookie, "value")


def test_sanitizado_nao_carrega_valor_de_cookie_nem_pii():
    """A projeção que vai para o laudo. A evidência dinâmica prova um
    vazamento; publicar o dado vazado junto faria dela o segundo vazamento —
    e este circula por CI, anexo de PR e caixa de e-mail."""
    log = NetworkLog(
        url="https://alvo.example.org/fatura?cpf=529.982.247-25",
        requisicoes=(RequisicaoObservada(
            "https://alvo.example.org/x?email=maria@empresa.com.br"),),
        cookies=(CookieObservado.de_playwright(
            {"name": "sessionid", "value": "sk-live-segredo"}),))
    saida = log.sanitizado()
    texto = repr(saida)
    assert "529.982.247-25" not in texto
    assert "sk-live-segredo" not in texto
    assert saida["total_requisicoes"] == 1


def test_de_terceiros_usa_a_origem_do_proprio_log():
    log = NetworkLog(
        url="https://alvo.example.org/",
        requisicoes=(RequisicaoObservada("https://alvo.example.org/a.js"),
                     RequisicaoObservada("https://cdn.alvo.example.org/b.js"),
                     RequisicaoObservada("https://terceiro.example.net/c.js")))
    assert [host_de(r.url) for r in log.de_terceiros()] == ["terceiro.example.net"]


def test_allowlist_vence_a_lista_de_rastreadores():
    """É a decisão documentada do controlador, e o check não pode ser mais
    esperto que a decisão registrada."""
    log = NetworkLog(
        url="https://alvo.example.org/",
        requisicoes=(RequisicaoObservada(
            "https://www.google-analytics.com/collect"),))
    dominios = ["google-analytics.com"]
    assert log.hosts_rastreadores(dominios) == ["www.google-analytics.com"]
    assert log.hosts_rastreadores(dominios, ["google-analytics.com"]) == []


# ==================================================== 3. a observação REAL
@tem_playwright
@pytest.mark.pse_navegador
def test_observa_alvo_real_e_ve_o_terceiro(alvo_de_fixture):
    """A prova que nenhum objeto fabricado dá: Playwright sobe, carrega uma
    página servida de verdade, e a tag que dispara DEPOIS do load aparece."""
    log = sessao.observar(alvo_de_fixture.url("/sujo"), espera_ms=900)
    assert log.observou
    assert alvo_de_fixture.host_terceiro in log.hosts()
    assert any("tag-de-analytics" in r.url for r in log.de_terceiros()), (
        "a tag dispara 200ms após o load — observar cedo demais produziria "
        "aprovação falsa, e é por isso que a espera pós-load existe")


@tem_playwright
@pytest.mark.pse_navegador
def test_cookies_chegam_com_os_atributos_que_o_navegador_viu(alvo_de_fixture):
    sujo = sessao.observar(alvo_de_fixture.url("/sujo"), espera_ms=500)
    limpo = sessao.observar(alvo_de_fixture.url("/limpo"), espera_ms=500)
    por_nome = {c.name: c for c in sujo.cookies}
    assert por_nome["sessionid"].httpOnly is False
    assert por_nome["sessionid"].secure is False
    assert "_ga" in por_nome
    bom = {c.name: c for c in limpo.cookies}
    assert bom["sessionid"].httpOnly is True and bom["sessionid"].secure is True


@tem_playwright
@pytest.mark.pse_navegador
def test_contexto_nasce_virgem_a_cada_observacao(alvo_de_fixture):
    """Cookie herdado de uma observação anterior faria o alvo parecer
    conforme ('já consentiu antes') — o pior falso negativo possível numa
    bateria de consentimento prévio."""
    sessao.observar(alvo_de_fixture.url("/sujo"), espera_ms=300)
    segunda = sessao.observar(alvo_de_fixture.url("/limpo"), espera_ms=300)
    assert "_ga" not in segunda.nomes_de_cookie(), (
        "o cookie de analytics da observação anterior sobreviveu — o contexto "
        "não estava virgem")


@tem_playwright
@pytest.mark.pse_navegador
def test_html_entregue_chega_ao_log(alvo_de_fixture):
    log = sessao.observar(alvo_de_fixture.url("/sujo"), espera_ms=300)
    assert "<form" in log.html and 'method="get"' in log.html.lower()


@tem_playwright
@pytest.mark.pse_navegador
@pytest.mark.mordida
def test_alvo_fora_do_ar_e_indeterminado(alvo_de_fixture):
    """A lição do dev, aplicada: ambiente local de pé não prova alvo
    respondendo. Porta fechada é indeterminação, nunca verde."""
    from pse.model import CheckIndeterminado
    porta_morta = f"http://127.0.0.1:{alvo_de_fixture.porta + 1}/"
    with pytest.raises(CheckIndeterminado):
        sessao.observar(porta_morta, espera_ms=0)


@pytest.mark.mordida
def test_playwright_ausente_vira_instrucao(monkeypatch):
    """Sem navegador, a mensagem tem de dizer o que fazer — e deixar claro
    que não olhar é diferente de olhar e não achar nada."""
    def sem_playwright():
        raise engines.PlaywrightAusente(engines.INSTRUCAO)
    monkeypatch.setattr(engines, "exigir_playwright", sem_playwright)
    monkeypatch.setattr(sessao, "exigir_playwright", sem_playwright)
    with pytest.raises(engines.PlaywrightAusente) as e:
        sessao.observar("https://a.example.org/")
    texto = str(e.value)
    assert "pse-suite[browser]" in texto
    assert "playwright install" in texto
    assert "INDETERMINADOS" in texto


def test_atribuicao_a_qa_suite_esta_declarada():
    """Procedência honesta é doutrina do projeto: o que foi portado diz de
    onde veio."""
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent / "pse" / "navegador"
    for nome in ("__init__.py", "engines.py", "rede.py", "sessao.py"):
        fonte = (raiz / nome).read_text(encoding="utf-8")
        assert "qa-suite" in fonte, f"{nome} não declara a procedência"
