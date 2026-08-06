import re
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

EXTS = {".py", ".js", ".ts", ".go", ".java"}


def _pii(ctx) -> str:
    termos = [t for grupo in ctx.data["pii-patterns"].values() for t in grupo]
    return "|".join(re.escape(t) for t in termos)


@check("P-01", "privacy", "PII em logs sem mascaramento", base_legal="LGPD Art. 46")
def pii_em_logs(ctx):
    padrao = rf"(logger\.\w+\(|logging\.\w+\(|\blog\(|console\.\w+\(|\bprint\().*\b({_pii(ctx)})\b"
    findings = []
    for p in scan.arquivos(ctx.repo, EXTS):
        for linha, snippet in scan.grep(p, padrao):
            findings.append(Finding(
                check_id="P-01", pack="privacy", severidade=Severidade.CRITICO,
                titulo="Log grava dado pessoal sem mascaramento",
                descricao="Identificador pessoal aparece em chamada de log/print "
                          "sem pseudonimizacao — risco de exposicao em vazamento de logs.",
                recomendacao="Mascarar PII antes de logar (ex.: jo***@d***.com); "
                             "logs sensiveis com chave KMS separada.",
                base_legal="LGPD Art. 46",
                arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet))
    return findings
