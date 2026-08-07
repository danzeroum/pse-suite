"""P-06 — a chave de pseudonimizacao morando junto do dado que ela protege.

Pseudonimizacao so vale enquanto a chave estiver separada: com ela em maos,
o pseudonimo volta a ser identificador direto. Chave literal no repositorio
e a segregacao anulada — quem le o codigo reidentifica a base inteira, e a
revogacao exige um deploy novo.

O RISCO nao tem gradacao, e essa e a diferenca para S-06: uma credencial de
parceiro exposta e um incidente de acesso; a chave de pseudonimizacao
exposta e a reidentificacao consumada de todo mundo que ja passou por ela.

A SEVERIDADE EMITIDA tem, e a distincao e o conserto da rodada de
reconhecimento. `pse.checks._credencial` responde uma pergunta diferente da
acima: aquela chave esta VIVA? Um `secret_key = "test-secret"` sob `tests/`
carrega o mesmo risco teorico e nenhum risco real, e 18 dos 19 CRITICOs de
credencial medidos contra alvos reais eram exatamente isso. Gate reprovado
por falso-positivo ensina a ignorar a categoria inteira — e ai o 19o, o real,
passa junto.

O achado NUNCA some. Ele cai para MEDIO, com o motivo escrito na descricao.
"""
from pse.checks import _credencial
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding

PADRAO = r"\b(hmac_key|secret_key|private_key|senha|password)\s*=\s*[\"\'][^\"\']{8,}[\"\']"


@check("P-06", "privacy", "Chave de pseudonimizacao no codigo", base_legal="LGPD Art. 46")
def chave_segregada(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, scan.ECMASCRIPT | {".py", ".go", ".java", ".env"}):
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
