"""E-01 — decisao automatizada sem explicacao.

MODO PASSIVO: le a decisao com a propria identidade. O titular tem direito
a saber por que a maquina decidiu o que decidiu (Art. 20); uma resposta que
diz apenas "negado" nao satisfaz o direito, por mais correta que a decisao
esteja.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo

CAMPOS_EXPLICACAO = ("motivo", "motivos", "fatores", "reason", "reason_code",
                     "reasons", "explicacao", "justificativa")


def presentes(dado, chaves) -> list:
    """Procura as chaves em qualquer profundidade do JSON de resposta."""
    achadas = set()
    pilha = [dado]
    while pilha:
        atual = pilha.pop()
        if isinstance(atual, dict):
            for k, v in atual.items():
                if str(k).lower() in chaves:
                    achadas.add(str(k).lower())
                pilha.append(v)
        elif isinstance(atual, list):
            pilha.extend(atual)
    return sorted(achadas)


@check("E-01", "ethics", "Decisao automatizada sem explicacao", base_legal="LGPD Art. 20")
def explicacao(ctx):
    cliente, _ = exigir_alvo(ctx, "passive")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "decisao")

    resposta, trace = cliente.requisitar("GET", rota, token=token_a,
                                         identidade="titular_a")
    dado = resposta.json()
    if dado is None:
        return [Finding(
            check_id="E-01", pack="ethics", severidade=Severidade.ALTO,
            titulo="Decisao nao devolve JSON interpretavel",
            descricao=f"A rota de decisao respondeu {resposta.status} sem corpo "
                      f"JSON — nao ha explicacao a oferecer ao titular.",
            recomendacao="Devolver a decisao em JSON com motivo e fatores.",
            base_legal="LGPD Art. 20", arquivo=rota, linha=1, trace=trace)]

    if presentes(dado, set(CAMPOS_EXPLICACAO)):
        return []
    return [Finding(
        check_id="E-01", pack="ethics", severidade=Severidade.ALTO,
        titulo="Decisao automatizada sem explicacao ao titular",
        descricao=f"A resposta da decisao nao traz nenhum de {list(CAMPOS_EXPLICACAO)}. "
                  f"O titular recebe o resultado sem saber que fatores o "
                  f"produziram, e sem isso nao consegue nem contestar.",
        recomendacao="Devolver motivo legivel e os fatores determinantes "
                     "(reason codes) junto da decisao, nao sob pedido.",
        base_legal="LGPD Art. 20", arquivo=rota, linha=1, trace=trace)]
