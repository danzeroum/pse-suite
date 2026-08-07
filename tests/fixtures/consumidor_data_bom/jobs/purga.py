"""P-02: a retencao declarada tem um job que apaga de verdade."""
from datetime import datetime, timedelta

from db import conexao


def purgar_expirados(anos=5):
    corte = datetime.utcnow() - timedelta(days=365 * anos)
    with conexao() as cur:
        cur.execute("DELETE FROM clientes WHERE criado_em < %s", (corte,))
        cur.execute("DELETE FROM dim_cliente WHERE criado_em < %s", (corte,))
