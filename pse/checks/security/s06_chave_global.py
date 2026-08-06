from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

PADRAO = (r"(\b(api_key|apikey|access_token)\s*=\s*[\"'][^\"']{12,}[\"']"
          r"|Authorization[\"']?\s*[:=].{0,10}(Bearer|Basic)\s+[A-Za-z0-9._\-]{16,})")


@check("S-06", "security", "Credencial de parceiro hardcoded", base_legal="LGPD Art. 46")
def chave_global(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, {".py", ".js", ".ts", ".go", ".java", ".env", ".yaml", ".yml"}):
        for linha, snippet in scan.grep(p, PADRAO):
            findings.append(Finding(
                check_id="S-06", pack="security", severidade=Severidade.CRITICO,
                titulo="API key / token de parceiro em texto claro",
                descricao="Credencial hardcoded: irrevogavel sem novo deploy e "
                          "compartilhada por todo consumidor do codigo.",
                recomendacao="Chave por parceiro em cofre, com TTL, rotacao e "
                             "revogacao em 1 clique.",
                base_legal="LGPD Art. 46",
                arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet[:80]))
    return findings
