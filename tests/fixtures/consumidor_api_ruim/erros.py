"""S-13: o handler de erro devolve traceback, caminho e versao ao cliente.

S-03 pega PII no payload de erro. Este pega a ESTRUTURA: pilha, caminho de
arquivo no disco e versao de framework — o mapa que o atacante usaria para
escolher o exploit.
"""
import sys
import traceback

from flask import Flask, jsonify

app = Flask(__name__)


@app.errorhandler(500)
def falha_interna(e):
    return jsonify({
        "erro": "falha",
        "trace": traceback.format_exc(),
        "modulo": __file__,
        "runtime": sys.version,
    }), 500


def salvar(payload):
    try:
        return repositorio.salvar(payload)
    except Exception as e:  # noqa: BLE001
        return jsonify({"detalhe": traceback.format_exception(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
