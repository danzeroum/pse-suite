"""E-05 — variavel proxy de discriminacao no score, sem ajuste de fairness.

ANCORA NO FATO (D-01): o ajuste so suprime o achado se for uma CHAMADA que
executa. `# nota: avaliar equalized_odds no futuro` nao equaliza nada.
Um finding por arquivo (D-09), pela mesma politica de ruido do P-03.
"""
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

RX_AJUSTE = re.compile(
    r"re_?weighting|equalized_odds|demographic_parity|ajuste_fairness", re.I)


def _tem_ajuste_executavel(p) -> bool:
    """Chamada real de ajuste — via AST no Python, via codigo efetivo fora dele."""
    if p.suffix == ".py":
        arvore = scan.arvore(p)      # SyntaxError -> CheckIndeterminado
        return any(RX_AJUSTE.search(nome) for _, nome in scan.chamadas(arvore))
    return bool(RX_AJUSTE.search(
        scan.codigo_efetivo(scan.ler(p), p.suffix, sem_literais=True)))


@check("E-05", "ethics", "Proxy de discriminacao em score", base_legal="LGPD Art. 6o IX")
def proxy_discriminacao(ctx):
    proibidas = ctx.data["prohibited-filters"]["proxies_discriminacao"]
    padrao = (rf"(score|pontuacao|features|X_train|model)\W.*"
              rf"\b({'|'.join(map(re.escape, proibidas))})\b")
    findings = []
    for p in scan.arquivos(ctx.repo, {".py"}):
        hits = scan.grep(p, padrao)
        if not hits or _tem_ajuste_executavel(p):
            continue
        linha, snippet = hits[0]     # um finding por arquivo — evita ruido
        findings.append(Finding(
            check_id="E-05", pack="ethics", severidade=Severidade.ALTO,
            titulo="Score usa variavel proxy de discriminacao sem ajuste",
            descricao="Variaveis como CEP/bairro/genero discriminam "
                      "indiretamente por raca/classe quando entram no score, "
                      "e nao ha chamada de ajuste de fairness que execute.",
            recomendacao="Aplicar re-weighting / equalized odds e justificar "
                         "a base legal de cada variavel; documentar no Model Card.",
            base_legal="LGPD Art. 6o IX",
            arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet))
    return findings
