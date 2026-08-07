"""Duas formas corretas de nao aceitar filtro sensivel.

A primeira nao menciona filtro proibido nenhum: o vocabulario de busca e
fechado, e o que nao esta nele nao chega ao repositorio. A segunda aceita um
campo do vocabulario amplo mas passa pela guarda que EXECUTA — e o D-08: um
pipeline que ja aplica allowlist nao pode receber achado.
"""
from flask import Flask, request

app = Flask(__name__)

FILTROS_PERMITIDOS = {"cidade", "status", "criado_em"}


def validar_filtros(recebidos):
    return {k: v for k, v in recebidos.items() if k in FILTROS_PERMITIDOS}


@app.get("/clientes")
def buscar_clientes():
    cidade = request.args.get("cidade")
    return repositorio.buscar(cidade=cidade)


@app.get("/pedidos")
def buscar_pedidos():
    filtros = validar_filtros(request.args)
    return repositorio.pedidos(**filtros)
