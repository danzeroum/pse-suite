from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

PADRAO = r"(deleted_at|is_deleted|status\s*==?\s*['\"]deleted['\"])"


@check("P-03", "privacy", "Soft-delete sem eliminacao fisica", base_legal="LGPD Art. 18 VI")
def soft_delete(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, {".py", ".sql"}):
        hits = scan.grep(p, PADRAO)
        if not hits:
            continue
        linha, snippet = hits[0]  # um finding por arquivo — evita ruido
        findings.append(Finding(
            check_id="P-03", pack="privacy", severidade=Severidade.ALTO,
            titulo="Soft-delete sem eliminacao definitiva",
            descricao="Registros sao apenas marcados como deletados e permanecem "
                      "acessiveis via SQL direto ou backup.",
            recomendacao="Job que elimina fisicamente apos o periodo de retencao; "
                         "crypto-shredding para dados criptografados.",
            base_legal="LGPD Art. 18 VI",
            arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet))
    return findings
