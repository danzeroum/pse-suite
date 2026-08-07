"""P-15 — dado pessoal virando feature de treino sem finalidade declarada.

O buraco que a matriz expos: privacidade em IA so existia de rabo de olho,
via ethics (E-11 olha o prompt, E-12 o derivado exportado). Nenhum dos dois
pergunta o obvio — **este campo pode ser usado para treinar?**

Treinar e uma finalidade nova, nao um detalhe de implementacao da finalidade
antiga. Um CPF coletado para cobranca e um CPF com base legal para cobranca;
usa-lo como feature de um modelo de risco e outro tratamento, que precisa da
sua propria finalidade declarada — e, se o campo for sensivel, da hipotese do
Art. 11, que nao admite legitimo interesse.

Cruza catalogo x codigo, como P-04 e P-08: o fato (a chamada de treino com o
campo) contra a declaracao (a finalidade no catalogo). Sem catalogo nao da
para decidir, e nao decidir bloqueia — nunca vira verde.

D-08: campo com `purpose` que inclui treino nao dispara. Punir quem declarou
seria punir exatamente o comportamento que o check quer produzir.
"""
import ast

from pse.engine import scan
from pse.engine.registry import check
from pse.model import CheckIndeterminado, Finding, Severidade, SkipCheck

BASE = "LGPD Art. 6o I e III (finalidade e necessidade)"
BASE_SENSIVEL = "LGPD Art. 11 (dado sensivel exige hipotese propria)"
REGUA = "adversarial-patterns"
# Art. 11 nao admite legitimo interesse; P-08 ja trava isso no catalogo, e
# aqui a exigencia e a mesma vista pelo angulo do treino.
BASES_VALIDAS_SENSIVEL = ("consentimento", "tutela", "saude", "publica",
                          "judicial", "vida")


def _termos(ctx, chave) -> set:
    return {t.lower() for t in ctx.data[REGUA][chave]}


def _campos_no_treino(ctx, arvore) -> list:
    """(no, campo) para cada literal de campo que entra numa chamada de treino."""
    treino = _termos(ctx, "chamadas_de_treino")
    saida = []
    for no, nome in scan.chamadas(arvore):
        if nome.split(".")[-1].lower() not in treino:
            continue
        for arg in list(no.args) + [k.value for k in no.keywords]:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    saida.append((no, sub.value))
                elif isinstance(sub, ast.Attribute):
                    saida.append((no, sub.attr))
    return saida


def _catalogo_de_campos(cat) -> dict:
    saida = {}
    for tmeta in (cat.get("tables") or {}).values():
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            saida[str(campo).lower()] = props or {}
    return saida


@check("P-15", "privacy", "PII como feature de treino", base_legal=BASE)
def pii_como_feature(ctx):
    finalidades = _termos(ctx, "finalidades_de_treino")
    pii = {t.lower() for grupo in ctx.data["pii-patterns"].values() for t in grupo}
    sensiveis = {t.lower() for t in ctx.data["sensitive-fields"]["sensiveis"]}

    achados_brutos, houve_treino = [], False
    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        no_treino = _campos_no_treino(ctx, arvore)
        if no_treino:
            houve_treino = True
        achados_brutos.append((p, no_treino))

    if not houve_treino:
        raise SkipCheck("nenhuma chamada de treino no codigo — nao ha feature "
                        "a confrontar com o catalogo")

    cat = ctx.catalog()
    if cat is None:
        raise CheckIndeterminado(
            "ha treino de modelo, mas nao existe catalogo de dados para dizer "
            "se os campos usados como feature declaram finalidade de treino — "
            "sem inventario a pergunta nao e respondivel (catalogo cobrado "
            "por P-04)")
    campos_cat = _catalogo_de_campos(cat)

    findings, vistos = [], set()
    for p, no_treino in achados_brutos:
        linhas = scan.ler(p).splitlines()
        for no, campo in no_treino:
            baixo = campo.lower()
            e_pii = baixo in pii or baixo in sensiveis or baixo in campos_cat
            if not e_pii:
                continue
            props = campos_cat.get(baixo, {})
            classe = props.get("class")
            if classe not in ("personal", "sensitive") and baixo not in pii \
                    and baixo not in sensiveis:
                continue

            proposito = str(props.get("purpose") or "").lower()
            if any(f in proposito for f in finalidades):
                continue                 # finalidade de treino declarada

            chave = (scan.rel(ctx.repo, p), no.lineno, baixo)
            if chave in vistos:
                continue
            vistos.add(chave)

            sensivel = classe == "sensitive" or baixo in sensiveis
            base_legal_campo = str(props.get("legal_basis") or "").lower()
            if sensivel:
                base = f"{BASE} + {BASE_SENSIVEL}"
                extra = (f" O campo e SENSIVEL: treina-lo exige hipotese do "
                         f"Art. 11, e a base declarada e "
                         f"'{props.get('legal_basis') or 'nenhuma'}'"
                         + ("" if any(b in base_legal_campo
                                      for b in BASES_VALIDAS_SENSIVEL)
                            else " — que nao serve para dado sensivel"))
            else:
                base, extra = BASE, ""

            i = no.lineno
            findings.append(Finding(
                check_id="P-15", pack="privacy", severidade=Severidade.ALTO,
                titulo=f"Campo '{campo}' vira feature de treino sem finalidade "
                       f"declarada",
                descricao=f"O catalogo declara purpose="
                          f"'{props.get('purpose') or 'nao declarado'}' para "
                          f"este campo, e treinar modelo nao esta la. Treino e "
                          f"finalidade NOVA, nao detalhe de implementacao da "
                          f"antiga: o dado coletado para uma coisa passa a "
                          f"produzir um modelo que decide outra, e o titular "
                          f"nunca foi informado disso.{extra}",
                recomendacao="Declarar a finalidade de treino no catalogo com a "
                             "base legal correspondente — ou remover o campo do "
                             "conjunto de features. Pseudonimizar antes do "
                             "treino resolve boa parte dos casos.",
                base_legal=base,
                arquivo=scan.rel(ctx.repo, p), linha=i,
                snippet=linhas[i - 1].strip()[:200] if i <= len(linhas) else None))
    return findings
