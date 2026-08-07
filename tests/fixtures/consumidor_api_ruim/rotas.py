"""P-17: a rota de busca aceita filtro sensivel, sem guarda nenhuma."""
from flask import Flask, request

app = Flask(__name__)


@app.get("/clientes")
def buscar_clientes():
    raca = request.args.get("raca")
    cep = request.args.get("cep")
    return repositorio.buscar(raca=raca, cep=cep)


@app.get("/parceiros/<pid>/clientes")
def buscar_por_parceiro(pid, genero=None, renda=None):
    return repositorio.buscar(parceiro=pid, genero=genero, renda=renda)


@app.get("/pedidos")
def buscar_pedidos():
    # Sem filtro proibido: nao ha achado aqui, e e o controle da fixture.
    status = request.args.get("status")
    return repositorio.pedidos(status=status)
