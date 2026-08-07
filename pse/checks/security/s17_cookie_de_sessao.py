"""S-17 — o cookie de sessao como o navegador o recebeu.

Par dinamico de S-09. O estatico procura token guardado no cliente pelo
codigo do front; este olha o que o SERVIDOR mandou e o navegador aceitou —
e sao coisas diferentes, porque o cookie de sessao quase nunca e escrito
pelo front. Ele vem no `Set-Cookie` de um middleware, de um proxy reverso,
de um gateway; nenhum deles esta no repositorio que o estatico varre.

Um cookie de sessao E uma credencial: quem o tem, e o titular, para todos
os efeitos. Os tres atributos exigidos fecham tres portas distintas, e por
isso o achado nomeia qual falta:

  HttpOnly  sem ele, qualquer XSS le o cookie por `document.cookie` e a
            sessao viaja junto com o payload do atacante
  Secure    sem ele, o navegador envia o cookie tambem em http:// — uma
            rede intermediaria captura a sessao inteira em claro
  SameSite  sem ele (ou com `None`), o cookie acompanha requisicao
            originada de outro site, que e a definicao de CSRF

O VALOR DO COOKIE NUNCA E LIDO. `CookieObservado.de_playwright` o descarta
na entrada: um cookie de sessao guardado em memoria para depois lembrar de
nao serializa-lo seria confiar na disciplina do proximo consumidor de
`executar()`. Aqui ele simplesmente nao existe — e por isso nao ha caminho
pelo qual ele chegue ao laudo.

D-08: cookie com os tres atributos nao dispara. Cookie que nao e de sessao
(preferencia de idioma, tema) nao entra no escopo — exigir HttpOnly de um
cookie de idioma que o proprio front precisa ler seria pedir ao time que
quebre o produto para agradar a suite.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a.base import exigir_observacao

BASE = "LGPD Art. 46 (seguranca) + OWASP A05"
REGUA = "rastreadores"


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _e_de_sessao(nome: str, prefixos) -> bool:
    baixo = str(nome).lower()
    return any(baixo.startswith(str(p).lower()) for p in prefixos)


def _faltantes(cookie, exigidos: dict, samesite_fraco) -> list:
    """(atributo, explicacao) do que falta neste cookie.

    O laco vem da REGUA, nao de tres `if` escritos aqui: acrescentar um
    quarto atributo exigido passa a ser uma edicao de YAML, revisavel e
    coberta pelo `catalog_hash`, em vez de uma alteracao de codigo. Foi um
    teste-guarda da propria suite que cobrou isto — `HttpOnly` e `Secure`
    estavam no .py.

    Um atributo esta SATISFEITO quando tem valor e esse valor nao consta da
    lista de valores sem protecao. Isso cobre os dois formatos numa regra
    so: booleano falso (`httpOnly: false`) e string explicitamente
    permissiva (`sameSite: None`) faltam pelo mesmo criterio.
    """
    fracos = {str(v).strip().lower() for v in samesite_fraco}
    faltando = []
    for atributo, explicacao in exigidos.items():
        valor = getattr(cookie, atributo, None)
        satisfeito = bool(valor) and str(valor).strip().lower() not in fracos
        if not satisfeito:
            faltando.append((atributo[0].upper() + atributo[1:], explicacao))
    return faltando


@check("S-17", "security", "Cookie de sessao inseguro", base_legal=BASE)
def cookie_de_sessao(ctx):
    log = exigir_observacao(ctx, "passive")   # 5 degraus + navegador
    ctx.relatorio("observacao_de_rede", log.sanitizado())

    prefixos = _r(ctx, "cookies_de_sessao")
    exigidos = _r(ctx, "atributos_exigidos_em_sessao")
    samesite_fraco = _r(ctx, "samesite_sem_protecao")

    findings = []
    for cookie in log.cookies:
        if not _e_de_sessao(cookie.name, prefixos):
            continue
        faltando = _faltantes(cookie, exigidos, samesite_fraco)
        if not faltando:
            continue                     # D-08: o cookie esta correto
        nomes = [n for n, _ in faltando]
        findings.append(Finding(
            check_id="S-17", pack="security", severidade=Severidade.ALTO,
            titulo=f"Cookie de sessao `{cookie.name}` sem {', '.join(nomes)}",
            descricao=(
                f"O navegador recebeu e aceitou este cookie sem "
                f"{', '.join(nomes)}. " +
                " ".join(f"{n}: {motivo}." for n, motivo in faltando) +
                " Um cookie de sessao E uma credencial — quem o tem e o "
                "titular, para todos os efeitos. E ele quase nunca e escrito "
                "pelo codigo do front: vem do middleware, do proxy reverso ou "
                "do gateway, nenhum deles no repositorio que S-09 varre."),
            recomendacao=(
                "Emitir o cookie com `HttpOnly; Secure; SameSite=Lax` (ou "
                "`Strict`, se nenhum fluxo depende de navegacao entre sites). "
                "`SameSite=None` so com justificativa de integracao "
                "declarada, e sempre com `Secure`."),
            base_legal=BASE,
            arquivo=log.url, linha=None,
            # A evidencia carrega exatamente os atributos que a regua exige:
            # se ela crescer, o trace cresce junto, sem ninguem lembrar.
            # Nunca o VALOR do cookie — ele nao existe neste objeto.
            trace={"cookie": {"name": cookie.name,
                              **{a: getattr(cookie, a, None) for a in exigidos}},
                   "observacao": log.sanitizado()}))
    return findings
