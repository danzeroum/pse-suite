from pse.engine.registry import check
from pse.model import Finding, Severidade

OBRIGATORIOS = ["class", "owner", "purpose", "legal_basis", "retention_years"]


@check("P-04", "privacy", "Catalogo vivo de dados", base_legal="LGPD Art. 37")
def catalogo(ctx):
    cat = ctx.catalog()
    caminho = ctx.config.get("catalog_path", "tests/qa/catalog.yaml")
    if cat is None:
        return [Finding(
            check_id="P-04", pack="privacy", severidade=Severidade.ALTO,
            titulo="Catalogo de dados ausente",
            descricao="Sem inventario (campo -> classe, dono, finalidade, base "
                      "legal, retencao) nenhum outro controle de privacidade opera.",
            recomendacao=f"Criar {caminho} conforme schema consent/catalog da suite.",
            base_legal="LGPD Art. 37", arquivo=caminho)]
    sensiveis = set(ctx.data["sensitive-fields"]["sensiveis"])
    findings = []
    for tabela, tmeta in (cat.get("tables") or {}).items():
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            props = props or {}
            if props.get("status") == "prohibited":
                continue
            faltando = [k for k in OBRIGATORIOS if k not in props]
            if faltando:
                findings.append(Finding(
                    check_id="P-04", pack="privacy", severidade=Severidade.MEDIO,
                    titulo=f"Campo {tabela}.{campo} com metadados incompletos",
                    descricao=f"Metadados ausentes no catalogo: {', '.join(faltando)}.",
                    recomendacao="Completar classe, dono, finalidade, base legal e retencao.",
                    base_legal="LGPD Art. 37", arquivo=caminho))
            if campo in sensiveis and props.get("class") != "sensitive":
                findings.append(Finding(
                    check_id="P-04", pack="privacy", severidade=Severidade.ALTO,
                    titulo=f"Campo {tabela}.{campo} sensivel classificado como '{props.get('class')}'",
                    descricao="Campo consta na lista curada de dados sensiveis "
                              "(Art. 5o II) mas nao esta classificado como sensitive.",
                    recomendacao="Reclassificar como sensitive e revisar base legal.",
                    base_legal="LGPD Art. 5o II", arquivo=caminho))
    return findings
