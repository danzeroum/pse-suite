from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

PADRAO = r"\b(hmac_key|secret_key|private_key|senha|password)\s*=\s*[\"'][^\"']{8,}[\"']"


@check("P-06", "privacy", "Chave de pseudonimizacao no codigo", base_legal="LGPD Art. 46")
def chave_segregada(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, {".py", ".js", ".ts", ".go", ".java", ".env"}):
        for linha, snippet in scan.grep(p, PADRAO):
            findings.append(Finding(
                check_id="P-06", pack="privacy", severidade=Severidade.CRITICO,
                titulo="Chave/segredo em texto claro no codigo",
                descricao="Chave de pseudonimizacao ou segredo hardcoded — "
                          "vazamento do repositorio revela os dados protegidos.",
                recomendacao="Mover para cofre (Vault/KMS/Secret Manager) com "
                             "rotacao; nunca versionar o valor.",
                base_legal="LGPD Art. 46",
                arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet[:80]))
    return findings
