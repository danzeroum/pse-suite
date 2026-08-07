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
# Identificador de recurso em URL de trace (Fase 2). Mascarar o UUID e nao a
# rota preserva a leitura do trace ("GET /api/clientes/<id> -> 200") sem
# publicar QUAL recurso do titular B foi sondado.
RX_UUID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I)
RX_HEX_LONGO = re.compile(r"\b[0-9a-f]{24,}\b", re.I)


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
    t = RX_UUID.sub(lambda m: _borda(m.group(0)), t)
    t = RX_HEX_LONGO.sub(lambda m: _borda(m.group(0)), t)
    return t


def sanitizar_profundo(valor):
    """Sanitiza recursivamente dict/list/str — a forma de um trace.

    Chaves nao sao tocadas (sao nomes de campo, nao conteudo do alvo);
    valores sao, em qualquer profundidade.
    """
    if isinstance(valor, dict):
        return {k: sanitizar_profundo(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [sanitizar_profundo(v) for v in valor]
    if isinstance(valor, str):
        return sanitizar(valor)
    return valor


def sanitizar_url(url: str) -> str:
    """Preserva esquema, host e caminho; apaga os VALORES da query.

    A camada dinamica quebrou uma premissa que valia enquanto tudo era
    estatico: em `sanitizar_finding`, `arquivo` era "o endereco do achado,
    nao o seu conteudo" — verdade para `src/App.jsx`, FALSA para
    `https://alvo/fatura?cpf=529.982.247-25`, onde o endereco E o conteudo.

    O nome do parametro fica (e ele que identifica o vazamento e orienta a
    correcao); o valor vira `***`. Um achado de "CPF na query" que
    carimbasse o CPF teria acabado de publicar o dado do titular num
    artefato que circula por CI, anexo de PR e caixa de e-mail.
    """
    from urllib.parse import parse_qsl, urlsplit, urlunsplit
    texto = str(url or "")
    try:
        partes = urlsplit(texto)
    except ValueError:
        return sanitizar(texto)
    if not partes.query:
        return sanitizar(texto)
    apagada = "&".join(f"{nome}=***"
                       for nome, _ in parse_qsl(partes.query,
                                                keep_blank_values=True))
    return sanitizar(urlunsplit((partes.scheme, partes.netloc, partes.path,
                                 apagada, "")))


def _e_url(valor: str) -> bool:
    return str(valor).startswith(("http://", "https://"))


def sanitizar_finding(d: dict) -> dict:
    """Aplica a regua ao que o finding carrega de conteudo do alvo.

    `arquivo` e preservado quando e caminho de arquivo — ali ele e endereco,
    nao conteudo. Quando e URL, passa por `sanitizar_url`: ver a docstring
    de la para o motivo de a premissa antiga nao sobreviver ao dinamico.
    """
    saida = dict(d)
    if saida.get("snippet"):
        saida["snippet"] = sanitizar(saida["snippet"])
    if saida.get("trace"):
        saida["trace"] = sanitizar_profundo(saida["trace"])
    if saida.get("arquivo") and _e_url(saida["arquivo"]):
        saida["arquivo"] = sanitizar_url(saida["arquivo"])
    return saida
