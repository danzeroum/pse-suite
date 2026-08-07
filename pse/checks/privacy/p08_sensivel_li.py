"""P-08 — dado sensivel apoiado em legitimo interesse.

Le o catalogo de dados e cruza duas colunas que o time preenche em momentos
diferentes: a categoria do campo e a base legal. O Art. 11 nao lista
legitimo interesse entre as hipoteses de dado sensivel — entao a combinacao
nao e um risco a ponderar, e um tratamento sem base.

CRITICO porque o defeito nao esta no codigo e sim na declaracao: enquanto
ela estiver assim, todo processamento daquele campo esta descoberto, e o
proprio catalogo e a prova.

Sem catalogo o check PULA, com motivo — a ausencia e cobrada por P-04.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

BASES_VEDADAS = {"legitimo_interesse", "legitimate_interest", "legitimo interesse"}


@check("P-08", "privacy", "Dado sensivel com legitimo interesse", base_legal="LGPD Art. 11")
def sensivel_legitimo_interesse(ctx):
    cat = ctx.catalog()
    if cat is None:
        raise SkipCheck("catalogo de dados ausente — cobrado por P-04")
    caminho = ctx.catalog_path()
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
                    base_legal="LGPD Art. 11", arquivo=caminho,
                    linha=ctx.linha_no_catalogo("tables", tabela, "fields", campo)))
    return findings
