"""D-02 — a evidencia nao pode vazar o que ela prova que nao vaza.

Em 1eb616b o laudo arquivava em claro, dentro de `harness/runs/`, o CPF, o
e-mail e a chave de producao que os checks acabavam de denunciar. A regua
existe justamente para isso: a suite aplica em si mesma o padrao que cobra
dos outros (plano §5.2 e §9 risco 3).

Mascaramento por borda: preserva 2 caracteres para que a pessoa que le o
laudo reconheca o achado, e apaga o resto. O localizador de um finding e
`arquivo:linha` — nunca o literal. Sanitizar nunca pode custar rastreabilidade.
"""
import re
from pathlib import Path

import yaml

_DATA = Path(__file__).resolve().parent / "data"
BORDA = 2


def _credenciais_da_regua() -> list:
    try:
        grupos = yaml.safe_load((_DATA / "pii-patterns.yaml").read_text(encoding="utf-8"))
        return list(grupos.get("credenciais", []))
    except (OSError, yaml.YAMLError):        # pragma: no cover
        return []


# Nomes que denunciam segredo. A regua curada entra aqui — outra razao para
# ela nunca ser copiavel pelo consumidor.
_NOMES_SECRETOS = "|".join(sorted(set(
    ["key", "secret", "token", "senha", "password", "pwd", "credential",
     "authorization", "passwd", "apikey"] + _credenciais_da_regua())))

RX_ATRIB_ASPAS = re.compile(
    rf"(\b\w*(?:{_NOMES_SECRETOS})\w*\b\s*[:=]\s*)(['\"])([^'\"]{{4,}})(\2)", re.I)
RX_ATRIB_NUA = re.compile(
    rf"(\b\w*(?:{_NOMES_SECRETOS})\w*\b\s*[:=]\s*)([^\s'\"#,;)]{{8,}})", re.I)
RX_BEARER = re.compile(r"\b(Bearer|Basic)\s+([A-Za-z0-9._\-+/=]{8,})", re.I)
RX_CPF = re.compile(r"\b(\d{2})\d\.?\d{3}\.?\d{3}-?\d{2}\b")
RX_EMAIL = re.compile(r"\b([A-Za-z0-9._%+-]{1,})@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
RX_TELEFONE = re.compile(r"(?<![\w.])(\(?\d{2}\)?[\s-]?)(9?\d{4})[\s-]?(\d{4})(?![\w.])")


def _borda(valor: str) -> str:
    if len(valor) <= BORDA:
        return "*" * len(valor)
    return valor[:BORDA] + "***"


def sanitizar(texto):
    """Mascara PII e segredos preservando a forma do achado.

    Idempotente: aplicar duas vezes nao degrada mais o texto.
    """
    if not texto:
        return texto
    t = str(texto)
    t = RX_ATRIB_ASPAS.sub(lambda m: f"{m.group(1)}{m.group(2)}{_borda(m.group(3))}{m.group(4)}", t)
    t = RX_ATRIB_NUA.sub(lambda m: f"{m.group(1)}{_borda(m.group(2))}", t)
    t = RX_BEARER.sub(lambda m: f"{m.group(1)} {_borda(m.group(2))}", t)
    t = RX_CPF.sub(lambda m: f"{m.group(1)}*.***.***-**", t)
    t = RX_EMAIL.sub(lambda m: f"{_borda(m.group(1))}@***", t)
    t = RX_TELEFONE.sub(lambda m: f"{m.group(1)}****-****", t)
    return t


def sanitizar_finding(d: dict) -> dict:
    """Aplica a regua ao que o finding carrega de conteudo do alvo.

    `arquivo` e `linha` sao preservados intactos: sao o endereco do achado,
    nao o seu conteudo.
    """
    saida = dict(d)
    if saida.get("snippet"):
        saida["snippet"] = sanitizar(saida["snippet"])
    return saida
