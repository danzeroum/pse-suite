"""P-07 — consentimento granular por finalidade, opt-in, com registro.

DUAS METADES. A estatica valida o modelo de consentimento declarado contra
`consent-model-1.0.json` — o schema existia desde a Fase 2, antes do check,
porque e ele que define o que sera cobrado. A runtime (MODO ATIVO) bate na
rota protegida por consentimento SEM declarar finalidade consentida e exige
recusa: sonda que espera rejeicao e ativa.

Consentimento pre-marcado nao e consentimento, e consentimento irrevogavel
nao e consentimento — as duas coisas o schema ja recusa por construcao
(`opt_in: const true`, `revogavel: const true`).
"""
import yaml

from pse.engine.registry import check
from pse.model import (CheckIndeterminado, Finding, NaoHabilitado,
                       Severidade)
from pse.schemas_validate import erros_de
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo

REJEICAO = (401, 403, 428, 451)


def _estatico(ctx, findings):
    rel = ctx.config.get("consent_model_path", "tests/qa/consent-model.yaml")
    arq = ctx.repo / rel
    if not arq.exists():
        findings.append(Finding(
            check_id="P-07", pack="privacy", severidade=Severidade.ALTO,
            titulo="Modelo de consentimento ausente",
            descricao=f"Nenhum modelo em {rel}. Sem finalidades declaradas nao "
                      f"ha como saber a que o titular consentiu — nem para "
                      f"registrar, nem para revogar.",
            recomendacao=f"Criar {rel} conforme pse/schemas/consent-model-1.0.json.",
            base_legal="LGPD Art. 7o-8o", arquivo=rel, linha=1))
        return
    try:
        modelo = yaml.safe_load(arq.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise CheckIndeterminado(f"modelo de consentimento ilegivel: {e}") from e

    for erro in erros_de("consent-model-1.0.json", modelo):
        caminho = "/".join(map(str, erro.path)) or "<raiz>"
        findings.append(Finding(
            check_id="P-07", pack="privacy", severidade=Severidade.ALTO,
            titulo=f"Modelo de consentimento invalido em '{caminho}'",
            descricao=f"{erro.message} (schema consent-model-1.0). "
                      f"Consentimento pre-marcado ou irrevogavel e recusado "
                      f"pelo proprio schema.",
            recomendacao="Ajustar o modelo: finalidade granular, opt_in "
                         "explicito, revogacao existente e registro da prova.",
            base_legal="LGPD Art. 7o-8o", arquivo=rel, linha=1))


def _runtime(ctx, findings):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "consentimento_protegido")

    resposta, trace = cliente.requisitar("GET", rota, token=token_a,
                                         identidade="titular_a")
    if resposta.status in REJEICAO or resposta.status >= 500:
        return
    if resposta.status < 300:
        findings.append(Finding(
            check_id="P-07", pack="privacy", severidade=Severidade.CRITICO,
            titulo="Rota protegida por consentimento responde sem consentimento",
            descricao=f"GET em {rota} sem finalidade consentida respondeu "
                      f"{resposta.status}. O consentimento existe no papel e nao "
                      f"e verificado na borda: o dado sai independentemente do "
                      f"que o titular autorizou.",
            recomendacao="Verificar consentimento vigente por finalidade no "
                         "servidor, recusando 403 quando ausente ou revogado.",
            base_legal="LGPD Art. 7o-8o", arquivo=rota, linha=1, trace=trace))


@check("P-07", "privacy", "Consentimento granular", base_legal="LGPD Art. 7o-8o")
def consentimento(ctx):
    findings = []
    _estatico(ctx, findings)
    try:
        _runtime(ctx, findings)
    except NaoHabilitado as e:
        # A metade estatica vale por si, mas a cobertura parcial nao pode
        # ficar invisivel: um check "executado" que so rodou metade e uma
        # meia-verdade no laudo.
        ctx.relatorio("cobertura_parcial", {
            **ctx.relatorios.get("cobertura_parcial", {}),
            "P-07": f"metade runtime nao executada: {e}"})
    return findings
