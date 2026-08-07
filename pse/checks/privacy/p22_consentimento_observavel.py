"""P-22 — o consentimento como ele e OBSERVADO, nao como esta declarado.

P-13 le o JSX e pergunta se a caixa nasce marcada. Este carrega a pagina
num navegador virgem e pergunta outra coisa, que nenhuma leitura de codigo
responde: **o que ja aconteceu quando o titular ainda nao clicou em nada?**

E a pergunta que separa politica de pratica. Um repositorio pode ter o
banner mais correto do mundo no componente e mesmo assim disparar a tag no
`index.html`, num script de terceiro, numa tag gerenciada que alguem
adicionou pelo painel — nenhum desses caminhos passa pelo codigo que o
estatico le. Art. 7o I e Art. 8o pedem consentimento PREVIO: o que dispara
antes do clique nao tem base legal, e so o navegador ve isso.

DOIS SINAIS, mesma pergunta:
  1. REQUISICAO a rastreador conhecido antes de qualquer interacao.
  2. COOKIE nao essencial ja gravado no primeiro load.

SEVERIDADE: ALTO, e a escolha e deliberada. O nome do host NAO prova a
finalidade do tratamento — um `googletagmanager.com` pode estar servindo
uma tag que ja respeita consentimento. E sinal forte, nao prova cabal, e
CRITICO aqui puniria com o peso maximo uma inferencia que admite excecao. A
qa-suite, de onde este check vem, marca o mesmo indicio como xfail; aqui
ele entra no laudo com a severidade que o indicio merece — visivel, e sem
fingir certeza que nao tem.

D-08: cookie essencial (sessao, CSRF, idioma, o proprio registro de
consentimento) NUNCA vira achado. Exigir opt-in para o cookie que mantem a
sessao de pe seria cobrar uma coisa que a lei nao pede e que quebraria o
produto — e o time aprenderia a ignorar o pack.

A allowlist do consumidor VENCE a regua: e a decisao documentada do
controlador, e o check nao pode ser mais esperto que a decisao registrada.
"""
from pse.engine.registry import check
from pse.navegador import analise
from pse.model import Finding, Severidade
from pse.navegador.rede import host_de
from pse.trabalho_a.base import exigir_observacao

BASE = "LGPD Art. 7o I e Art. 8o (consentimento previo e especifico)"
REGUA = "rastreadores"


def _r(ctx, chave):
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def _allowlist(ctx) -> list:
    """Hosts que o controlador declarou como decididos. Vem da config."""
    alvo = (ctx.config or {}).get("target") or {}
    return [str(h).lower() for h in (alvo.get("trackers_allowlist") or [])]


def _cookies_nao_essenciais(log, nao_essenciais, essenciais) -> list:
    achados = []
    for cookie in log.cookies:
        nome = cookie.name.lower()
        if any(nome.startswith(e) for e in essenciais):
            continue                     # D-08: o produto precisa dele
        if any(nome.startswith(p) for p in nao_essenciais):
            achados.append(cookie.name)
    return sorted(set(achados))


def _registrar(ctx, log):
    """A observacao entra no laudo — SANITIZADA, e uma vez so."""
    analise.relatar_observacao(ctx, log)


@check("P-22", "privacy", "Consentimento observavel", base_legal=BASE)
def consentimento_observavel(ctx):
    log = exigir_observacao(ctx, "passive")   # 5 degraus + navegador
    _registrar(ctx, log)

    dominios = _r(ctx, "rastreadores")
    allowlist = _allowlist(ctx)
    hosts = log.hosts_rastreadores(dominios, allowlist)
    cookies = _cookies_nao_essenciais(
        log, _r(ctx, "cookies_nao_essenciais"), _r(ctx, "cookies_essenciais"))

    if not hosts and not cookies:
        return []

    sinais = []
    if hosts:
        sinais.append(f"requisicao a rastreador conhecido: {hosts}")
    if cookies:
        sinais.append(f"cookie nao essencial ja gravado: {cookies}")

    return [Finding(
        check_id="P-22", pack="privacy", severidade=Severidade.ALTO,
        titulo=f"Tratamento antes do consentimento em `{host_de(log.url)}`",
        descricao=(
            "No PRIMEIRO carregamento da pagina, sem nenhuma interacao com o "
            "banner, ja se observou: " + "; ".join(sinais) + ". O Art. 7o I "
            "pede consentimento PREVIO — o que dispara antes do clique nao "
            "tem base legal, e IP e identificador de dispositivo ja sairam. "
            "Nenhuma leitura de codigo alcanca isto: a tag pode vir do "
            "index.html, de um script de terceiro ou de uma tag gerenciada "
            "adicionada pelo painel, e so o navegador ve. "
            "LIMITE DECLARADO: o nome do host nao prova a finalidade do "
            "tratamento — e sinal forte, nao prova cabal, e por isso ALTO e "
            "nao CRITICO."),
        recomendacao=(
            "Carregar tag de medicao APENAS depois do aceite registrado, e "
            "gravar cookie nao essencial no mesmo momento. Se algum host da "
            "lista ja opera sob consentimento gerenciado, declare-o em "
            "`target.trackers_allowlist` — a decisao documentada do "
            "controlador vence a regua da suite."),
        base_legal=BASE,
        arquivo=log.url, linha=None,
        trace={"observacao": log.sanitizado()})]
