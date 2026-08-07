"""A observacao: abrir o alvo UMA vez e devolver o que a rede revelou.

Adaptado da fixture `network_log` de danzeroum/qa-suite (MIT), com uma
diferenca de forma que vem da arquitetura da PSE: la a observacao e uma
fixture de sessao do pytest, porque a qa-suite roda como bateria de testes;
aqui ela e memorizada no `Contexto`, porque os checks da PSE rodam dentro de
`executar()`, no repositorio do consumidor, sem pytest por perto.

A substancia foi preservada inteira:

  * CONTEXTO VIRGEM. Cookie ou consentimento herdado de uma observacao
    anterior faria o alvo parecer conforme ("ja consentiu antes") — o pior
    falso negativo possivel numa bateria de consentimento previo.
  * ESPERA DEPOIS DO LOAD. Tag de analytics costuma disparar depois do
    evento `load`; observar cedo demais produz aprovacao falsa.
  * SO METADADOS no handler de resposta. Puxar corpo dentro do handler
    faria a pagina inteira residir na RAM sem ninguem ter pedido.
  * INSTRUMENTACAO NAO DERRUBA A OBSERVACAO. Excecao registrando um recurso
    e engolida; excecao carregando o alvo, nao.

UMA observacao por execucao, partilhada pelos tres checks. Nao e so
economia: tres cargas de pagina contra um alvo dinamico poderiam discordar
entre si, e o laudo teria tres verdades sobre o mesmo instante.
"""
import os

from pse.model import CheckIndeterminado
from pse.navegador.engines import (PlaywrightAusente, engines_configurados,
                                   exigir_playwright)
from pse.navegador.rede import (CookieObservado, NetworkLog, RecursoObservado,
                                RequisicaoObservada, host_casa, host_de)

ESPERA_APOS_LOAD_MS = 2_000
TIMEOUT_NAVEGACAO_MS = 60_000

# Binario do navegador fora do registro do Playwright. Existe porque em
# ambiente conteinerizado o browser costuma vir na imagem, e a versao do
# pacote Python nem sempre casa com o build instalado — sem esta valvula, a
# unica saida seria baixar um segundo navegador de centenas de MB.
# Vazio (o normal) deixa o Playwright resolver sozinho.
ENV_EXECUTAVEL = "PSE_BROWSER_EXECUTABLE"


def observar(url: str, engine: str = None, user_agent: str = None,
             espera_ms: int = ESPERA_APOS_LOAD_MS, data=None) -> NetworkLog:
    """Carrega `url` em contexto virgem e devolve o NetworkLog.

    Entrada de baixo nivel do motor: NAO verifica autorizacao. Quem chama a
    partir de um check passa antes por `trabalho_a.base.exigir_alvo` — e a
    porta unica dos cinco degraus. Este modulo e usado direto apenas pelos
    testes do proprio motor, contra o alvo de fixture local.
    """
    sync_api = exigir_playwright()          # PlaywrightAusente -> instrucao
    engine = engine or engines_configurados(data=data)[0]

    requisicoes, recursos = [], []
    origem = host_de(url)

    executavel = os.environ.get(ENV_EXECUTAVEL) or None
    with sync_api.sync_playwright() as p:
        try:
            navegador = getattr(p, engine).launch(
                **({"executable_path": executavel} if executavel else {}))
        except Exception as e:              # engine sem binario instalado
            raise PlaywrightAusente(
                f"engine `{engine}` indisponivel: rode "
                f"`python -m playwright install {engine}` ({e}). Engine "
                f"ausente NUNCA conta como aprovacao.") from e

        # Contexto novo e virgem: ver docstring do modulo.
        opcoes = {"user_agent": user_agent} if user_agent else {}
        contexto = navegador.new_context(**opcoes)
        contexto.on("request", lambda r: requisicoes.append(
            RequisicaoObservada(r.url, getattr(r, "resource_type", "") or "")))

        def registrar_resposta(resposta):
            try:
                u = resposta.url
                recursos.append(RecursoObservado(
                    url=u, status=int(resposta.status),
                    tipo=str((resposta.headers or {}).get("content-type", "")),
                    da_origem=bool(host_de(u) and host_casa(host_de(u), origem))))
            except Exception:
                pass        # instrumentacao nao pode derrubar a observacao

        contexto.on("response", registrar_resposta)
        pagina = contexto.new_page()
        try:
            pagina.goto(url, wait_until="load", timeout=TIMEOUT_NAVEGACAO_MS)
            if espera_ms:
                pagina.wait_for_timeout(espera_ms)
            html = pagina.content()
            cookies = tuple(CookieObservado.de_playwright(c)
                            for c in contexto.cookies())
        except Exception as e:
            raise CheckIndeterminado(
                f"nao foi possivel observar {url}: {type(e).__name__}: "
                f"{str(e).splitlines()[0][:160]}") from e
        finally:
            contexto.close()
            navegador.close()

    return NetworkLog(url=url, requisicoes=tuple(requisicoes),
                      cookies=cookies, recursos=tuple(recursos),
                      html=html, engine=engine)


def ausente(url: str, motivo: str, engine: str = "") -> NetworkLog:
    """Um log que declara NAO ter observado. Nunca se confunde com log vazio."""
    return NetworkLog(url=url, engine=engine, motivo_de_ausencia=motivo)
