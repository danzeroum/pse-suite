"""S-22: o sistema que passa em S-07 e reprova aqui.

Este arquivo faz TUDO o que S-07 pede. A finalidade e exigida (sem ela a
requisicao morre em 428), e propagada, e vai inteira para o log de auditoria
com ator, acao, recurso e timestamp. Um auditor lendo a trilha reconstroi
para que cada dado foi lido, que e a pergunta do Art. 37.

E nada, em lugar nenhum, diz sob que base legal aquela finalidade podia
rodar. `X-Purpose: marketing_segmentado` passa igual a `cobranca`, e o
processamento acontece sob o que o time achar. O log, que era a prova de
conformidade, vira a prova documental da infracao: ele registra com precisao
que a operacao ilegal aconteceu, e para que.

O comentario abaixo tambem esta aqui de proposito. Ele cita a checagem que
nao existe, e nao pode ligar nem desligar nada (D-01).
"""
from flask import Flask, request

app = Flask(__name__)


@app.get("/relatorios")
def relatorios():
    # TODO: validar legal basis por finalidade antes do acesso
    finalidade = request.headers.get("X-Purpose")
    if not finalidade:
        return {"erro": "X-Purpose obrigatorio"}, 428
    auditoria.registrar(
        ator=request.headers.get("X-Actor"),
        acao="leitura",
        recurso="/relatorios",
        finalidade=finalidade,
    )
    return repositorio.relatorios(finalidade=finalidade)
