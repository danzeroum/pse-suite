"""P-05 — minimizacao: campo fora da allowlist deve ser rejeitado.

MODO ATIVO, E ESCREVE DE VERDADE. Envia um POST com um campo que o
consumidor nunca declarou. Se o alvo aceitar, a API coleta o que lhe
mandarem — e a minimizacao (Art. 6o III) nao esta sendo aplicada na borda.

Por escrever, so roda com `synthetic_identities: true` atestado e em
staging. O campo plantado leva prefixo reconhecivel para que qualquer
registro criado por esta sonda seja identificavel e removivel.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo

CAMPO_PLANTADO = "__pse_campo_nao_declarado"
REJEICAO = (400, 409, 422)


@check("P-05", "privacy", "Minimizacao por jornada", base_legal="LGPD Art. 6o III")
def minimizacao(ctx):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "escrita")

    corpo = {CAMPO_PLANTADO: "sonda-pse-minimizacao"}
    resposta, trace = cliente.requisitar("POST", rota, token=token_a,
                                         corpo=corpo, identidade="titular_a")

    if resposta.status in REJEICAO:
        return []                          # rejeitou o campo extra — conforme
    if resposta.status in (401, 403):
        return []                          # nao chegou a avaliar o payload
    if resposta.status < 300:
        return [Finding(
            check_id="P-05", pack="privacy", severidade=Severidade.ALTO,
            titulo="Endpoint aceita campo fora da allowlist",
            descricao=f"POST com o campo nao declarado '{CAMPO_PLANTADO}' "
                      f"retornou {resposta.status}. O serializador aceita o que "
                      f"lhe mandarem: qualquer campo extra enviado por um "
                      f"cliente entra no sistema sem finalidade nem base legal.",
            recomendacao="Allowlist explicita no DTO/serializer: campo fora da "
                         "lista rejeita a requisicao, nao e ignorado em silencio "
                         "(ignorar tambem esconde o erro de quem integra).",
            base_legal="LGPD Art. 6o III",
            arquivo=rota, linha=1, trace=trace)]
    return []
