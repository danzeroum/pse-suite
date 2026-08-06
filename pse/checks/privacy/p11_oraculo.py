"""P-11 — oraculo de existencia: 403 e 404 distinguiveis.

MODO ATIVO. Compara a resposta a um recurso que EXISTE e nao e seu (o do
titular B, declarado) com a resposta a um recurso que comprovadamente nao
existe (declarado em `endpoints.inexistente`). Se as duas diferem, a API
responde "este recurso existe, mas nao e seu" — e isso permite enumerar
titulares sem nunca ler um dado: o oraculo E o vazamento.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo


@check("P-11", "privacy", "Oraculo de existencia", base_legal="profiling")
def oraculo(ctx):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    recursos = autorizacao.recursos_de_b(ctx.config)
    rota_inexistente = autorizacao.endpoint(ctx.config, "inexistente")

    r_ausente, _ = cliente.requisitar("GET", rota_inexistente, token=token_a,
                                      identidade="titular_a")
    findings = []
    for rota in recursos:
        r_alheio, trace = cliente.requisitar("GET", rota, token=token_a,
                                             identidade="titular_a")
        if r_alheio.status == r_ausente.status:
            continue                       # indistinguivel — conforme
        if r_alheio.status in (401, 403) and r_ausente.status == 404:
            findings.append(Finding(
                check_id="P-11", pack="privacy", severidade=Severidade.CRITICO,
                titulo="API distingue 'existe e nao e seu' de 'nao existe'",
                descricao=f"Recurso alheio respondeu {r_alheio.status} e recurso "
                          f"inexistente respondeu {r_ausente.status}. A diferenca "
                          f"permite enumerar titulares por tentativa, sem ler um "
                          f"unico dado — o oraculo e o proprio vazamento.",
                recomendacao="Responder 404 tanto para recurso inexistente "
                             "quanto para recurso de outro titular; usar IDs "
                             "opacos (UUID) no lugar de identificadores naturais.",
                base_legal="profiling / LGPD Art. 6o VIII",
                arquivo=rota, linha=1, trace=trace))
    return findings
