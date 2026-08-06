from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

BASES_VEDADAS = {"legitimo_interesse", "legitimate_interest", "legitimo interesse"}


@check("P-08", "privacy", "Dado sensivel com legitimo interesse", base_legal="LGPD Art. 11")
def sensivel_legitimo_interesse(ctx):
    cat = ctx.catalog()
    if cat is None:
        raise SkipCheck("catalogo de dados ausente — cobrado por P-04")
    caminho = ctx.config.get("catalog_path", "tests/qa/catalog.yaml")
    findings = []
    for tabela, tmeta in (cat.get("tables") or {}).items():
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            props = props or {}
            base = str(props.get("legal_basis", "")).strip().lower()
            if props.get("class") == "sensitive" and base in BASES_VEDADAS:
                findings.append(Finding(
                    check_id="P-08", pack="privacy", severidade=Severidade.CRITICO,
                    titulo=f"Campo sensivel {tabela}.{campo} com base 'legitimo interesse'",
                    descricao="Dado sensivel nao admite legitimo interesse como "
                              "base legal — trava estrutural, sem excecao.",
                    recomendacao="Usar consentimento especifico e destacado (Art. 11) "
                                 "ou outra hipotese legal valida; senao, nao tratar.",
                    base_legal="LGPD Art. 11", arquivo=caminho))
    return findings
