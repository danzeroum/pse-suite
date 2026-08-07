"""P-19: o topico e append-only e o CPF vai cru, sem chave por titular.

Apagar o titular do banco nao apaga o evento: o registro e imutavel por
construcao, e o dado sobrevive a todo pedido de eliminacao.
"""
from kafka import KafkaProducer

producer = KafkaProducer(bootstrap_servers="kafka:9092")


def registrar_cadastro(cliente):
    producer.send("clientes.cadastrados", {
        "cpf": cliente.cpf,
        "email": cliente.email,
        "genero": cliente.genero,
    })
