"""Selecao de engine de navegador. Adaptado de danzeroum/qa-suite (MIT).

Por que a lista vem do ambiente e nao do `pse-config.yaml` do consumidor: as
engines a exercitar sao decisao da EXECUCAO — `chromium` no PR para nao
triplicar o CI, matriz completa no noturno — e nao propriedade do alvo
auditado. Fica fora do contrato de Trabalho A de proposito.

A regra que veio junto e nao pode se perder: **engine desconhecida e ERRO**,
nunca filtro silencioso. Um typo (`chromiun`) que degenerasse em "rodou zero
engines e passou" seria a pior forma de verde falso — a que esta suite
inteira existe para impedir.

O vocabulario de engines validas vive em `pse/data/rastreadores.yaml`, como
toda regua curada da PSE.
"""
import os

from pse.model import EntradaInvalida

ENV_ENGINES = "PSE_BROWSER_ENGINES"
ENGINES_PADRAO = ("chromium",)


def engines_validas(data: dict | None = None) -> tuple:
    """Vocabulario aceito. Vem da regua; sem ela, nao se inventa um default.

    `data` e o `ctx.data` ja carregado. O parametro existe para o teste
    poder passar uma regua sintetica sem montar um Contexto inteiro.
    """
    if data is None:
        from pse.engine.context import Contexto
        data = Contexto(os.getcwd()).data
    return tuple(str(e).strip().lower()
                 for e in data["rastreadores"]["engines_validas"])


def engines_configurados(env=None, data=None) -> tuple:
    """Engines a exercitar, lidas de `PSE_BROWSER_ENGINES` (lista por virgula).

    Default: so `chromium`. Ordem de declaracao e unicidade preservadas.

    FAIL-CLOSED: engine fora do vocabulario levanta `EntradaInvalida`
    (exit 30). Nao e preciosismo — e a diferenca entre o operador descobrir
    o typo agora e descobrir daqui a um mes que o noturno nunca rodou.
    """
    origem = env if env is not None else os.environ
    bruto = str(origem.get(ENV_ENGINES, "") or "").strip()
    if not bruto:
        return ENGINES_PADRAO

    validas = engines_validas(data)
    escolhidas: dict = {}
    for item in bruto.split(","):
        engine = item.strip().lower()
        if not engine:
            continue
        if engine not in validas:
            raise EntradaInvalida(
                f"engine de navegador desconhecida em {ENV_ENGINES}: "
                f"{engine!r}. Validas: {', '.join(validas)}. Recusado de "
                f"proposito: filtrar em silencio faria a execucao passar sem "
                f"ter aberto navegador nenhum.")
        escolhidas.setdefault(engine, None)
    return tuple(escolhidas) or ENGINES_PADRAO


class PlaywrightAusente(Exception):
    """Playwright nao instalado. Vira indeterminacao COM INSTRUCAO."""


INSTRUCAO = (
    "Playwright nao esta instalado. A camada dinamica e opcional de "
    "proposito — quem so quer o inventario estatico nao carrega um navegador "
    "junto. Para habilita-la:\n"
    "    pip install 'pse-suite[browser]'\n"
    "    python -m playwright install chromium\n"
    "Enquanto nao estiver instalada, os checks dinamicos ficam "
    "INDETERMINADOS (exit 20) — nunca verdes: nao ter olhado e diferente de "
    "ter olhado e nao achado nada.")


def exigir_playwright():
    """Devolve o modulo `sync_api`, ou levanta com a instrucao de instalar."""
    try:
        from playwright import sync_api
    except ImportError as e:                      # pragma: no cover - ambiente
        raise PlaywrightAusente(INSTRUCAO) from e
    return sync_api
