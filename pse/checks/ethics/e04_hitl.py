import re
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

DECISOES = (r"(bloquear_conta|negar_credito|rejeitar_emprestimo|suspender_perfil"
            r"|excluir_conta|negar_seguro|recusar_beneficio)")
RX_REVISAO = re.compile(
    r"revisao_humana|human_in_the_loop|human_review|fila_revisao|para_analista", re.I)


@check("E-04", "ethics", "Decisao critica sem rota humana", base_legal="LGPD Art. 20 §3")
def hitl(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, {".py", ".js", ".ts", ".java", ".go"}):
        hits = scan.grep(p, DECISOES)
        if not hits or RX_REVISAO.search(scan.ler(p)):
            continue
        linha, snippet = hits[0]
        findings.append(Finding(
            check_id="E-04", pack="ethics", severidade=Severidade.CRITICO,
            titulo="Decisao de alto impacto 100% automatizada",
            descricao="Acao que afeta direitos (credito, conta, beneficio) sem "
                      "nenhuma rota de revisao humana no mesmo modulo.",
            recomendacao="Encaminhar decisoes limitrofes/incertas para analista "
                         "e registrar evidencia da revisao (decision log).",
            base_legal="LGPD Art. 20 §3",
            arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet))
    return findings
