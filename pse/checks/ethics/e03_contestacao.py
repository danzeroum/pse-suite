"""E-03 — contestacao: o recurso existe e devolve protocolo e prazo.

MODO ATIVO: abre um recurso de verdade no alvo, entao exige escopo ativo,
staging e identidades sinteticas atestadas.

Direito de revisao sem protocolo e sem prazo e direito no papel: o titular
contesta e nunca sabe se alguem recebeu, nem ate quando teria resposta.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo
from .e01_explicacao import presentes

PROTOCOLO = ("protocolo", "protocol", "ticket", "id", "numero", "referencia")
PRAZO = ("sla", "prazo", "prazo_dias", "deadline", "previsao", "due_date")


@check("E-03", "ethics", "Contestacao com protocolo e SLA", base_legal="LGPD Art. 18")
def contestacao(ctx):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "contestacao")

    corpo = {"motivo": "sonda-pse-contestacao", "origem": "pse-suite"}
    resposta, trace = cliente.requisitar("POST", rota, token=token_a,
                                         corpo=corpo, identidade="titular_a")

    if resposta.status >= 400:
        return [Finding(
            check_id="E-03", pack="ethics", severidade=Severidade.ALTO,
            titulo="Rota de contestacao nao aceita pedido de revisao",
            descricao=f"POST em {rota} respondeu {resposta.status}. O direito a "
                      f"revisao (Art. 18) nao tem por onde ser exercido.",
            recomendacao="Expor endpoint de contestacao que aceite o pedido e "
                         "devolva protocolo rastreavel e prazo de resposta.",
            base_legal="LGPD Art. 18", arquivo=rota, linha=1, trace=trace)]

    dado = resposta.json() or {}
    faltando = []
    if not presentes(dado, set(PROTOCOLO)):
        faltando.append("protocolo rastreavel")
    if not presentes(dado, set(PRAZO)):
        faltando.append("prazo/SLA de resposta")
    if not faltando:
        return []
    return [Finding(
        check_id="E-03", pack="ethics", severidade=Severidade.ALTO,
        titulo="Contestacao aceita sem protocolo ou sem prazo",
        descricao=f"A contestacao foi aceita ({resposta.status}) mas a resposta "
                  f"nao traz: {', '.join(faltando)}. O titular contesta e fica "
                  f"sem saber se alguem recebeu, nem ate quando tera resposta.",
        recomendacao="Devolver protocolo rastreavel e prazo na propria resposta "
                     "de abertura; notificar mudanca de estado.",
        base_legal="LGPD Art. 18", arquivo=rota, linha=1, trace=trace)]
