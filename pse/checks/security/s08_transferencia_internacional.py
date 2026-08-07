"""S-08 — destino fora do Brasil sem base de transferencia declarada.

Le o manifesto de terceiros, nao o codigo: quem declara `data_residency`
fora do BR assume o Art. 33, e a base (SCC, adequacao, consentimento
especifico) tem de estar escrita ao lado. Residencia sem base e o achado.

Sem manifesto o check PULA, com motivo: a ausencia do arquivo ja e cobrada
por S-04, e cobrar duas vezes o mesmo defeito ensina a ignorar os dois.

Par estatico de S-16, e a divisao entre eles e deliberada: aqui olha-se o
egresso DECLARADO ao terceiro; la, onde o byte efetivamente pousa no codigo
de escrita. Um alvo pode passar num e reprovar no outro.
"""
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
                base_legal="LGPD Art. 33",
                arquivo=ctx.manifesto_path(),
                linha=ctx.linha_da_integracao(item.get("name"))))
    return findings
