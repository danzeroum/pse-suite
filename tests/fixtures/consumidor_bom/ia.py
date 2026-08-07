"""O lado conforme de E-11 e E-12."""
import llm_client as llm

from indexador import broker, modelo
from redacao import redact


def resumir_atendimento(user):
    # E-11 conforme: o prompt passa por redacao que EXECUTA antes de sair.
    prompt = f"cliente {user.cpf} pediu reembolso"
    return llm.complete(redact(prompt))


def indexar_perfil(user):
    # E-12 conforme: o campo de origem esta no catalogo como personal, entao
    # o derivado nao esta sendo tratado como anonimo.
    embedding_do_cpf = modelo.encode(user.cpf)
    broker.send(embedding_do_cpf)
