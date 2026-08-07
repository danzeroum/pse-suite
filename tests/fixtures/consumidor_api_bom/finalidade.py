"""S-22 conforme: a finalidade chega, e a base legal a limita.

As duas metades que o check exige, e nesta ordem porque uma sem a outra nao
vale nada:

  1. O MAPA e um dicionario LITERAL. Cada finalidade que o produto conhece
     declara sob que base do Art. 7o ela roda. Nao ha entrada coringa: uma
     finalidade que ninguem escreveu aqui nao existe para o servidor.
  2. A RECUSA acontece no mesmo ponto em que a finalidade e lida, antes de
     qualquer acesso ao repositorio. Marketing sob legitimo interesse morre
     na porta, e nao no relatorio do DPO seis meses depois.

Repare no que NAO esta no mapa: `analytics`, `melhoria_do_produto`,
`interesse_do_negocio`. Sao finalidades, e finalidade nao e base legal —
confundir as duas e exatamente o defeito que S-22 procura.
"""
from flask import Flask, request

app = Flask(__name__)

BASE_LEGAL_POR_FINALIDADE = {
    "cobranca": "execucao_de_contrato",
    "prevencao_a_fraude": "legitimo_interesse",
    "marketing_segmentado": "consentimento",
    "atendimento": "execucao_de_contrato",
}


class BaseLegalInvalida(Exception):
    """A combinacao finalidade/base que a lei nao permite."""


def exigir_base_legal(finalidade, base_declarada):
    esperada = BASE_LEGAL_POR_FINALIDADE.get(finalidade)
    if esperada is None:
        raise BaseLegalInvalida(
            f"finalidade '{finalidade}' nao consta do mapa de bases legais")
    if esperada != base_declarada:
        raise BaseLegalInvalida(
            f"'{finalidade}' so roda sob {esperada}, e veio {base_declarada}")
    return esperada


@app.get("/relatorios")
def relatorios():
    finalidade = request.headers.get("X-Purpose")
    base = request.headers.get("X-Legal-Basis")
    exigir_base_legal(finalidade, base)
    return repositorio.relatorios(finalidade=finalidade)
