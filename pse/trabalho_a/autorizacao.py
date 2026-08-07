"""Contrato de autorizacao do Trabalho A — verificado ANTES de qualquer byte.

A ordem aqui nao e detalhe de implementacao, e a propria seguranca da Fase 2:
o risco desta fase e sondar um alvo sem autorizacao. Por isso a validacao e
escalonada e cada degrau so e alcancado se o anterior passou:

    1. config recusavel  -> EntradaInvalida (exit 30), ANTES do runner existir
    2. modo habilitado?  -> NaoHabilitado (nao bloqueia)
    3. atestacao valida? -> CheckIndeterminado (exit 20)
    4. tokens no ambiente?
    5. healthcheck 200?  -> uma unica vez por execucao
    6. so entao o cliente HTTP e entregue ao check

Nada em 2-6 emite requisicao, exceto o proprio healthcheck no degrau 5.
"""
import hashlib
import os
import re
from datetime import date

from pse.model import CheckIndeterminado, EntradaInvalida, NaoHabilitado

MODOS = ("pse_inventory", "pse_passive", "pse_active")
MODOS_A = ("pse_passive", "pse_active")
# Modo do catalogo -> modos de execucao que o disparam. Um check `passive`
# roda tambem em pse_active; um `active` NUNCA roda em pse_passive.
DISPARA_EM = {"passive": ("pse_passive", "pse_active"), "active": ("pse_active",)}

RX_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# Hosts de loopback. Unica excecao a exigencia de https:// — ver `_e_loopback`.
LOOPBACK = ("127.0.0.1", "localhost", "[::1]", "::1")


def _e_loopback(base_url: str) -> bool:
    """`http://` so e aceito quando o alvo nao sai da maquina.

    MUDANCA DE REGRA, declarada. A exigencia de https existe por UM motivo
    escrito: sonda em texto claro vaza o proprio token de teste na rede. Em
    loopback nao ha rede — o pacote nao passa por interface fisica, nao ha
    intermediario e nao ha o que capturar. A razao da regra nao alcanca este
    caso.

    Sem esta excecao, a camada dinamica nao teria como ser provada contra um
    alvo REAL: o alvo de fixture serve em `http://127.0.0.1`, e gerar
    certificado no teste exigiria dependencia nova e `ignore_https_errors`,
    que e um afrouxamento maior que este.

    Deliberadamente estreita: casa o host de loopback EXATO, nunca por
    substring. `http://127.0.0.1.atacante.com` NAO passa, e ha teste-mordida
    provando. Qualquer outro host em http:// segue recusado com exit 30.
    """
    from urllib.parse import urlsplit
    if not str(base_url).startswith("http://"):
        return False
    try:
        host = (urlsplit(str(base_url)).hostname or "").strip().lower()
    except ValueError:
        return False
    return host in ("127.0.0.1", "localhost", "::1")


def fingerprint_alvo(base_url: str) -> str:
    return hashlib.sha256(str(base_url).strip().encode("utf-8")).hexdigest()


def alvo_de(config: dict) -> dict:
    return (config or {}).get("target") or {}


def habilitado(config: dict) -> bool:
    """Trabalho A esta habilitado quando o consumidor declarou um alvo."""
    return bool(alvo_de(config).get("base_url"))


def validar_config(config: dict, modo: str):
    """Recusas que acontecem ANTES de o runner rodar — nenhuma requisicao.

    Sao as unicas que produzem exit 30: o consumidor pediu algo que a suite
    nao faz, e descobrir isso no meio da execucao ja seria tarde.
    """
    if modo not in MODOS:
        raise EntradaInvalida(f"modo invalido: {modo!r}; use {list(MODOS)}")
    if modo == "pse_inventory":
        return
    if not habilitado(config):
        raise EntradaInvalida(
            f"modo {modo} pedido sem `target.base_url` declarado — nao ha "
            f"contra o que auditar, e a suite nao descobre alvo")

    alvo = alvo_de(config)
    base_url = str(alvo.get("base_url"))
    if not base_url.startswith("https://") and not _e_loopback(base_url):
        raise EntradaInvalida(
            f"target.base_url deve ser https:// (recebido {base_url!r}) — uma "
            f"sonda de autorizacao em texto claro vaza o proprio token de teste")

    ambiente = str(alvo.get("environment") or "").strip().lower()
    if ambiente not in ("staging", "production"):
        raise EntradaInvalida(
            f"target.environment deve ser staging ou production "
            f"(recebido {ambiente!r})")

    # A recusa da v1: sonda ativa so em staging. Levantada aqui, antes de
    # qualquer requisicao — inclusive antes do healthcheck.
    if modo == "pse_active" and ambiente == "production":
        raise EntradaInvalida(
            "pse_active contra environment: production e recusado nesta versao. "
            "Sonda ativa cruza identidades e espera rejeicao; em producao isso "
            "toca dado de titular real. Rode em staging, ou aguarde a dupla "
            "atestacao de uma versao futura")


def validar_atestacao(config: dict, modo: str):
    """Atestacao valida para ESTE modo e ESTE alvo. Invalida -> indeterminado.

    Nunca EntradaInvalida: falta de atestacao nao e erro de digitacao do
    consumidor, e ausencia de autorizacao — e a resposta correta e nao
    auditar, com o motivo visivel e o processo bloqueado (exit 20).
    """
    alvo = alvo_de(config)
    att = alvo.get("authorization") or {}

    if not att:
        raise CheckIndeterminado(
            "Trabalho A habilitado sem bloco `target.authorization` — sem "
            "atestacao humana nenhuma requisicao e emitida")

    quem = str(att.get("attested_by") or "").strip()
    if len(quem) < 3 or quem.lower() in ("ci", "bot", "automacao", "equipe"):
        raise CheckIndeterminado(
            f"attested_by={quem!r} nao identifica um humano responsavel")

    escopo = att.get("scope") or []
    if modo not in escopo:
        raise CheckIndeterminado(
            f"atestacao nao cobre o modo {modo} (scope declarado: {list(escopo)}) "
            f"— autorizar o passivo nao autoriza a sonda ativa")

    prazo = str(att.get("expires") or "")
    if not RX_DATA.match(prazo):
        raise CheckIndeterminado(
            f"expires={prazo!r} ausente ou malformado — autorizacao sem prazo "
            f"e autorizacao permanente, que ninguem revisa")
    if date.fromisoformat(prazo) < date.today():
        raise CheckIndeterminado(
            f"atestacao vencida em {prazo} — renove antes de auditar de novo")

    esperado = fingerprint_alvo(alvo.get("base_url"))
    declarado = str(att.get("target_fingerprint") or "")
    if declarado != esperado:
        raise CheckIndeterminado(
            "target_fingerprint nao corresponde a base_url declarada — a "
            "atestacao foi emitida para outro alvo, e apontar a suite para um "
            "host diferente nao herda autorizacao")

    if modo == "pse_active" and att.get("synthetic_identities") is not True:
        raise CheckIndeterminado(
            "pse_active exige synthetic_identities: true — sonda ativa so "
            "contra contas de teste, sem titular real por tras")

    return att


def token(config: dict, titular: str) -> str:
    """Le o token pelo NOME da variavel. O valor nunca toca o YAML nem o laudo."""
    ident = (alvo_de(config).get("identities") or {}).get(titular) or {}
    nome = ident.get("token_env")
    if not nome:
        raise CheckIndeterminado(
            f"identities.{titular}.token_env nao declarado — sem identidade "
            f"nao ha o que provar")
    if not nome.startswith("PSE_"):
        raise CheckIndeterminado(
            f"token_env={nome!r} fora do prefixo PSE_: o fiscal de higiene de "
            f"ambiente do consumidor cobre PSE_*, e uma variavel fora dele "
            f"escapa da denylist")
    valor = os.environ.get(nome)
    if not valor:
        raise CheckIndeterminado(
            f"variavel {nome} declarada e ausente no ambiente — a suite nao "
            f"adivinha credencial")
    return valor


def endpoint(config: dict, nome: str) -> str:
    """Superficie declarada. Ausente = indeterminado, jamais descoberta."""
    rota = (alvo_de(config).get("endpoints") or {}).get(nome)
    if not rota:
        raise CheckIndeterminado(
            f"endpoint `{nome}` nao declarado em target.endpoints — a suite "
            f"nao sai procurando qual rota testar")
    return rota


def recursos_de_b(config: dict) -> list:
    recursos = alvo_de(config).get("resources_titular_b") or []
    if not recursos:
        raise CheckIndeterminado(
            "recurso de B nao declarado em target.resources_titular_b — "
            "descobrir recurso alheio no alvo e executar exatamente a violacao "
            "que este check existe para impedir")
    return list(recursos)


def exigir_modo(config: dict, modo_execucao: str, modo_check: str):
    """Degrau 2: este check e disparado por este modo de execucao?"""
    if not habilitado(config):
        raise NaoHabilitado(
            "Trabalho A nao habilitado: nenhum `target` declarado em "
            "pse-config.yaml. Check previsto e nao habilitado.")
    if modo_execucao not in DISPARA_EM.get(modo_check, ()):
        raise NaoHabilitado(
            f"check de modo `{modo_check}` nao e disparado por "
            f"`{modo_execucao}` — rode com --modo apropriado e atestacao no escopo")


def resumo_publicavel(att: dict) -> dict:
    """O que do bloco de autorizacao pode ser carimbado no laudo (sem segredo)."""
    return {
        "attested_by": att.get("attested_by"),
        "scope": list(att.get("scope") or []),
        "expires": att.get("expires"),
        "target_fingerprint": att.get("target_fingerprint"),
        "synthetic_identities": att.get("synthetic_identities"),
    }
