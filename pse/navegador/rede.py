"""NetworkLog — o contrato da observacao de rede. Adaptado de danzeroum/qa-suite (MIT).

IMUTAVEL DE PROPOSITO. Os tres checks dinamicos compartilham UMA observacao
do alvo (uma carga de pagina por execucao, nao tres), e um log mutavel
deixaria o primeiro check a rodar alterar o que o segundo enxerga. O bug
seria silencioso e dependente de ordem — a pior combinacao possivel num
artefato que existe para ser prova.

O que a PSE acrescentou ao contrato da qa-suite:

  * `html` — o corpo entregue na navegacao principal. P-23 precisa dele
    para ver PII em `href` e em `<form method=get>`, e le-lo aqui, uma vez,
    evita uma segunda visita ao alvo.
  * `sanitizado()` — a projecao que vai para o laudo. A evidencia dinamica
    NAO pode vazar o que ela prova: um achado de "CPF na query string" que
    carimbasse o CPF no laudo teria acabado de publicar o dado do titular
    num artefato que circula por CI, anexo de PR e e-mail.

`host_de` e `host_casa` vieram inteiros: o casamento por SUFIXO DE ROTULO
(nunca por substring) e o que impede `meugoogle-analytics.com` de casar com
`google-analytics.com`.
"""
from dataclasses import dataclass, field
from urllib.parse import urlsplit


def host_de(url: str) -> str:
    """Host em minusculas de uma URL http(s); "" para data:, blob:, about:blank."""
    try:
        parsed = urlsplit(str(url))
    except ValueError:
        return ""
    if parsed.scheme not in ("http", "https"):
        return ""
    return (parsed.hostname or "").lower().rstrip(".")


def _normalizar(dominio: str) -> str:
    dominio = str(dominio).strip().lower().rstrip(".")
    for prefixo in ("*.", "www."):
        if dominio.startswith(prefixo):
            dominio = dominio[len(prefixo):]
    return dominio


def host_casa(host: str, dominio: str) -> bool:
    """True se `host` e o proprio dominio ou um subdominio dele.

    Casamento por sufixo de ROTULO, nunca por substring: `meugoogle-
    analytics.com` nao casa com `google-analytics.com`. E a mesma licao que
    `scan.nome_casa` aprendeu no estatico, no outro eixo.
    """
    dominio = _normalizar(dominio)
    host = str(host).strip().lower().rstrip(".")
    if not host or not dominio:
        return False
    return host == dominio or host.endswith("." + dominio)


@dataclass(frozen=True)
class RequisicaoObservada:
    url: str
    tipo: str = ""


@dataclass(frozen=True)
class RecursoObservado:
    url: str
    status: int = 0
    tipo: str = ""
    da_origem: bool = False


@dataclass(frozen=True)
class CookieObservado:
    """Um cookie do contexto apos o load.

    Campos com default para que um teste possa fabricar um log declarando
    so o que interessa aquela pergunta — sem isso, cada teste novo passaria
    a depender da forma inteira do objeto do Playwright.
    """
    name: str
    domain: str = ""
    path: str = "/"
    httpOnly: bool = False
    secure: bool = False
    sameSite: str = ""
    valor_presente: bool = True

    @classmethod
    def de_playwright(cls, bruto: dict) -> "CookieObservado":
        """Do dicionario do Playwright — SEM o valor.

        O valor do cookie nunca entra no objeto. Um cookie de sessao E uma
        credencial: guarda-lo em memoria para depois lembrar de nao
        serializa-lo e confiar na disciplina do proximo consumidor de
        `executar()`. Aqui ele simplesmente nao existe.
        """
        return cls(
            name=str(bruto.get("name", "")),
            domain=str(bruto.get("domain", "")),
            path=str(bruto.get("path", "/")),
            httpOnly=bool(bruto.get("httpOnly", False)),
            secure=bool(bruto.get("secure", False)),
            sameSite=str(bruto.get("sameSite", "") or ""),
            valor_presente=bool(bruto.get("value")),
        )


@dataclass(frozen=True)
class NetworkLog:
    """O que a rede revelou ao carregar o alvo, uma vez, em contexto virgem."""

    url: str
    requisicoes: tuple = ()
    cookies: tuple = ()
    recursos: tuple = ()
    html: str = ""
    engine: str = ""
    # Preenchido quando a observacao NAO aconteceu (Playwright ausente, alvo
    # fora do ar). Log vazio e log-que-nao-foi-feito nunca se confundem.
    motivo_de_ausencia: str = field(default="")

    @property
    def observou(self) -> bool:
        return not self.motivo_de_ausencia

    def hosts(self) -> list:
        """Hosts http(s) unicos contactados, em ordem de primeiro contato."""
        vistos: dict = {}
        for req in self.requisicoes:
            host = host_de(req.url)
            if host:
                vistos.setdefault(host, None)
        return list(vistos)

    def de_terceiros(self) -> list:
        origem = host_de(self.url)
        return [r for r in self.requisicoes
                if host_de(r.url) and not host_casa(host_de(r.url), origem)]

    def rastreadores(self, dominios, allowlist=()) -> list:
        """Requisicoes a rastreador conhecido e nao liberado.

        A allowlist VENCE a lista: e a decisao documentada do controlador
        (uma tag gerenciada que ja respeita consentimento, por exemplo), e o
        check nao pode ser mais esperto que a decisao registrada.
        """
        allowlist = tuple(allowlist or ())
        saida = []
        for req in self.requisicoes:
            host = host_de(req.url)
            if not host:
                continue
            if any(host_casa(host, a) for a in allowlist):
                continue
            if any(host_casa(host, d) for d in dominios):
                saida.append(req)
        return saida

    def hosts_rastreadores(self, dominios, allowlist=()) -> list:
        return sorted({host_de(r.url)
                       for r in self.rastreadores(dominios, allowlist)})

    def nomes_de_cookie(self) -> list:
        return [c.name for c in self.cookies]

    def sanitizado(self) -> dict:
        """A projecao que pode ir para o laudo.

        Passa pelo MESMO sanitizador do resto da suite, na ORIGEM. A
        evidencia dinamica prova um vazamento; publicar o dado vazado junto
        transformaria o laudo no segundo vazamento — e este circula por CI,
        anexo de PR e caixa de e-mail.
        """
        from pse.sanitize import sanitizar, sanitizar_url
        return {
            "url": sanitizar_url(self.url),
            "engine": self.engine,
            "observou": self.observou,
            "motivo_de_ausencia": self.motivo_de_ausencia or None,
            "hosts_contactados": [sanitizar(h) for h in self.hosts()],
            "total_requisicoes": len(self.requisicoes),
            # Nome e atributos. Nunca o valor — ele nem chega a existir aqui.
            "cookies": [{"name": sanitizar(c.name), "httpOnly": c.httpOnly,
                         "secure": c.secure, "sameSite": c.sameSite}
                        for c in self.cookies],
        }
