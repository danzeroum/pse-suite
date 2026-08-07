"""S-18, S-19, S-20, P-24, S-21 — o resto do passivo, portado da qa-suite.

Fase 2 observa mais fundo que a Fase 1: além das requisições e dos cookies,
agora se lê o CORPO do que o servidor entregou. Isso multiplica os dois
riscos que já eram os únicos que importam, e por isso os testes duros deste
módulo são os mesmos dois:

  (a) VERDE FALSO. Corpo grande demais para ler não pode virar "limpo" —
      `test_s20_nada_lido_e_indeterminado` é a trava. Playwright ausente,
      alvo fora do ar e falta de atestação seguem cobertos em
      `test_dinamico.py`, e valem igual para estes cinco.
  (b) VAZAMENTO NA EVIDÊNCIA. Agora há um segredo *de verdade* passando
      pela suite. `test_s20_nao_publica_a_credencial` e
      `test_p24_nao_le_a_coordenada` são os testes que mais valem aqui:
      um laudo que republicasse a chave teria acabado de distribuí-la por
      CI, anexo de PR e caixa de e-mail.

NADA AQUI É ATIVO. Nenhum check desta fase clica, submete ou pede ao
servidor um recurso que ele não ofereceu. O `.map` que S-21 encontra **não
é baixado** — confirmar se está publicado é sondagem, logo Fase 3.
"""
import json
from contextlib import contextmanager
from datetime import date, timedelta

import pytest

from pse.engine.runner import executar
from pse.model import Severidade
from pse.navegador.analise import jpeg_com_exif_gps
from pse.navegador.rede import CookieObservado, NetworkLog, RecursoObservado
from pse.navegador.rede import RequisicaoObservada
from pse.trabalho_a.autorizacao import fingerprint_alvo

from test_navegador import MOTIVO as _MOTIVO_NAVEGADOR

pytestmark = pytest.mark.pse_dinamico

FASE2 = ("S-18", "S-19", "S-20", "P-24", "S-21")
BASE_URL = "https://alvo.example.org"
SEGREDO = "AKIAIOSFODNN7EXAMPLE"

tem_playwright = pytest.mark.skipif(bool(_MOTIVO_NAVEGADOR),
                                    reason=_MOTIVO_NAVEGADOR or "ok")

MANIFESTO = """integrations:
  - name: parceiro-declarado
    hosts: [api.declarado.example.org]
    dpa_signed: true
"""

CABECALHOS_OK = (("content-security-policy", "default-src 'self'"),
                 ("x-content-type-options", "nosniff"),
                 ("referrer-policy", "no-referrer"))


class Observador:
    def __init__(self, log):
        self.log, self.chamadas = log, 0

    def __call__(self, url, engine=None, user_agent=None, data=None, **_):
        self.chamadas += 1
        return self.log


class TransporteDeHealth:
    def __init__(self, status=200):
        self.status, self.chamadas = status, []

    def enviar(self, metodo, url, headers, corpo, timeout):
        from pse.trabalho_a.cliente import Resposta
        self.chamadas.append((metodo, url))
        return Resposta(self.status, "{}", {})


def config(**extra):
    return {"third_party_manifest": "tp.yml", **extra, "target": {
        "base_url": BASE_URL, "environment": "staging", "healthcheck": "/health",
        "authorization": {
            "attested_by": "arquiteto@danzeroum",
            "scope": ["pse_passive", "pse_active"],
            "target_fingerprint": fingerprint_alvo(BASE_URL),
            "expires": (date.today() + timedelta(days=90)).isoformat(),
            "synthetic_identities": True}}}


def log_de(url=BASE_URL + "/", requisicoes=(), recursos=(), cookies=(), html=""):
    return NetworkLog(
        url=url,
        requisicoes=tuple(RequisicaoObservada(u) for u in requisicoes),
        recursos=tuple(recursos), cookies=tuple(cookies), html=html,
        engine="fixture")


def documento(headers=CABECALHOS_OK, url=BASE_URL + "/"):
    return RecursoObservado(url=url, status=200, tipo="text/html",
                            da_origem=True, headers=tuple(headers))


def rodar(tmp_path, log, cfg=None, com_manifesto=True):
    if com_manifesto:
        (tmp_path / "tp.yml").write_text(MANIFESTO, encoding="utf-8")
    obs = Observador(log)
    res = executar(tmp_path, {"privacy", "security"}, cfg or config(),
                   modo="pse_passive", transporte=TransporteDeHealth(),
                   doms=["frontend"], observador=obs)
    return res, obs


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


@contextmanager
def regua_sem_ignorar_loopback():
    """Régua sintética sem `localhost` em `ignorar`, só para o ponta a ponta.

    A régua de PRODUÇÃO ignora hosts de exemplo e loopback de propósito — e
    é o certo. Mas o alvo de fixture serve o "terceiro" por `localhost`,
    então sem esta janela o e2e de S-18 provaria o silêncio em vez do
    achado. A regra em si é coberta com host real em
    `test_s18_terceiro_nao_declarado`.
    """
    from pse.engine.context import Contexto
    original = Contexto.__init__

    def com_regua(self, *a, **kw):
        original(self, *a, **kw)
        terceiros = dict(self.data["third-party-endpoints"])
        terceiros["ignorar"] = [h for h in terceiros.get("ignorar", [])
                                if h not in ("localhost", "127.0.0.1")]
        self.data["third-party-endpoints"] = terceiros

    Contexto.__init__ = com_regua
    try:
        yield
    finally:
        Contexto.__init__ = original


# ==================================================== o alvo limpo não dispara
def test_alvo_limpo_nao_dispara_nenhum_dos_cinco(tmp_path):
    """Vale mais que os cinco caminhos felizes somados: cinco checks novos
    que acusassem um alvo correto ensinariam o time a desligar a camada
    dinâmica inteira."""
    log = log_de(
        requisicoes=[BASE_URL + "/", BASE_URL + "/app.js"],
        recursos=[documento(),
                  RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                   tipo="application/javascript", da_origem=True,
                                   headers=tuple(CABECALHOS_OK),
                                   corpo=b"var cfg={endpoint:'/api'};"),
                  RecursoObservado(url=BASE_URL + "/foto.jpg", status=200,
                                   tipo="image/jpeg", da_origem=True,
                                   corpo=jpeg_com_exif_gps(False))])
    res, _ = rodar(tmp_path, log)
    for cid in FASE2:
        assert not acha(res, cid), [(f.arquivo, f.titulo) for f in acha(res, cid)]
        assert cid in res["checks_executados"], f"{cid} não chegou a executar"


# ==================================================== S-18
@pytest.mark.pse_security
def test_s18_terceiro_nao_declarado(tmp_path):
    log = log_de(requisicoes=[BASE_URL + "/",
                              "https://cdn.terceiro.example.net/widget.js"])
    res, _ = rodar(tmp_path, log)
    s18 = acha(res, "S-18")
    assert s18 and "cdn.terceiro.example.net" in s18[0].descricao


@pytest.mark.pse_security
def test_s18_host_declarado_nao_dispara(tmp_path):
    log = log_de(requisicoes=[BASE_URL + "/",
                              "https://api.declarado.example.org/x"])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-18")


@pytest.mark.pse_security
def test_s18_subdominio_de_declarado_e_o_mesmo_controlador(tmp_path):
    """Quem declarou `declarado.example.org` declarou o controlador."""
    log = log_de(requisicoes=[BASE_URL + "/",
                              "https://cdn.api.declarado.example.org/x"])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-18")


@pytest.mark.pse_security
def test_s18_primeira_parte_nao_e_terceiro(tmp_path):
    log = log_de(requisicoes=[BASE_URL + "/", BASE_URL + "/a.js",
                              "https://cdn.alvo.example.org/b.js"])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-18")


@pytest.mark.pse_security
def test_s18_sem_manifesto_e_pulado(tmp_path):
    log = log_de(requisicoes=[BASE_URL + "/", "https://t.example.net/x"])
    res, _ = rodar(tmp_path, log, com_manifesto=False)
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "S-18" in pulados and "S-04" in pulados["S-18"]


@pytest.mark.pse_security
def test_s18_inventario_vai_ao_laudo_mesmo_sem_achado(tmp_path):
    """Insumo de ROPA (Art. 37): o consumidor precisa saber o que já está
    certo, não só o que está errado."""
    log = log_de(requisicoes=[BASE_URL + "/",
                              "https://api.declarado.example.org/x"])
    res, _ = rodar(tmp_path, log)
    inv = res["relatorios"]["terceiros_observados"]
    assert inv["hosts"] and inv["hosts"][0]["host"] == "api.declarado.example.org"


# ==================================================== S-19
@pytest.mark.pse_security
def test_s19_documento_sem_cabecalhos(tmp_path):
    res, _ = rodar(tmp_path, log_de(recursos=[documento(headers=())]))
    s19 = acha(res, "S-19")
    assert s19
    titulo = s19[0].titulo.lower()
    assert "content-security-policy" in titulo and "x-content-type-options" in titulo


@pytest.mark.pse_security
def test_s19_cabecalho_vazio_conta_como_ausente(tmp_path):
    """`CSP: ` não restringe nada. Tratar a presença da chave como
    conformidade premiaria a configuração que só parece existir."""
    res, _ = rodar(tmp_path, log_de(recursos=[documento(headers=(
        ("content-security-policy", "  "), ("x-content-type-options", "nosniff"),
        ("referrer-policy", "no-referrer")))]))
    s19 = acha(res, "S-19")
    assert s19 and "content-security-policy" in s19[0].titulo.lower()


@pytest.mark.pse_security
def test_s19_mixed_content(tmp_path):
    log = log_de(recursos=[documento(),
                           RecursoObservado(url="http://cdn.example.net/x.js",
                                            status=200, tipo="application/javascript")])
    res, _ = rodar(tmp_path, log)
    s19 = acha(res, "S-19")
    assert any("http://" in f.titulo for f in s19), [f.titulo for f in s19]


@pytest.mark.pse_security
def test_s19_alvo_http_nao_tem_mixed_content(tmp_path):
    """Num alvo http NADA é mixed content, e cobrar ali seria inventar
    violação."""
    log = log_de(url="http://127.0.0.1:9/",
                 recursos=[documento(url="http://127.0.0.1:9/"),
                           RecursoObservado(url="http://127.0.0.1:9/x.js",
                                            status=200, tipo="application/javascript")])
    res, _ = rodar(tmp_path, log)
    assert not [f for f in acha(res, "S-19") if "http://" in f.titulo]


@pytest.mark.pse_security
def test_s19_asset_de_terceiro_pelado_e_observacao_nao_achado(tmp_path):
    """Maturidade do FORNECEDOR: o controlador do alvo não manda no servidor
    dele. Vira observação no laudo, com o que ele pode fazer."""
    log = log_de(recursos=[documento(),
                           RecursoObservado(url="https://cdn.example.net/x.js",
                                            status=200, tipo="application/javascript",
                                            da_origem=False)])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-19")
    assert res["relatorios"]["assets_de_terceiro_sem_nosniff"]["recursos"]


@pytest.mark.pse_security
def test_s19_hsts_ausente_e_informativo(tmp_path):
    res, _ = rodar(tmp_path, log_de(recursos=[documento()]))
    assert not acha(res, "S-19")
    informativos = res["relatorios"]["cabecalhos_informativos_ausentes"]
    assert "strict-transport-security" in informativos["cabecalhos"]


# ==================================================== S-20
@pytest.mark.pse_security
def test_s20_credencial_no_bundle_de_origem(tmp_path):
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                            tipo="application/javascript",
                                            da_origem=True,
                                            corpo=f'var k="{SEGREDO}";'.encode())])
    res, _ = rodar(tmp_path, log)
    s20 = acha(res, "S-20")
    assert s20 and s20[0].severidade is Severidade.CRITICO
    assert "AWS_ACCESS_KEY_ID" in s20[0].titulo


@pytest.mark.pse_security
def test_s20_bundle_de_terceiro_esta_fora_de_escopo(tmp_path):
    """Chave num bundle de terceiro é problema do terceiro, e o controlador
    não tem como removê-la."""
    log = log_de(recursos=[documento(),
                           RecursoObservado(url="https://cdn.example.net/x.js",
                                            status=200, tipo="application/javascript",
                                            da_origem=False,
                                            corpo=f'var k="{SEGREDO}";'.encode())])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-20")


@pytest.mark.pse_security
def test_s20_bundle_limpo_nao_dispara(tmp_path):
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                            tipo="application/javascript",
                                            da_origem=True,
                                            corpo=b"var cfg={endpoint:'/api'};")])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-20")


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s20_nada_lido_e_indeterminado(tmp_path):
    """Teto de memória NÃO é atestado de conformidade. Se nenhum candidato
    pôde ser lido, o check não sabe — e não saber bloqueia."""
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                            tipo="application/javascript",
                                            da_origem=True,
                                            motivo_nao_lido="corpo acima do teto")])
    res, _ = rodar(tmp_path, log)
    indet = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "S-20" in indet and "nao e limpo" in indet["S-20"]


@pytest.mark.pse_security
def test_s20_parcialmente_lido_declara_o_que_ficou_de_fora(tmp_path):
    log = log_de(recursos=[
        documento(),
        RecursoObservado(url=BASE_URL + "/a.js", status=200,
                         tipo="application/javascript", da_origem=True,
                         corpo=f'var k="{SEGREDO}";'.encode()),
        RecursoObservado(url=BASE_URL + "/b.js", status=200,
                         tipo="application/javascript", da_origem=True,
                         motivo_nao_lido="corpo acima do teto")])
    res, _ = rodar(tmp_path, log)
    assert acha(res, "S-20")
    assert res["relatorios"]["recursos_nao_varridos"]["recursos"]


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s20_nao_publica_a_credencial(tmp_path):
    """O teste que mais vale nesta fase. A chave passa pela suite; ela não
    pode sair do outro lado."""
    from pse.evidence import montar_laudo
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                            tipo="application/javascript",
                                            da_origem=True,
                                            corpo=f'var apiKey="{SEGREDO}";'.encode())])
    res, _ = rodar(tmp_path, log)
    assert acha(res, "S-20"), "a credencial não foi detectada"
    serializado = json.dumps(montar_laudo(tmp_path, res, {"privacy", "security"}))
    assert SEGREDO not in serializado, "o laudo republicou a credencial"
    assert "AWS_ACCESS_KEY_ID" in serializado, "o FORMATO tem de estar lá"


# ==================================================== P-24
@pytest.mark.pse_privacy
def test_p24_gps_em_imagem_publicada(tmp_path):
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/foto.jpg", status=200,
                                            tipo="image/jpeg", da_origem=True,
                                            corpo=jpeg_com_exif_gps(True))])
    res, _ = rodar(tmp_path, log)
    p24 = acha(res, "P-24")
    assert p24 and p24[0].severidade is Severidade.ALTO
    assert "Art. 5" in p24[0].base_legal


@pytest.mark.pse_privacy
def test_p24_imagem_sem_exif_nao_dispara(tmp_path):
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/foto.jpg", status=200,
                                            tipo="image/jpeg", da_origem=True,
                                            corpo=jpeg_com_exif_gps(False))])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "P-24")


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_p24_nao_le_a_coordenada(tmp_path):
    """A minimização acontece ANTES do sanitizador: o parser devolve o
    rótulo `gps`, e a coordenada nunca é extraída. Não há valor a mascarar —
    e o sanitizador roda por cima mesmo assim."""
    from pse.evidence import montar_laudo
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/foto.jpg", status=200,
                                            tipo="image/jpeg", da_origem=True,
                                            corpo=jpeg_com_exif_gps(True))])
    res, _ = rodar(tmp_path, log)
    laudo = json.dumps(montar_laudo(tmp_path, res, {"privacy", "security"}))
    assert "gps" in laudo.lower(), "a presença tem de ser reportada"
    for proibido in ("latitude", "longitude", "GPSLatitude", "coordenada:"):
        assert proibido not in laudo


@pytest.mark.pse_privacy
def test_p24_jpeg_quebrado_nao_e_acusacao(tmp_path):
    """Parser que chuta numa bateria regulatória é pior que parser nenhum."""
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/x.jpg", status=200,
                                            tipo="image/jpeg", da_origem=True,
                                            corpo=b"\xff\xd8lixo")])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "P-24")


# ==================================================== S-21
@pytest.mark.pse_security
def test_s21_sourcemap_referenciado(tmp_path):
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                            tipo="application/javascript",
                                            da_origem=True,
                                            corpo=b"var a=1;\n//# sourceMappingURL=app.js.map")])
    res, _ = rodar(tmp_path, log)
    s21 = acha(res, "S-21")
    assert s21 and s21[0].severidade is Severidade.MEDIO


@pytest.mark.pse_security
def test_s21_e_medio_porque_o_map_nao_foi_baixado(tmp_path):
    """A severidade carrega a honestidade do método: o que se sabe é que a
    REFERÊNCIA existe. Baixar o `.map` seria sondagem — Fase 3."""
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                            tipo="application/javascript",
                                            da_origem=True,
                                            corpo=b"//# sourceMappingURL=app.js.map")])
    res, _ = rodar(tmp_path, log)
    s21 = acha(res, "S-21")
    assert "nao foi baixado" in s21[0].descricao.lower()
    assert "sondagem" in s21[0].descricao.lower()


@pytest.mark.pse_security
def test_s21_bundle_sem_sourcemap_nao_dispara(tmp_path):
    log = log_de(recursos=[documento(),
                           RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                            tipo="application/javascript",
                                            da_origem=True, corpo=b"var a=1;")])
    res, _ = rodar(tmp_path, log)
    assert not acha(res, "S-21")


@pytest.mark.mordida
def test_nenhum_check_desta_fase_emite_requisicao_nova(tmp_path):
    """A linha que separa esta bateria de um scanner. O `.map` é apontado e
    NÃO buscado; nenhum check pede ao servidor o que ele não ofereceu."""
    log = log_de(recursos=[documento(headers=()),
                           RecursoObservado(url=BASE_URL + "/app.js", status=200,
                                            tipo="application/javascript",
                                            da_origem=True,
                                            corpo=b"//# sourceMappingURL=app.js.map")])
    transporte = TransporteDeHealth()
    (tmp_path / "tp.yml").write_text(MANIFESTO, encoding="utf-8")
    obs = Observador(log)
    executar(tmp_path, {"privacy", "security"}, config(), modo="pse_passive",
             transporte=transporte, doms=["frontend"], observador=obs)
    # Só o healthcheck, e UMA observação partilhada pelos oito dinâmicos.
    assert [u for _, u in transporte.chamadas] == [BASE_URL + "/health"]
    assert obs.chamadas == 1


# ==================================================== correlação
def test_correlacao_dos_pares_novos():
    from pse.correlacao import PARES, correlacionar
    from pse.model import Finding
    assert ("S-04", "S-18") in PARES and ("P-06", "S-20") in PARES

    estatico = Finding(check_id="P-06", pack="privacy",
                       severidade=Severidade.CRITICO, titulo="t", descricao="d",
                       recomendacao="r", arquivo="app.py", linha=3)
    dinamico = Finding(check_id="S-20", pack="security",
                       severidade=Severidade.CRITICO, titulo="t", descricao="d",
                       recomendacao="r", arquivo=BASE_URL + "/app.js")
    par = [c for c in correlacionar([estatico, dinamico])
           if c["par"] == ["P-06", "S-20"]][0]
    assert par["cenario"] == "confirmado_nas_duas_camadas"

    so_dinamico = [c for c in correlacionar([dinamico])
                   if c["par"] == ["P-06", "S-20"]][0]
    assert so_dinamico["cenario"] == "so_na_camada_dinamica"
    assert "build" in so_dinamico["leitura"]


# ==================================================== catálogo
def test_os_cinco_sao_passivos_e_de_frontend():
    from pse import catalogo
    for cid in FASE2:
        m = catalogo.meta(cid)
        assert catalogo.dominios(cid) == ["frontend"]
        assert m["modo"] == "passive", "nada de ativo nesta fase"
        assert m["tipo"] == "runtime"
        assert catalogo.pilar_esperado(cid) == m["pack"]
    assert catalogo.incoerencias_de_prefixo() == []


def test_cada_um_tem_mutacao_canonica():
    from pse.mutacao import provar
    for cid in FASE2:
        r = provar(cid)
        assert r["ok"], r["motivo"]


# ==================================================== ponta a ponta, alvo REAL
@tem_playwright
@pytest.mark.pse_navegador
@pytest.mark.mordida
def test_ponta_a_ponta_contra_alvo_real(tmp_path, alvo_de_fixture):
    """O aceite da fase: os cinco contra um alvo servindo de verdade, com
    navegador de verdade — e o segredo plantado NÃO sai no laudo."""
    from alvo_fixture.servir import SEGREDO_PLANTADO
    from pse.evidence import montar_laudo

    (tmp_path / "tp.yml").write_text(MANIFESTO, encoding="utf-8")
    cfg = config()
    cfg["target"]["base_url"] = alvo_de_fixture.url("/sujo")
    # Alvo em loopback: o degrau `local_target` SUBSTITUI o fingerprint —
    # a porta do alvo de fixture é efêmera, e um fingerprint que muda a cada
    # execução viraria burocracia que ninguém lê. Sem a linha, o contrato
    # recusa (há teste-mordida provando).
    cfg["target"]["authorization"].pop("target_fingerprint", None)
    cfg["target"]["authorization"]["local_target"] = True

    # O alvo de fixture serve o "terceiro" por `localhost`, que a régua de
    # produção lista em `ignorar` — e com razão: é host de exemplo. Para o
    # ponta a ponta exercitar S-18 de verdade, o teste usa uma régua
    # sintética sem essa entrada. A régua de produção segue intocada, e há
    # `test_s18_terceiro_nao_declarado` cobrindo a regra com host real.
    with regua_sem_ignorar_loopback():
        res = executar(tmp_path, {"privacy", "security"}, cfg,
                       modo="pse_passive", transporte=TransporteDeHealth(),
                       doms=["frontend"])
    laudo = montar_laudo(tmp_path, res, {"privacy", "security"})
    ids = {f["check_id"] for f in laudo["findings"]}

    assert {"S-18", "S-19", "S-20", "P-24", "S-21"} <= ids, (
        f"faltou: {sorted(ids)} / indet={res['checks_indeterminados']}")
    serializado = json.dumps(laudo)
    assert SEGREDO_PLANTADO not in serializado, "o laudo publicou a credencial"


@tem_playwright
@pytest.mark.pse_navegador
def test_alvo_real_limpo_nao_dispara(tmp_path, alvo_de_fixture):
    (tmp_path / "tp.yml").write_text(MANIFESTO, encoding="utf-8")
    cfg = config()
    cfg["target"]["base_url"] = alvo_de_fixture.url("/limpo")
    # Alvo em loopback: o degrau `local_target` SUBSTITUI o fingerprint —
    # a porta do alvo de fixture é efêmera, e um fingerprint que muda a cada
    # execução viraria burocracia que ninguém lê. Sem a linha, o contrato
    # recusa (há teste-mordida provando).
    cfg["target"]["authorization"].pop("target_fingerprint", None)
    cfg["target"]["authorization"]["local_target"] = True
    res = executar(tmp_path, {"privacy", "security"}, cfg, modo="pse_passive",
                   transporte=TransporteDeHealth(), doms=["frontend"])
    for cid in FASE2:
        assert not acha(res, cid), [(f.arquivo, f.titulo) for f in acha(res, cid)]
