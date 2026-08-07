"""Violacoes de IA e cadeia de terceiros — E-11 e E-12."""
import llm_client as llm

from indexador import broker, modelo


def resumir_atendimento(user):
    # TODO: redact antes de mandar pro modelo
    return llm.complete(f"cliente {user.cpf} pediu reembolso")      # E-11 CRITICO


def indexar_perfil(user):
    embedding_do_usuario = modelo.encode(user.nome_completo)
    broker.send(embedding_do_usuario)                               # E-12
