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
    """Uma RESPOSTA observada: metadados, cabecalhos e — as vezes — o corpo.

    O corpo e capturado DURANTE a observacao, e nao sob demanda como na
    qa-suite, por uma diferenca de arquitetura: la o contexto do navegador
    fica vivo enquanto o teste roda, entao `ler_corpo` pode ir busca-lo; aqui
    a observacao e memorizada no Contexto e o navegador ja fechou quando os
    checks rodam. Capturar depois seria uma segunda visita ao alvo.

    Por isso a captura e SELETIVA e com TETO: so os tipos que algum check
    varre, e so ate `TETO_CORPO`. Guardar todo asset de uma pagina em RAM
    seria pagar caro por bytes que ninguem le.

    `motivo_nao_lido` preenchido significa NAO AVALIADO — que nunca e o
    mesmo que limpo. E o check que precisa dizer isso no laudo; um recurso
    grande demais nao pode virar atestado de conformidade.
    """
    url: str
    status: int = 0
    tipo: str = ""
    da_origem: bool = False
    headers: tuple = ()
    corpo: bytes = b""
    motivo_nao_lido: str = ""

    def cabecalho(self, nome: str) -> str:
        """Valor do cabecalho, em minusculas na chave. "" se ausente."""
        alvo = str(nome).strip().lower()
        for chave, valor in self.headers:
            if str(chave).strip().lower() == alvo:
                return str(valor)
        return ""

    @property
    def avaliavel(self) -> bool:
        return bool(self.corpo) and not self.motivo_nao_lido

    @property
    def esquema(self) -> str:
        try:
            return urlsplit(str(self.url)).scheme.lower()
        except ValueError:
            return ""

    def texto(self) -> str:
        """Corpo como texto. Bytes indecodificaveis nao derrubam nada."""
        if not self.avaliavel:
            return ""
        return self.corpo.decode("utf-8", errors="replace")


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

    def indicios_de_dev_server(self, marcas) -> list:
        """Caminhos servidos que denunciam modo de desenvolvimento.

        Ver `marcas_de_dev_server` em `pse/data/servido-ao-cliente.yaml`: o
        que a camada dinamica observa depende inteiramente de QUEM serviu, e
        um dev server nao serve o mesmo artefato que a producao.
        """
        vistos = []
        for r in self.recursos:
            baixo = str(r.url).lower()
            for m in marcas:
                if str(m).lower() in baixo and m not in vistos:
                    vistos.append(m)
        return vistos

    def sanitizado(self, marcas_de_dev=(), artefato_declarado="") -> dict:
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
            # UMA superficie, e o laudo tem de dizer qual. A camada dinamica
            # carrega a pagina de UM endereco; qualquer outra rota da mesma
            # origem NAO foi observada. No btv isso importou: o alvo serve
            # DUAS SPAs — o produto na raiz e um console em `/dev` — e medir
            # so a raiz e apresentar meia cobertura como inteira.
            "superficie_observada": sanitizar_url(self.url),
            "nota_de_superficie": (
                "Os checks dinamicos observaram ESTE endereco. Nenhuma outra "
                "rota da mesma origem foi carregada: ausencia de achado aqui "
                "nao diz nada sobre elas. Para cobrir outra superficie, rode "
                "de novo com `base_url` apontando para ela."),
            **_bloco_de_artefato(self, marcas_de_dev, artefato_declarado),
        }


def _bloco_de_artefato(log, marcas, declarado="") -> dict:
    """Cruza o que foi DECLARADO com o que foi OBSERVADO.

    DUAS PERGUNTAS, e junta-las seria repetir o erro do mapa de cobertura
    numa terceira escala.

      declarado  o operador afirma, na atestacao, contra que artefato esta
                 medindo. A suite NAO consegue descobrir isso sozinha: um
                 `vite preview` e um deploy real servem bundle igualmente
                 minificado, e inferir "producao" da ausencia de indicios
                 seria a suite inventando um fato sobre o alvo.
      observado  indicios de dev server no que foi servido. Isso a suite ve.

    O cruzamento e o que interessa: `producao` DECLARADO com indicios de dev
    server OBSERVADOS e contradicao, e ela aparece em voz alta. Quem apontou
    a atestacao de producao para um `vite dev` precisa saber antes de ler os
    achados como se fossem do artefato publicado.
    """
    indicios = log.indicios_de_dev_server(marcas) if marcas else []
    saida = {
        "artefato_declarado": declarado or "nao_declarado",
        "servidor_de_desenvolvimento": bool(indicios),
    }
    if indicios:
        saida["indicios_de_dev_server"] = indicios
        saida["nota_de_dev_server"] = (
            "O endereco observado responde como SERVIDOR DE DESENVOLVIMENTO. "
            "Modulo sem minificar, sourcemap embutido e ausencia de "
            "cabecalhos de borda sao comportamento NORMAL desse modo — e nao "
            "sao, por si, propriedade do artefato publicado. Os achados desta "
            "execucao descrevem o que foi servido AQUI; para afirmar algo "
            "sobre producao, observe o servidor de producao.")
    if declarado == "producao" and indicios:
        saida["contradicao_de_artefato"] = (
            "A atestacao declara `artefato: producao` e o alvo respondeu com "
            f"indicios de servidor de desenvolvimento ({', '.join(indicios)}). "
            "Uma das duas coisas esta errada, e o laudo nao adivinha qual — "
            "mas os achados NAO podem ser lidos como propriedade do artefato "
            "publicado enquanto a contradicao existir.")
    if declarado == "producao" and not indicios:
        saida["nota_de_producao"] = (
            "A atestacao declara `artefato: producao` e nada no que foi "
            "servido contradiz isso. A suite NAO verifica a declaracao — ela "
            "so registra que nao viu indicio contrario. O que ficou de fora "
            "desta observacao (ingress, proxy, WAF, CDN) segue sem ser "
            "observado, e ausencia de observacao nunca e atestado.")
    if not declarado:
        saida["nota_de_artefato"] = (
            "A atestacao nao declara `artefato`. O laudo diz o que observou e "
            "nao afirma se isso e o artefato publicado — declarar "
            "`artefato: producao` ou `artefato: desenvolvimento` no alvo faz "
            "essa distincao entrar no laudo.")
    return saida
