import re
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

RX_ML = re.compile(r"^(import|from)\s+(sklearn|torch|tensorflow|xgboost|lightgbm|keras)\b", re.M)
RX_CARD = re.compile(r"model[-_]card", re.I)


@check("E-07", "ethics", "Model Card ausente", base_legal="EbD-AI / LGPD Art. 20")
def model_card(ctx):
    usa_ml = any(RX_ML.search(scan.ler(p)) for p in scan.arquivos(ctx.repo, {".py"}))
    if not usa_ml:
        return []
    tem_card = any(RX_CARD.search(p.name)
                   for p in scan.arquivos(ctx.repo, {".md", ".yaml", ".yml", ".json"}))
    if tem_card:
        return []
    return [Finding(
        check_id="E-07", pack="ethics", severidade=Severidade.ALTO,
        titulo="Codigo de ML sem Model Card versionado",
        descricao="Ha treino/inferencia de modelo sem documentacao formal de "
                  "proposito, limitacoes, dados de treino e metricas de fairness.",
        recomendacao="Criar model-card.yaml (Mitchell et al., 2019) versionado "
                     "com o codigo; validar no CI.",
        base_legal="EbD-AI / LGPD Art. 20")]
