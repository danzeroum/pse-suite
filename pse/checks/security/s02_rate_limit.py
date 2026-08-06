"""S-02 — rate limit ausente: extracao em massa possivel.

MODO ATIVO. Pagina a listagem declarada ate o alvo bloquear. Espera
rejeicao (429), o que a classifica como ativa mesmo sendo GET — na duvida
entre passivo e ativo, ativo.

O teto de requisicoes e da suite, nao do consumidor: um limite que o
vigiado configura nao mede nada. Se o alvo nao bloqueou em `TENTATIVAS`,
um extrator tambem nao seria bloqueado.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo

TENTATIVAS = 25
BLOQUEIO = (429, 503)


@check("S-02", "security", "Rate limit / anti-extracao", base_legal="OWASP API4")
def rate_limit(ctx):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "listagem")

    ultimo = None
    for i in range(TENTATIVAS):
        resposta, ultimo = cliente.requisitar("GET", rota, token=token_a,
                                              identidade="titular_a")
        if resposta.status in BLOQUEIO:
            return []                      # bloqueou — conforme
    return [Finding(
        check_id="S-02", pack="security", severidade=Severidade.ALTO,
        titulo="Listagem sem rate limit: extracao em massa possivel",
        descricao=f"{TENTATIVAS} requisicoes consecutivas a {rota} sem nenhum "
                  f"bloqueio (429/503). Uma base inteira de titulares pode ser "
                  f"extraida por paginacao, com credencial legitima e sem "
                  f"disparar nenhum alarme.",
        recomendacao="Rate limit por identidade e por IP, paginacao por cursor "
                     "com teto de page_size, e alerta de volume anomalo.",
        base_legal="OWASP API4",
        arquivo=rota, linha=1, trace=ultimo)]
