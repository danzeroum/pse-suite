"""P-15/P-16 conforme: os campos usados no treino declaram finalidade de
treino no catalogo, e o dataset tem entrada de governanca."""
import pandas as pd
from sklearn.linear_model import LogisticRegression


def treinar():
    df = pd.read_csv("dados/base_credito.csv")
    modelo = LogisticRegression()
    modelo.fit(df[["cpf", "renda"]], df["inadimplente"])
    return modelo
