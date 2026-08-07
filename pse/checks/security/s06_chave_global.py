"""S-06 — credencial de parceiro hardcoded.

SEVERIDADE POR CONTEXTO desde a rodada de conserto, pelo mesmo modulo que
P-06 usa (`pse.checks._credencial`) e pelo mesmo motivo: um token
propositalmente invalido num teste de rejeicao nao pode dirigir o exit code
de ninguem. Ele continua no laudo, em MEDIO.
"""
from pse.checks import _credencial
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding

PADRAO = (r"(\b(api_key|apikey|access_token)\s*=\s*[\"'][^\"']{12,}[\"']"
          r"|Authorization[\"']?\s*[:=].{0,10}(Bearer|Basic)\s+[A-Za-z0-9._\-]{16,})")


@check("S-06", "security", "Credencial de parceiro hardcoded", base_legal="LGPD Art. 46")
def chave_global(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, {".py", ".js", ".ts", ".go", ".java", ".env", ".yaml", ".yml"}):
        rel = scan.rel(ctx.repo, p)
        for linha, snippet in scan.grep(p, PADRAO):
            sev = _credencial.severidade(ctx, rel, snippet)
            nota = _credencial.motivo(ctx, rel, snippet)
            findings.append(Finding(
                check_id="S-06", pack="security", severidade=sev,
                titulo="API key / token de parceiro em texto claro",
                descricao="Credencial hardcoded: irrevogavel sem novo deploy e "
                          "compartilhada por todo consumidor do codigo."
                          + (" " + nota if nota else ""),
                recomendacao="Chave por parceiro em cofre, com TTL, rotacao e "
                             "revogacao em 1 clique.",
                base_legal="LGPD Art. 46",
                arquivo=rel, linha=linha, snippet=snippet[:80]))
    return findings
