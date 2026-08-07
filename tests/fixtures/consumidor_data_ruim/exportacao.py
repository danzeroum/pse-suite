"""P-20: SHA-256 nu de CPF gravado numa coluna chamada de anonima.

O CPF tem ~10^11 valores validos. Um dicionario completo de sha256 sobre
esse espaco se constroi em segundos num laptop — entao o "anonimo" e uma
tabela de-para que qualquer um remonta.
"""
import hashlib


def exportar(cliente, warehouse):
    # anonimizado antes de sair do dominio
    id_anonimo = hashlib.sha256(cliente.cpf.encode()).hexdigest()
    warehouse.insert("dim_cliente", {
        "id_anonimo": id_anonimo,
        "cidade": cliente.cidade,
    })


def marcar_coorte(cliente, warehouse):
    marca = hashlib.md5(cliente.email.encode()).hexdigest()
    warehouse.write("coorte", {"marca": marca})


def perfil_sensivel(cliente, warehouse):
    chave = hashlib.sha1(cliente.biometria.encode()).hexdigest()
    warehouse.insert("perfil", {"chave": chave})
