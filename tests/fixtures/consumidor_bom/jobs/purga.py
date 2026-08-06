"""P-02 conforme: job de purga EXECUTAVEL — funcao que apaga de verdade.

Declarar retention_years no catalogo nao e implementar a purga. O que
satisfaz o check e este codigo: uma funcao de expurgo cujo corpo executa
uma operacao de eliminacao.
"""
from datetime import datetime, timedelta

from db import conexao


def purgar_expirados(anos=5):
    corte = datetime.utcnow() - timedelta(days=365 * anos)
    with conexao() as cur:
        cur.execute("DELETE FROM clientes WHERE criado_em < %s", (corte,))
        cur.execute("DELETE FROM contratos WHERE criado_em < %s", (corte,))
    registrar_evidencia_de_eliminacao(corte)


def registrar_evidencia_de_eliminacao(corte):
    """Art. 16: a eliminacao deixa prova auditavel."""
    with conexao() as cur:
        cur.execute("INSERT INTO ledger_purga (corte, executado_em) VALUES (%s, now())", (corte,))
