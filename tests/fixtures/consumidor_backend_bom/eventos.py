"""Crypto-shredding: o evento e cifrado com a chave do titular.

Eliminar o titular destroi a chave, e o evento imutavel vira ruido — a
unica eliminacao que funciona num registro append-only.
"""
from kafka import KafkaProducer

from cripto import cifrar_com_chave_do_titular, destroy_key

producer = KafkaProducer(bootstrap_servers="kafka:9092")


def registrar_cadastro(cliente):
    producer.send("clientes.cadastrados", cifrar_com_chave_do_titular({
        "cpf": cliente.cpf,
        "email": cliente.email,
    }, cliente.id))


def esquecer(titular_id):
    """Art. 18 VI num log imutavel."""
    return destroy_key(titular_id)
