"""Alvo de fixture — um servidor real, para o navegador visitar de verdade.

Inspirado no `fixture_target` de danzeroum/qa-suite (MIT), reduzido ao que a
Fase 1 da camada dinamica precisa provar.

POR QUE UM SERVIDOR E NAO UM NetworkLog FABRICADO. Os dois existem, e cada
um prova uma coisa diferente:

  * NetworkLog fabricado prova a LOGICA do check — a regra que separa
    achado de nao-achado. E barato e roda em qualquer maquina.
  * Este servidor prova o MOTOR — que o Playwright sobe, que o contexto
    nasce virgem, que a espera pos-load pega a tag que dispara tarde, que os
    cookies chegam com os atributos que o navegador de fato viu.

A licao do `dist/` no .gitignore vale aqui, invertida: ambiente local de pe
nao prova alvo respondendo. Um check dinamico validado so contra objeto
fabricado e um check que nunca abriu navegador — e ninguem descobriria ate
o primeiro alvo real.

DUAS ROTAS:
  /sujo   dispara "rastreador", grava cookie de analytics e cookie de sessao
          sem atributo nenhum, e publica CPF na query de um link
  /limpo   nao dispara nada antes do aceite, cookie de sessao completo,
          sem PII em URL

O "rastreador" e servido pelo PROPRIO processo, mas por um HOST DIFERENTE:
a pagina e servida em `127.0.0.1` e a tag e buscada em `localhost`. Sao o
mesmo computador e nomes distintos, entao a deteccao de terceiro e exercida
de verdade — o check ve um host que nao e o da origem, que e exatamente o
fato que ele existe para reconhecer.

Chamar `google-analytics.com` de verdade seria a suite fazendo o que ela
audita: contactar terceiro sem base legal, a partir da maquina de quem roda
o teste. O teste declara `localhost` como rastreador na sua propria regua
sintetica; a regua de producao em `pse/data/rastreadores.yaml` segue
intocada.
"""
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# CPF e e-mail sinteticos, plantados para a suite encontrar (D-02/D-03).
CPF_PLANTADO = "529.982.247-25"
EMAIL_PLANTADO = "maria@titular.example.org"

PAGINA_SUJA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>alvo sujo</title>
<!-- A tag dispara ANTES de qualquer aceite, e depois do load: e o vetor
     que uma observacao apressada nao veria. -->
<script>
  setTimeout(function () {
    var s = document.createElement('script');
    s.src = '__TERCEIRO__/tag-de-analytics.js';
    document.head.appendChild(s);
  }, 200);
</script>
</head><body>
<h1>Portal do cliente</h1>
<div id="banner">Usamos cookies. <button id="aceitar">Aceitar</button></div>
<a id="fatura" href="/fatura?cpf=__CPF__&amp;email=__EMAIL__">
  Minha fatura</a>
<form id="busca" method="get" action="/buscar">
  <input name="cpf" value="">
  <input name="telefone" value="">
  <button type="submit">Buscar</button>
</form>
</body></html>
"""

PAGINA_LIMPA = """<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>alvo limpo</title>
</head><body>
<h1>Portal do cliente</h1>
<div id="banner">Usamos cookies. <button id="aceitar">Aceitar</button></div>
<a id="fatura" href="/fatura?id=9f1c2e3a-0000-4000-8000-000000000000">
  Minha fatura</a>
<form id="busca" method="post" action="/buscar">
  <input name="termo" value="">
  <button type="submit">Buscar</button>
</form>
</body></html>
"""


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *_):
        pass                      # silencio: o alvo nao polui a saida do pytest

    def _responder(self, corpo: str, cookies=(), tipo="text/html; charset=utf-8"):
        dados = corpo.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(dados)))
        for cookie in cookies:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(dados)

    # Base do "terceiro" — outro HOST, mesmo processo. Definida pelo
    # AlvoDeFixture antes de servir.
    base_terceiro = ""

    def _pagina_suja(self) -> str:
        return (PAGINA_SUJA
                .replace("__TERCEIRO__", self.base_terceiro)
                .replace("__CPF__", CPF_PLANTADO)
                .replace("__EMAIL__", EMAIL_PLANTADO))

    def do_GET(self):
        rota = self.path.split("?")[0]

        if rota == "/health":
            self._responder("{}", tipo="application/json")

        elif rota in ("/", "/sujo"):
            self._responder(self._pagina_suja(), cookies=[
                # Cookie de sessao sem HttpOnly, sem Secure, sem SameSite.
                "sessionid=abc123; Path=/",
                # Analytics gravado no primeiro load, antes de qualquer aceite.
                "_ga=GA1.2.999.888; Path=/",
            ])

        elif rota == "/limpo":
            self._responder(PAGINA_LIMPA, cookies=[
                "sessionid=abc123; Path=/; HttpOnly; Secure; SameSite=Lax",
                "cookieconsent=pendente; Path=/; SameSite=Lax",
            ])

        elif rota == "/tag-de-analytics.js":
            # O "terceiro". Servido daqui de proposito: bater no Google de
            # verdade seria a suite cometendo o que ela audita.
            self._responder("window.__tag=1;", tipo="application/javascript")

        else:
            self._responder("<html><body>ok</body></html>")


class AlvoDeFixture:
    """Servidor efemero em loopback. `with AlvoDeFixture() as alvo: ...`"""

    #: Host pelo qual a tag de "terceiro" e buscada. Mesmo processo, nome
    #: diferente do da origem — e o que exercita a deteccao de terceiro.
    HOST_TERCEIRO = "localhost"

    def __init__(self, host="127.0.0.1"):
        self._servidor = ThreadingHTTPServer((host, 0), _Handler)
        self.host, self.porta = self._servidor.server_address[:2]
        _Handler.base_terceiro = f"http://{self.HOST_TERCEIRO}:{self.porta}"
        self._thread = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.porta}"

    @property
    def host_terceiro(self) -> str:
        return self.HOST_TERCEIRO

    def url(self, rota: str) -> str:
        return f"{self.base_url}{rota}"

    def __enter__(self) -> "AlvoDeFixture":
        self._thread = threading.Thread(target=self._servidor.serve_forever,
                                        daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._servidor.shutdown()
        self._servidor.server_close()
        if self._thread:
            self._thread.join(timeout=5)
