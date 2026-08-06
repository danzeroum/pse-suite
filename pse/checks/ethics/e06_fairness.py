"""E-06 — drift de disparidade por grupo contra o baseline.

MODO INVENTORY, E DELIBERADAMENTE SEM INFERENCIA. A suite nao carrega o
dataset de avaliacao nem roda o modelo do consumidor: fazer isso significaria
processar dado sensivel de titulares reais dentro de uma ferramenta de
auditoria, para produzir um numero que o consumidor ja tem. O fiscal
deterministico nao julga — ele cobra que o julgamento exista, esteja fresco
e traga as condicoes de medicao.

O que este check exige, nesta ordem:
  1. `fairness_dataset` DECLARADO pelo consumidor e existente em disco.
     Ausente -> indeterminado. Dataset e insumo declarado, jamais descoberto:
     sair procurando parquet no repositorio seria adivinhar sobre que dados
     a justica do modelo foi medida.
  2. relatorio de fairness declarado, valido contra fairness-report-1.0 e
     FRESCO em relacao ao fingerprint do dataset (numero de outra medicao
     nao vale).
  3. DPD por grupo dentro do teto — que a suite valida, e o consumidor nao
     afrouxa (pse/limites.py).

"Numero sem condicoes de medicao nao entra" e literal aqui: o schema exige
as condicoes, e relatorio sem elas reprova.
"""
import hashlib
from pathlib import Path

import yaml

from pse import limites
from pse.engine.registry import check
from pse.model import CheckIndeterminado, Finding, Severidade
from pse.schemas_validate import erros_de


def _fingerprint(caminho: Path) -> str:
    h = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


@check("E-06", "ethics", "Drift de disparidade", base_legal="nao-discriminacao")
def fairness(ctx):
    packs = ctx.config.get("packs") or {}
    declarado = (packs.get("ethics") or {}).get("fairness_dataset") \
        or ctx.config.get("fairness_dataset")

    if not declarado:
        raise CheckIndeterminado(
            "dataset de avaliacao ausente: nenhum `fairness_dataset` declarado "
            "em pse-config.yaml. Fairness sem dados representativos e teatro, "
            "e a suite nao sai procurando qual arquivo seria o dataset")

    dataset = ctx.repo / declarado
    if not dataset.exists():
        raise CheckIndeterminado(
            f"fairness_dataset declarado ({declarado}) nao existe no alvo — "
            f"declaracao que nao resolve nao e declaracao")

    rel_path = (packs.get("ethics") or {}).get("fairness_report") \
        or ctx.config.get("fairness_report", "tests/qa/fairness-report.yaml")
    relatorio_arq = ctx.repo / rel_path
    if not relatorio_arq.exists():
        return [Finding(
            check_id="E-06", pack="ethics", severidade=Severidade.ALTO,
            titulo="Dataset de avaliacao declarado sem relatorio de fairness",
            descricao=f"Existe {declarado}, mas nenhum relatorio de disparidade "
                      f"em {rel_path}. O dataset sozinho nao mede nada.",
            recomendacao="Gerar o relatorio no CI (schema fairness-report-1.0) "
                         "com DPD por grupo, baseline e condicoes de medicao.",
            base_legal="nao-discriminacao",
            arquivo=rel_path, linha=1)]

    try:
        relatorio = yaml.safe_load(relatorio_arq.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise CheckIndeterminado(f"relatorio de fairness ilegivel: {e}") from e

    findings = []
    for erro in erros_de("fairness-report-1.0.json", relatorio):
        caminho = "/".join(map(str, erro.path)) or "<raiz>"
        findings.append(Finding(
            check_id="E-06", pack="ethics", severidade=Severidade.ALTO,
            titulo=f"Relatorio de fairness invalido em '{caminho}'",
            descricao=f"{erro.message}. Numero sem condicoes de medicao nao "
                      f"entra: sem saber sobre que dados e com que corte a "
                      f"disparidade foi medida, o valor nao e verificavel.",
            recomendacao="Completar o relatorio conforme fairness-report-1.0.",
            base_legal="nao-discriminacao", arquivo=rel_path, linha=1))
    if findings:
        return findings

    # Frescor: o numero tem de ser DESTE dataset.
    atual = _fingerprint(dataset)
    declarado_fp = str(relatorio.get("dataset_fingerprint") or "")
    if declarado_fp != atual:
        return [Finding(
            check_id="E-06", pack="ethics", severidade=Severidade.ALTO,
            titulo="Relatorio de fairness stale",
            descricao=f"O relatorio foi medido sobre um dataset de fingerprint "
                      f"{declarado_fp[:12]}..., e o dataset atual e "
                      f"{atual[:12]}.... Metrica de outra medicao nao vale para "
                      f"esta: o modelo pode ter mudado justamente onde importa.",
            recomendacao="Regerar o relatorio contra o dataset atual no mesmo "
                         "job de CI que treina/avalia o modelo.",
            base_legal="nao-discriminacao", arquivo=rel_path, linha=1)]

    teto = limites.valor(ctx.config, "dpd_max_delta")
    for grupo in relatorio.get("grupos", []):
        dpd = grupo.get("dpd")
        if dpd is None:
            continue
        if abs(float(dpd)) > teto:
            findings.append(Finding(
                check_id="E-06", pack="ethics", severidade=Severidade.ALTO,
                titulo=f"Disparidade acima do teto no grupo '{grupo.get('nome')}'",
                descricao=f"DPD = {dpd} contra teto de {teto}. A diferenca de "
                          f"tratamento entre grupos excede o que a suite aceita "
                          f"como ruido de medicao.",
                recomendacao="Investigar a origem da disparidade (features "
                             "proxy, desbalanceamento do treino) antes de "
                             "promover o modelo; registrar a decisao.",
                base_legal="nao-discriminacao / LGPD Art. 6o IX",
                arquivo=rel_path, linha=1))
    return findings
