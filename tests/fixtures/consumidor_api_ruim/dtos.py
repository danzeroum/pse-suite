"""S-12 vetor B: o contrato promete `telefone`, o DTO nao implementa.

O schema declara em `x-ethics` que a conta carrega cpf e telefone, e que o
escopo `conta:leitura` so ve id e agencia. Quem le o contrato acredita que
existe uma ontologia aplicada; o codigo nunca soube de `telefone`.
"""
from pydantic import BaseModel


class Cliente(BaseModel):
    id: str
    cpf: str
    email: str
    genero: str


class ContaBancaria(BaseModel):
    id: str
    agencia: str
    cpf: str
    # telefone: prometido no x-ethics e nunca implementado
