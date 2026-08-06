"""S-07 — propagacao de finalidade (X-Purpose) + log de auditoria estruturado.

MODO ATIVO — e nao passivo, como o catalogo declarava na Fase 2. A primeira
metade do check envia uma requisicao SEM `X-Purpose` esperando que o alvo a
recuse; pela regra ratificada, sonda que espera rejeicao e ativa, e ser
somente-leitura nao a torna passiva. Reclassificado na direcao conservadora.

Duas metades, uma causa: sem finalidade propagada, o log de auditoria
registra QUE alguem leu um dado, nunca PARA QUE. E "para que" e a unica
pergunta que o Art. 37 realmente faz.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo
from ..ethics.e01_explicacao import presentes

CAMPOS_LOG = {
    "quem": ("ator", "actor", "usuario", "user", "sujeito", "principal"),
    "o que": ("acao", "action", "operacao", "evento", "event"),
    "quando": ("timestamp", "quando", "data", "occurred_at", "criado_em"),
    "sobre o que": ("recurso", "resource", "objeto", "entidade", "alvo"),
    "para que": ("finalidade", "purpose", "proposito", "motivo"),
}
REJEICAO = (400, 403, 422, 428)


def _sem_finalidade(ctx, cliente, token, findings):
    rota = autorizacao.endpoint(ctx.config, "listagem")
    resposta, trace = cliente.requisitar("GET", rota, token=token,
                                         identidade="titular_a")
    if resposta.status in REJEICAO:
        return                          # exigiu finalidade — conforme
    if resposta.status >= 500:
        return
    findings.append(Finding(
        check_id="S-07", pack="security", severidade=Severidade.ALTO,
        titulo="Requisicao sem X-Purpose e atendida",
        descricao=f"GET em {rota} sem o cabecalho X-Purpose respondeu "
                  f"{resposta.status}. A finalidade nao e propagada nem exigida: "
                  f"o dado sai do sistema sem que ninguem registre para que foi "
                  f"lido, e nenhum log posterior consegue reconstruir isso.",
        recomendacao="Exigir X-Purpose validado contra a lista de finalidades "
                     "do catalogo; recusar 428 quando ausente e propagar o "
                     "valor ate o log de auditoria.",
        base_legal="LGPD Art. 37", arquivo=rota, linha=1, trace=trace))


def _log_estruturado(ctx, cliente, token, findings):
    rota = autorizacao.endpoint(ctx.config, "log_auditoria")
    resposta, trace = cliente.requisitar(
        "GET", rota, token=token, identidade="titular_a",
        extra_headers={"X-Purpose": "auditoria_pse"})

    if resposta.status >= 400:
        findings.append(Finding(
            check_id="S-07", pack="security", severidade=Severidade.ALTO,
            titulo="Log de auditoria nao consultavel",
            descricao=f"GET em {rota} respondeu {resposta.status}. Um log que o "
                      f"auditor nao consegue ler nao e trilha de auditoria.",
            recomendacao="Expor consulta autenticada ao log estruturado.",
            base_legal="LGPD Art. 37", arquivo=rota, linha=1, trace=trace))
        return

    dado = resposta.json()
    amostra = dado[0] if isinstance(dado, list) and dado else dado
    if not isinstance(amostra, (dict, list)):
        findings.append(Finding(
            check_id="S-07", pack="security", severidade=Severidade.ALTO,
            titulo="Log de auditoria sem estrutura",
            descricao="A amostra do log nao e um registro estruturado — "
                      "texto livre nao e auditavel por terceiro.",
            recomendacao="Emitir log em JSON com campos fixos.",
            base_legal="LGPD Art. 37", arquivo=rota, linha=1, trace=trace))
        return

    faltando = [rotulo for rotulo, aliases in CAMPOS_LOG.items()
                if not presentes(amostra, set(aliases))]
    if faltando:
        findings.append(Finding(
            check_id="S-07", pack="security", severidade=Severidade.ALTO,
            titulo="Log de auditoria incompleto",
            descricao=f"A amostra do log nao registra: {', '.join(faltando)}. "
                      f"Sem 'para que', o log diz que alguem leu o dado e nunca "
                      f"por que — que e a unica pergunta do Art. 37.",
            recomendacao="Registrar ator, acao, timestamp, recurso e finalidade "
                         "em todo acesso a dado pessoal.",
            base_legal="LGPD Art. 37", arquivo=rota, linha=1, trace=trace))


@check("S-07", "security", "Propagacao de finalidade e log", base_legal="LGPD Art. 37")
def finalidade(ctx):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    findings = []
    _sem_finalidade(ctx, cliente, token_a, findings)
    _log_estruturado(ctx, cliente, token_a, findings)
    return findings
