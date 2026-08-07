"""P-06 — chave de pseudonimizacao ou segredo em texto claro no codigo.

SEVERIDADE POR CONTEXTO desde a rodada de conserto. `pse.checks._credencial`
responde se o achado dirige o gate (CRITICO) ou fica visivel sem bloquear
(MEDIO) — nunca se ele existe. Ver aquele modulo para o porque; o resumo e
que 18 dos 19 CRITICOs de credencial contra alvos reais eram fixtures, e um
gate reprovado por falso-positivo ensina a ignorar a categoria inteira.
"""
from pse.checks import _credencial
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding

PADRAO = r"\b(hmac_key|secret_key|private_key|senha|password)\s*=\s*[\"'][^\"']{8,}[\"']"


@check("P-06", "privacy", "Chave de pseudonimizacao no codigo", base_legal="LGPD Art. 46")
def chave_segregada(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, {".py", ".js", ".ts", ".go", ".java", ".env"}):
        rel = scan.rel(ctx.repo, p)
        for linha, snippet in scan.grep(p, PADRAO):
            sev = _credencial.severidade(ctx, rel, snippet)
            nota = _credencial.motivo(ctx, rel, snippet)
            findings.append(Finding(
                check_id="P-06", pack="privacy", severidade=sev,
                titulo="Chave/segredo em texto claro no codigo",
                descricao="Chave de pseudonimizacao ou segredo hardcoded — "
                          "vazamento do repositorio revela os dados protegidos."
                          + (" " + nota if nota else ""),
                recomendacao="Mover para cofre (Vault/KMS/Secret Manager) com "
                             "rotacao; nunca versionar o valor.",
                base_legal="LGPD Art. 46",
                arquivo=rel, linha=linha, snippet=snippet[:80]))
    return findings
