"""E-07 — Model Card e Datasheet: presentes, versionados e validos.

A obrigacao nao e declarada pelo time: ela nasce do `import sklearn` (ou
torch, tensorflow, xgboost...). Quem coloca um modelo em producao passa a
dever a documentacao que permite contesta-lo — e o import e a evidencia
verificavel de que o modelo existe.

Por isso o endereco do achado (D-07) e a LINHA DO IMPORT, nao a raiz do
repositorio: o defeito e "este modelo, aqui, nao tem card", e um achado
apontando para lugar nenhum nao se conserta.
"""
import re
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

RX_ML = re.compile(r"^(import|from)\s+(sklearn|torch|tensorflow|xgboost|lightgbm|keras)\b", re.M)
RX_CARD = re.compile(r"model[-_]card", re.I)


def _onde_usa_ml(ctx):
    """O import que cria a obrigacao — e o endereco do achado (D-07).

    Um finding de AUSENCIA tambem precisa de `arquivo:linha`: aponta para o
    fato que exige o artefato, nao para o artefato que nao existe.
    """
    for p in scan.arquivos(ctx.repo, {".py"}):
        texto = scan.ler(p)
        m = RX_ML.search(scan.codigo_efetivo(texto, ".py", sem_literais=True))
        if m:
            return p, texto[:m.start()].count("\n") + 1, m.group(0).strip()
    return None, None, None


@check("E-07", "ethics", "Model Card ausente", base_legal="EbD-AI / LGPD Art. 20")
def model_card(ctx):
    p, linha, snippet = _onde_usa_ml(ctx)
    if p is None:
        return []
    tem_card = any(RX_CARD.search(f.name)
                   for f in scan.arquivos(ctx.repo, {".md", ".yaml", ".yml", ".json"}))
    if tem_card:
        return []
    return [Finding(
        check_id="E-07", pack="ethics", severidade=Severidade.ALTO,
        titulo="Codigo de ML sem Model Card versionado",
        descricao="Ha treino/inferencia de modelo sem documentacao formal de "
                  "proposito, limitacoes, dados de treino e metricas de fairness.",
        recomendacao="Criar model-card.yaml (Mitchell et al., 2019) versionado "
                     "com o codigo; validar no CI.",
        base_legal="EbD-AI / LGPD Art. 20",
        arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet)]
