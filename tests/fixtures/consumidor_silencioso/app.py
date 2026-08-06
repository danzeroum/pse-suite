"""Fixture da MORDIDA D-01 — violacoes reais + comentarios que as suprimiam.

Em 1eb616b este repositorio produzia 0 findings e exit 0: E-04, E-05 e P-02
suprimiam o achado porque uma *string* aparecia em qualquer lugar do arquivo.
Um comentario desligava uma trava CRITICA, sem rastro de configuracao.

Nada aqui e conforme. Se a suite ficar verde neste diretorio, a trava
voltou a ser desligavel por comentario.
"""


# TODO: implementar revisao_humana algum dia
def negar_credito(user, score):
    """Decisao de alto impacto, 100% automatizada. E-04 CRITICO."""
    if score < 500:
        return {"aprovado": False}
    return {"aprovado": True}


def calcular_score(renda, cep):
    # nota: avaliar equalized_odds no futuro
    features = {"renda": renda, "cep": cep}   # E-05: proxy de discriminacao
    return renda * 0.4 + int(cep[:2]) * 0.1
