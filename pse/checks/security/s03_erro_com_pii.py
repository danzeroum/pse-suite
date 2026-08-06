"""S-03 — payload de erro carregando dado pessoal.

MODO PASSIVO. Requisicao somente-leitura com a propria identidade do
chamador contra a rota de erro declarada. Nao cruza identidades, nao espera
rejeicao de autorizacao: e leitura de uma superficie que o consumidor
declarou.

ESCOPO DESTA VERSAO: o payload de erro. A outra metade do check no plano —
interceptacao de webhook — exige um receptor declarado, que o contrato de
Trabalho A ainda nao tem; fica registrada aqui como ausencia conhecida, e
nao como algo que este check ja cobre.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.sanitize import RX_CPF, RX_EMAIL, RX_TELEFONE
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo

VALORES = (("CPF", RX_CPF), ("e-mail", RX_EMAIL), ("telefone", RX_TELEFONE))


@check("S-03", "security", "Erro/webhook com PII no payload", base_legal="LGPD Art. 46")
def erro_com_pii(ctx):
    cliente, _ = exigir_alvo(ctx, "passive")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "erro")

    resposta, trace = cliente.requisitar("GET", rota, token=token_a,
                                         identidade="titular_a")
    corpo = resposta.corpo or ""
    achou = [rotulo for rotulo, rx in VALORES if rx.search(corpo)]

    # Nomes de campo de PII na regua curada tambem denunciam: um erro que
    # devolve {"cpf": ...} vaza mesmo que o valor esteja truncado.
    termos = {t.lower() for grupo in ctx.data["pii-patterns"].values() for t in grupo}
    campos = sorted(t for t in termos if f'"{t}"' in corpo.lower())

    if not achou and not campos:
        return []

    detalhe = ", ".join(achou + [f"campo '{c}'" for c in campos])
    return [Finding(
        check_id="S-03", pack="security", severidade=Severidade.ALTO,
        titulo="Payload de erro devolve dado pessoal",
        descricao=f"A resposta de erro ({resposta.status}) carrega {detalhe}. "
                  f"Payload de erro costuma ir para log de terceiro, "
                  f"rastreador de excecao e tela de usuario — tres lugares onde "
                  f"o dado nao deveria estar.",
        recomendacao="Padronizar erros com codigo e mensagem generica; mover o "
                     "detalhe para log interno correlacionado por trace-id.",
        base_legal="LGPD Art. 46",
        arquivo=rota, linha=1, trace=trace)]
