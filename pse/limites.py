"""Faixas permitidas dos thresholds declarados pelo consumidor.

O plano §4 e explicito: "a suite valida faixa permitida (k >= 5); consumidor
nao afrouxa abaixo do piso". Um threshold que o vigiado escolhe livremente
nao e uma regua — e um campo de configuracao com nome de regua.

Afrouxar alem do limite nao vira achado: vira **entrada invalida** (exit 30).
Achado o operador pode aprender a ignorar; recusa de execucao, nao.
"""
from pse.model import EntradaInvalida

# nome -> (piso, teto, direcao_segura)
# `direcao_segura` diz para que lado o consumidor PODE mexer sem afrouxar.
FAIXAS = {
    "k_anonymity_min": {
        "piso": 5, "teto": None, "seguro": "aumentar",
        "porque": "celula de agregacao com menos de 5 titulares reidentifica",
    },
    "dpd_max_delta": {
        "piso": 0.0, "teto": 0.10, "seguro": "diminuir",
        "porque": "disparidade acima de 10 pontos entre grupos nao e ruido "
                  "de medicao, e efeito",
    },
}

PADROES = {"k_anonymity_min": 5, "dpd_max_delta": 0.05}


def valor(config: dict, nome: str):
    """Threshold efetivo, ja validado contra a faixa da suite."""
    declarados = (config or {}).get("thresholds") or {}
    if nome not in declarados:
        return PADROES[nome]
    v = declarados[nome]
    if not isinstance(v, (int, float)) or isinstance(v, bool):
        raise EntradaInvalida(f"threshold {nome}={v!r} nao e numerico")
    return v


def validar(config: dict):
    """Recusa qualquer threshold fora da faixa. Chamado antes de auditar."""
    declarados = (config or {}).get("thresholds") or {}
    for nome, v in declarados.items():
        faixa = FAIXAS.get(nome)
        if faixa is None:
            raise EntradaInvalida(
                f"threshold desconhecido: {nome!r}. A suite so aceita "
                f"{sorted(FAIXAS)} — um threshold que ela nao conhece e um "
                f"threshold que ela nao valida")
        v = valor(config, nome)
        if faixa["piso"] is not None and v < faixa["piso"]:
            raise EntradaInvalida(
                f"{nome}={v} abaixo do piso da suite ({faixa['piso']}): "
                f"{faixa['porque']}. O consumidor pode {faixa['seguro']}, "
                f"nunca afrouxar")
        if faixa["teto"] is not None and v > faixa["teto"]:
            raise EntradaInvalida(
                f"{nome}={v} acima do teto da suite ({faixa['teto']}): "
                f"{faixa['porque']}. O consumidor pode {faixa['seguro']}, "
                f"nunca afrouxar")
