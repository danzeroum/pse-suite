"""E-02 — decision log estruturado.

MODO PASSIVO. A explicacao ao titular (E-01) e uma coisa; o registro
auditavel da decisao e outra. Sem modelo, features, score, limiar e
revisor, ninguem consegue reconstruir a decisao depois — nem o DPO, nem o
juiz, nem a equipe que precisa entender por que o modelo virou.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo
from .e01_explicacao import presentes

EXIGIDOS = {
    "modelo": ("modelo", "modelo_v", "model", "model_version", "modelo_versao"),
    "features": ("features", "atributos", "variaveis"),
    "score": ("score", "pontuacao", "probabilidade"),
    "limiar": ("limiar", "threshold", "corte"),
    "revisor": ("revisor", "reviewer", "revisao", "decidido_por"),
}


@check("E-02", "ethics", "Decision log estruturado", base_legal="LGPD Art. 20/37")
def decision_log(ctx):
    cliente, _ = exigir_alvo(ctx, "passive")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "decisao")

    resposta, trace = cliente.requisitar("GET", rota, token=token_a,
                                         identidade="titular_a")
    dado = resposta.json()
    if dado is None:
        return []          # E-01 ja reporta a ausencia de corpo interpretavel

    faltando = [rotulo for rotulo, aliases in EXIGIDOS.items()
                if not presentes(dado, set(aliases))]
    if not faltando:
        return []
    return [Finding(
        check_id="E-02", pack="ethics", severidade=Severidade.ALTO,
        titulo="Decision log incompleto",
        descricao=f"A decisao nao registra: {', '.join(faltando)}. Sem esses "
                  f"campos a decisao nao e reconstruivel depois — e uma decisao "
                  f"que ninguem consegue reconstruir e uma decisao que ninguem "
                  f"consegue contestar.",
        recomendacao="Registrar por decisao: versao do modelo, features de "
                     "entrada, score, limiar aplicado e revisor humano (ou a "
                     "marca explicita de que nao houve).",
        base_legal="LGPD Art. 20/37", arquivo=rota, linha=1, trace=trace)]
