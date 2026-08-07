"""P-15 e P-16: CPF vira feature de treino, e o dataset nao tem governanca."""
import pandas as pd
from sklearn.linear_model import LogisticRegression


def treinar():
    df = pd.read_csv("dados/base_clientes.csv")
    modelo = LogisticRegression()
    modelo.fit(df[["cpf", "genero", "renda"]], df["inadimplente"])    # P-15
    return modelo
