"""Tres formas corretas, e nenhuma delas e hash nu.

HMAC com chave de cofre: quem nao tem a chave nao remonta o de-para, e a
chave e destrutivel — o que torna a eliminacao possivel de verdade.
Sal aleatorio POR REGISTRO: nao ha determinismo, entao nao ha ligacao entre
duas ocorrencias do mesmo titular.
E hash de conteudo para integridade nao toca titular nenhum.
"""
import hashlib
import hmac
import secrets

from cofre import chave_do_vault


def exportar(cliente, warehouse):
    pseudonimo = hmac.new(
        chave_do_vault("pseudonimizacao"), cliente.cpf.encode(),
        hashlib.sha256).hexdigest()
    warehouse.insert("dim_cliente", {
        "pseudonimo": pseudonimo,
        "cidade": cliente.cidade,
    })


def marcar_coorte(cliente, warehouse):
    sal = secrets.token_bytes(16)
    marca = hashlib.sha256(sal + cliente.email.encode()).hexdigest()
    warehouse.write("coorte", {"marca": marca, "sal": sal.hex()})


def checksum_do_arquivo(conteudo, warehouse):
    """Integridade de arquivo: nao ha titular nisto."""
    return warehouse.write("arquivos", {
        "sha": hashlib.sha256(conteudo).hexdigest()})
