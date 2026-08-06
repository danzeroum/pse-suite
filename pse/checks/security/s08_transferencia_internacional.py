from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

NACIONAL = {"br", "brasil", "brazil"}


@check("S-08", "security", "Transferencia internacional sem base", base_legal="LGPD Art. 33")
def transferencia_internacional(ctx):
    manifesto = ctx.manifest_terceiros()
    if manifesto is None:
        raise SkipCheck("manifesto de terceiros ausente — cobrado por S-04")
    findings = []
    for item in manifesto.get("integrations", []):
        residencia = str(item.get("data_residency", "")).strip().lower()
        if residencia and residencia not in NACIONAL and not item.get("transfer_basis"):
            findings.append(Finding(
                check_id="S-08", pack="security", severidade=Severidade.ALTO,
                titulo=f"'{item.get('name')}' processa fora do BR sem base de transferencia",
                descricao=f"data_residency={residencia!r} sem transfer_basis "
                          "(SCC, adequacao, consentimento especifico...).",
                recomendacao="Declarar transfer_basis valida no manifesto ou "
                             "rotear para regiao nacional.",
                base_legal="LGPD Art. 33"))
    return findings
