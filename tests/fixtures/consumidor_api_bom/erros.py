"""Erro padronizado: correlacao para quem opera, nada para quem ataca.

O traceback vai para o log estruturado — que fica do lado de dentro. O
cliente recebe um identificador e uma mensagem estavel. E a distincao que
S-13 cobra: observabilidade nao exige entregar a topologia do disco.
"""
import logging
import uuid

from flask import Flask, jsonify

app = Flask(__name__)
log = logging.getLogger(__name__)


@app.errorhandler(500)
def falha_interna(e):
    correlacao = str(uuid.uuid4())
    log.exception("falha interna", extra={"correlacao": correlacao})
    return jsonify({"erro": "falha_interna", "correlacao": correlacao}), 500


def salvar(payload):
    try:
        return repositorio.salvar(payload)
    except Exception:  # noqa: BLE001
        correlacao = str(uuid.uuid4())
        log.exception("falha ao salvar", extra={"correlacao": correlacao})
        return jsonify({"erro": "falha_ao_salvar", "correlacao": correlacao}), 500


if __name__ == "__main__":
    app.run(debug=False)
