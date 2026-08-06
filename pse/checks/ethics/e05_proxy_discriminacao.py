import re
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

RX_AJUSTE = re.compile(r"re_?weighting|equalized_odds|demographic_parity|ajuste_fairness", re.I)


@check("E-05", "ethics", "Proxy de discriminacao em score", base_legal="LGPD Art. 6o IX")
def proxy_discriminacao(ctx):
    proibidas = ctx.data["prohibited-filters"]["proxies_discriminacao"]
    padrao = rf"(score|pontuacao|features|X_train|model)\W.*\b({'|'.join(map(re.escape, proibidas))})\b"
    findings = []
    for p in scan.arquivos(ctx.repo, {".py"}):
        conteudo = scan.ler(p)
        for linha, snippet in scan.grep(p, padrao):
            if RX_AJUSTE.search(conteudo):
                continue
            findings.append(Finding(
                check_id="E-05", pack="ethics", severidade=Severidade.ALTO,
                titulo="Score usa variavel proxy de discriminacao sem ajuste",
                descricao="Variaveis como CEP/bairro/genero discriminam "
                          "indiretamente por raca/classe quando entram no score.",
                recomendacao="Aplicar re-weighting / equalized odds e justificar "
                             "a base legal de cada variavel; documentar no Model Card.",
                base_legal="LGPD Art. 6o IX",
                arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet))
    return findings
