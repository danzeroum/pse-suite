"""S-01 — BOLA/IDOR: recurso de titular acessivel por outro titular.

MODO ATIVO. Envia o token do titular A contra um recurso declarado do
titular B: e sonda de autorizacao deliberada, e ser somente-leitura nao a
torna passiva. So dispara em `--modo pse_active`, com escopo atestado, em
staging e com identidades sinteticas declaradas.

A suite nao descobre o recurso de B — ele e declarado. Enumerar recurso
alheio no alvo seria executar exatamente a violacao que este check existe
para impedir.
"""
from pse.engine.registry import check
from pse.model import CheckIndeterminado, Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo


@check("S-01", "security", "BOLA/IDOR", base_legal="OWASP API1")
def bola(ctx):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    recursos = autorizacao.recursos_de_b(ctx.config)

    findings = []
    for rota in recursos:
        resposta, trace = cliente.requisitar("GET", rota, token=token_a,
                                             identidade="titular_a")
        if resposta.status in (200, 206):
            findings.append(Finding(
                check_id="S-01", pack="security", severidade=Severidade.CRITICO,
                titulo="Recurso de outro titular acessivel (BOLA/IDOR)",
                descricao=f"O token do titular A obteve {resposta.status} num "
                          f"recurso declarado do titular B. Nao ha verificacao "
                          f"de propriedade: qualquer usuario autenticado le o "
                          f"dado de qualquer outro.",
                recomendacao="Verificar propriedade do recurso no servidor "
                             "(assertOwnership) antes de responder; responder "
                             "404 para recurso alheio, nunca 403.",
                base_legal="OWASP API1",
                arquivo=rota, linha=1, trace=trace))
        elif resposta.status in (401, 403):
            # Negou o acesso, mas confirmou a existencia. Isso e P-11, nao S-01:
            # cada check responde por uma coisa so.
            continue
        elif resposta.status != 404:
            raise CheckIndeterminado(
                f"alvo respondeu {resposta.status} a sonda de propriedade — "
                f"nao da para concluir se ha BOLA; indeterminado bloqueia igual")
    return findings
