"""Os dois defeitos que so o primeiro alvo local VIVO revelou.

Nenhum dos dois aparece em fixture, e a razao e a mesma nos dois casos: a
fixture e servida por um servidor que o teste escreveu, no processo do
teste, sem proxy e sem negociacao de conteudo. Um alvo real tem as duas
coisas — e as duas fizeram a suite julgar um alvo de pe como caido.

`alvo indisponivel` e o pior lugar possivel para um falso: ele bloqueia
TODOS os checks dinamicos de uma vez, com uma mensagem que manda o time
investigar o proprio sistema, que esta bom.
"""
import urllib.request

import pytest

from pse.engine.context import Contexto
from pse.model import CheckIndeterminado
from pse.trabalho_a.autorizacao import e_loopback, host_e_loopback
from pse.trabalho_a.cliente import TransporteUrllib


# --------------------------------------------------- loopback nao vai a proxy

@pytest.mark.parametrize("url", [
    "http://127.0.0.1:5178/",
    "http://localhost:8000/health",
    "https://127.0.0.1:8443/",
    "https://localhost:8443/",
    "http://[::1]:5178/",
])
def test_loopback_abre_sem_proxy(url):
    """Com `HTTPS_PROXY` no ambiente, `urllib` mandaria a requisicao de
    loopback para fora da maquina. O bypass nao e conveniencia de ambiente:
    o degrau `local_target` dispensa a prova de posse com o argumento de que
    em loopback nao ha rede nem intermediario. Se a requisicao atravessa um
    proxy, esse argumento e falso e a atestacao autoriza sobre premissa que
    nao se sustenta.
    """
    abridor = TransporteUrllib()._abridor(url)
    assert abridor is not urllib.request.urlopen
    # Nao basta "nao ser o urlopen padrao": o opener nao pode carregar UM
    # proxy configurado. Um ProxyHandler com proxies passaria pelo teste
    # anterior sem cumprir promessa nenhuma.
    com_proxy = [h.proxies for h in abridor.__self__.handlers
                 if isinstance(h, urllib.request.ProxyHandler) and h.proxies]
    assert not com_proxy, com_proxy


def test_o_opener_padrao_realmente_leria_o_proxy_do_ambiente(monkeypatch):
    """A mordida do teste acima: sem ela, "nenhum ProxyHandler com proxies"
    passaria mesmo se `urllib` nunca lesse o ambiente, e o teste estaria
    provando nada."""
    monkeypatch.setenv("https_proxy", "http://proxy.interno:3128")
    padrao = urllib.request.build_opener()
    com_proxy = [h.proxies for h in padrao.handlers
                 if isinstance(h, urllib.request.ProxyHandler) and h.proxies]
    assert com_proxy, "urllib nao leu o proxy do ambiente — teste inutil"

    sem_proxy = TransporteUrllib()._abridor("http://127.0.0.1:5178/")
    assert not [h for h in sem_proxy.__self__.handlers
                if isinstance(h, urllib.request.ProxyHandler) and h.proxies]


@pytest.mark.parametrize("url", [
    "https://api.exemplo.com/",
    "https://127.0.0.1.exemplo.com/",
    "https://localhost.exemplo.com/",
])
def test_alvo_publicado_continua_honrando_o_proxy_do_ambiente(url):
    """O bypass e restrito a loopback de verdade. Um host que apenas se
    PARECE com loopback (`127.0.0.1.exemplo.com`) sai pela rede normalmente
    — o contrario seria um jeito de escapar do proxy corporativo escolhendo
    o nome do dominio.

    Nao e hipotese: a primeira versao do bypass casava por prefixo de string
    e deixava passar as duas ultimas URLs desta lista. Foi este teste que
    achou."""
    assert not e_loopback(url)
    assert not host_e_loopback(url)
    assert TransporteUrllib()._abridor(url) is urllib.request.urlopen


# ------------------------------------------- healthcheck e prova de VIDA

class _ClienteFalso:
    """Registra o que o healthcheck pediu, e responde como um dev server de
    SPA: 200 para qualquer Accept que aceite html, 404 para o resto."""

    def __init__(self):
        self.pedidos = []

    def requisitar(self, metodo, rota, identidade=None, extra_headers=None,
                   **kw):
        from pse.trabalho_a.cliente import Resposta
        headers = {"Accept": "application/json"}
        headers.update(extra_headers or {})
        self.pedidos.append(headers)
        aceita = headers["Accept"]
        ok = "*/*" in aceita or "text/html" in aceita
        return Resposta(200 if ok else 404, "", {}), None


def test_healthcheck_nao_negocia_conteudo():
    """O padrao do cliente e `application/json`, que serve para API e REPROVA
    um alvo web: o dev server do Vite devolve 404 para `/` quando o Accept
    nao inclui html. Healthcheck e prova de VIDA, nao negociacao de conteudo
    — pedir um tipo especifico transforma uma preferencia da suite em
    criterio de disponibilidade do alvo.
    """
    ctx = Contexto("/tmp")
    cliente = _ClienteFalso()
    ctx.exigir_alvo_saudavel(cliente, {"healthcheck": "/"})
    assert cliente.pedidos == [{"Accept": "*/*"}]
    assert ctx._saude == 200


def test_healthcheck_com_accept_json_teria_reprovado_o_alvo_de_pe():
    """A mordida: prova que o cliente falso reproduz mesmo o comportamento
    do Vite, e portanto que o teste acima nao passa por acidente."""
    cliente = _ClienteFalso()
    resposta, _ = cliente.requisitar("GET", "/", identidade="anonima")
    assert resposta.status == 404


def test_alvo_realmente_caido_continua_bloqueando():
    """A correcao nao pode ter afrouxado o gate: 503 segue sendo 503, e
    nenhuma sonda sai contra alvo que nao esta de pe."""
    class Caido(_ClienteFalso):
        def requisitar(self, *a, **kw):
            from pse.trabalho_a.cliente import Resposta
            super().requisitar(*a, **kw)
            return Resposta(503, "", {}), None

    ctx = Contexto("/tmp")
    cliente = Caido()
    with pytest.raises(CheckIndeterminado) as e:
        ctx.exigir_alvo_saudavel(cliente, {"healthcheck": "/"})
    assert "503" in str(e.value)
    # E o veredito e MEMORIZADO: o segundo check nao toca a rede de novo.
    with pytest.raises(CheckIndeterminado):
        ctx.exigir_alvo_saudavel(cliente, {"healthcheck": "/"})
    assert len(cliente.pedidos) == 1
