"""O DTO implementa exatamente o que o contrato promete no `x-ethics`.

`Pedido` nao carrega PII nenhuma, entao nao precisa de ontologia — exigir
`x-ethics` de um schema sem dado pessoal seria burocracia, e burocracia
ensina o time a preencher por reflexo.
"""
from pydantic import BaseModel


class Cliente(BaseModel):
    id: str
    cidade: str
    cpf: str
    email: str
    genero: str


class Pedido(BaseModel):
    id: str
    valor: float
    status: str
