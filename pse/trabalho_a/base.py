"""A porta unica por onde todo check de Trabalho A passa.

Se um check runtime obtiver um cliente HTTP por qualquer outro caminho, a
garantia desta fase deixa de valer. Por isso `exigir_alvo()` e a unica
funcao que constroi um `Cliente`, e ela so o faz depois dos cinco degraus.
"""
from pse.trabalho_a import autorizacao
from pse.trabalho_a.cliente import TIMEOUT_PADRAO, Cliente


def exigir_alvo(ctx, modo_check: str):
    """Devolve (cliente, alvo) — ou levanta antes de qualquer requisicao.

    NaoHabilitado      -> nao bloqueia (checks_nao_habilitados)
    CheckIndeterminado -> bloqueia (exit 20)
    """
    config = ctx.config
    modo_exec = getattr(ctx, "modo", "pse_inventory")

    # 2. o modo desta execucao dispara este check?
    autorizacao.exigir_modo(config, modo_exec, modo_check)
    # 3. atestacao valida para este modo e este alvo?
    autorizacao.validar_atestacao(config, modo_exec)

    alvo = autorizacao.alvo_de(config)
    cliente = ctx.cliente_http(alvo)
    # 5. alvo de pe? Uma unica vez por execucao, e o resultado vale para
    #    todos os checks: alvo caido nao merece uma sonda sequer.
    ctx.exigir_alvo_saudavel(cliente, alvo)
    return cliente, alvo


def novo_cliente(alvo, transporte=None) -> Cliente:
    return Cliente(alvo.get("base_url"), transporte=transporte,
                   timeout=alvo.get("timeout_s") or TIMEOUT_PADRAO)
