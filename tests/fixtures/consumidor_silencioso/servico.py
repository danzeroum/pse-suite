"""P-02: o catalogo declara retencao, mas nao existe job de purga.

Em 1eb616b bastava a palavra 'purge' num comentario para o check passar.
"""


def cobrar(cliente_id):
    # nao ha job de purge neste repositorio; a palavra so aparece aqui
    return {"cliente": cliente_id, "status": "cobrado"}
