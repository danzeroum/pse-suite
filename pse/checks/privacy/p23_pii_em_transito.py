"""P-23 — PII na URL, vista no HTML que o alvo de fato entregou.

Par dinamico de P-14. O estatico le o codigo do front e acha
`"?email=" + user.email`; este le a pagina RENDERIZADA e acha o mesmo
vazamento venha ele de onde vier — de um template do servidor, de um link
montado no build, de um componente de terceiro. P-14 nao alcanca nenhum
desses caminhos, e sao a maioria.

TRES SUPERFICIES, tres vazamentos distintos:

  QUERY STRING    vai inteira para o log do servidor, para o log do proxy,
                  para o historico do navegador — e para o cabecalho
                  `Referer` da proxima requisicao, INCLUSIVE as de
                  terceiros. Um CPF numa URL vaza para o analytics sem que
                  ninguem tenha mandado o CPF para o analytics.
  FORM METHOD=GET publica o que o titular DIGITOU na barra de enderecos e
                  no historico. O campo se chama `cpf` porque e um CPF.
  REFERER         consequencia dos dois acima, e o motivo de a query ser
                  pior do que parece: o vazamento nao para na sua
                  infraestrutura.

O QUE VAI PARA O LAUDO E O NOME DO PARAMETRO, NUNCA O VALOR. Um achado de
"CPF na query string" que carimbasse o CPF no laudo teria acabado de
publicar o dado do titular num artefato que circula por CI, anexo de PR e
caixa de e-mail — a evidencia viraria o segundo vazamento, maior que o
primeiro, porque distribuido. O `Finding` ainda passa pelo sanitizador na
origem; nao depender disso e a diferenca entre uma trava e uma esperanca.

D-08: identificador OPACO na URL (UUID, hash, id de pedido) nao dispara.
E o padrao correto, e puni-lo empurraria o time para o oposto do que se
quer.
"""
import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit

from pse.engine.registry import check
from pse.navegador import analise
from pse.model import Finding, Severidade
from pse.trabalho_a.base import exigir_observacao

BASE = "LGPD Art. 46 + Art. 6o VII (seguranca e prevencao)"
REGUA = "rastreadores"


class _Coletor(HTMLParser):
    """Links e formularios GET da pagina entregue.

    Parser de verdade, nao regex sobre o HTML: `href` dentro de um
    comentario ou de um bloco de texto nao e link, e o D-01 vale igual na
    camada dinamica — o fato e o elemento, nao a mencao.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs, self.forms_get = [], []
        self._form_atual = None

    def handle_starttag(self, tag, attrs):
        atributos = {k.lower(): (v or "") for k, v in attrs}
        if tag == "a" and atributos.get("href"):
            self.hrefs.append(atributos["href"])
        elif tag == "form":
            metodo = atributos.get("method", "get").strip().lower()
            self._form_atual = [] if metodo == "get" else None
        elif tag == "input" and self._form_atual is not None:
            nome = atributos.get("name")
            if nome:
                self._form_atual.append(nome)

    def handle_endtag(self, tag):
        if tag == "form":
            if self._form_atual:
                self.forms_get.append(list(self._form_atual))
            self._form_atual = None

    def close(self):
        super().close()
        # `</form>` ausente e HTML real: nao perder o formulario por isso.
        if self._form_atual:
            self.forms_get.append(list(self._form_atual))


def _pii(ctx) -> set:
    """A regua compartilhada. P-23 nao tem lista propria de PII."""
    campos = {t.lower() for grupo in ctx.data["pii-patterns"].values()
              for t in grupo}
    return campos | {t.lower() for t in ctx.data["sensitive-fields"]["sensiveis"]}


def _parametros_de_pii(url: str, pii: set) -> list:
    try:
        query = urlsplit(url).query
    except ValueError:
        return []
    if not query:
        return []
    return sorted({nome for nome in parse_qs(query, keep_blank_values=True)
                   if nome.lower() in pii})


RX_PII_NA_ROTA = re.compile(r"[?&]([A-Za-z_][A-Za-z0-9_-]*)=")


@check("P-23", "privacy", "PII em transito na URL", base_legal=BASE)
def pii_em_transito(ctx):
    log = exigir_observacao(ctx, "passive")   # 5 degraus + navegador
    analise.relatar_observacao(ctx, log)

    pii = _pii(ctx)
    superficies = ctx.data[REGUA]["superficies_de_transito"]

    coletor = _Coletor()
    coletor.feed(log.html or "")
    coletor.close()

    achados = {}          # superficie -> conjunto de NOMES de parametro

    # 1. a propria URL observada
    for nome in _parametros_de_pii(log.url, pii):
        achados.setdefault("query", set()).add(nome)
    # 2. links entregues na pagina
    for href in coletor.hrefs:
        for nome in _parametros_de_pii(href, pii):
            achados.setdefault("query", set()).add(nome)
    # 3. requisicoes que o navegador de fato emitiu
    for req in log.requisicoes:
        for nome in _parametros_de_pii(req.url, pii):
            achados.setdefault("query", set()).add(nome)
    # 4. formularios GET
    for campos in coletor.forms_get:
        for nome in campos:
            if nome.lower() in pii:
                achados.setdefault("formulario_get", set()).add(nome)

    if not achados:
        return []

    # A query de terceiro e o vazamento por Referer: so vale nomear quando
    # ha, de fato, terceiro contactado.
    if "query" in achados and log.de_terceiros():
        achados.setdefault("referer", set()).update(achados["query"])

    partes = [f"{superficies.get(sup, sup)} — parametro(s) "
              f"{sorted(nomes)}" for sup, nomes in sorted(achados.items())]

    return [Finding(
        check_id="P-23", pack="privacy", severidade=Severidade.ALTO,
        titulo=f"Dado pessoal em transito na URL "
               f"({', '.join(sorted(achados))})",
        descricao=(
            "Observado na pagina entregue: " + "; ".join(partes) + ". "
            "Somente os NOMES dos parametros sao registrados aqui — o valor "
            "observado nao entra no laudo, porque publicar o dado que o "
            "achado denuncia transformaria a evidencia num segundo "
            "vazamento, este distribuido por CI e por anexo de PR. "
            "P-14 le o codigo do front e nao alcanca link montado em "
            "template do servidor, no build ou por componente de terceiro — "
            "que sao a maioria dos casos."),
        recomendacao=(
            "Trocar o identificador da URL por um opaco (UUID, id de pedido) "
            "e mover o dado para o corpo de um POST. Formulario que recebe "
            "dado pessoal usa `method=post`. Onde a URL nao puder mudar, "
            "aplicar `Referrer-Policy: no-referrer` — mitiga o vazamento "
            "para terceiro, mas nao o log do proprio servidor."),
        base_legal=BASE,
        arquivo=log.url, linha=None,
        trace={"superficies": {sup: sorted(nomes)
                               for sup, nomes in achados.items()},
               "observacao": log.sanitizado()})]
