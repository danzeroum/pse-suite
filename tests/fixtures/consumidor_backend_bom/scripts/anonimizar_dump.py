"""Substituicao irreversivel: o valor original nao volta de lugar nenhum."""
import sys

from faker import Faker


def anonimizar(entrada, saida):
    fake = Faker("pt_BR")
    with open(entrada) as f, open(saida, "w") as g:
        for linha in f:
            g.write(mascarar(linha, fake))


if __name__ == "__main__":
    anonimizar(sys.argv[1], sys.argv[2])
