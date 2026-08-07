"""P-06 — a chave de pseudonimizacao morando junto do dado que ela protege.

Pseudonimizacao so vale enquanto a chave estiver separada: com ela em maos,
o pseudonimo volta a ser identificador direto. Chave literal no repositorio
e a segregacao anulada — quem le o codigo reidentifica a base inteira, e a
revogacao exige um deploy novo.

CRITICO sem gradacao, e essa e a diferenca para S-06: uma credencial de
parceiro exposta e um incidente de acesso; a chave de pseudonimizacao
exposta e a reidentificacao consumada de todo mundo que ja passou por ela.
"""
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
