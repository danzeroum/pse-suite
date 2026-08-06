"""E-04 — decisao critica sem rota de revisao humana.

ANCORA NO FATO (D-01): a rota de revisao so conta se for uma CHAMADA que
executa. Em 1eb616b bastava a string aparecer em qualquer lugar do arquivo:
`# TODO: implementar revisao_humana algum dia` desligava um CRITICO.
Comentario nao roteia ninguem para analista nenhum.
"""
import ast
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

DECISOES = (r"(bloquear_conta|negar_credito|rejeitar_emprestimo|suspender_perfil"
            r"|excluir_conta|negar_seguro|recusar_beneficio)")
RX_DECISAO = re.compile(DECISOES, re.I)
RX_REVISAO = re.compile(
    r"revisao_humana|human_in_the_loop|human_review|fila_revisao|para_analista", re.I)

PY = {".py"}
OUTRAS = {".js", ".ts", ".java", ".go"}


def _revisa(no: ast.AST) -> bool:
    """Ha, dentro deste no, uma chamada a rotina de revisao humana?"""
    return any(RX_REVISAO.search(nome) for _, nome in scan.chamadas(no))


def _funcoes(arvore):
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            yield no


def _python(ctx, p, findings):
    arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
    # Um nivel de indirecao: funcoes locais que de fato encaminham para revisao.
    encaminham = {f.name for f in _funcoes(arvore) if _revisa(f)}

    for fn in _funcoes(arvore):
        if not RX_DECISAO.search(fn.name):
            continue
        chamadas = {nome for _, nome in scan.chamadas(fn)}
        if _revisa(fn) or any(c.split(".")[-1] in encaminham for c in chamadas):
            continue                  # a rota existe e executa — conforme
        findings.append(Finding(
            check_id="E-04", pack="ethics", severidade=Severidade.CRITICO,
            titulo="Decisao de alto impacto 100% automatizada",
            descricao=f"'{fn.name}' decide sobre direitos (credito, conta, "
                      "beneficio) e nao chama nenhuma rota de revisao humana. "
                      "Mencao em comentario nao conta: so chamada que executa.",
            recomendacao="Encaminhar decisoes limitrofes/incertas para analista "
                         "e registrar evidencia da revisao (decision log).",
            base_legal="LGPD Art. 20 §3",
            arquivo=scan.rel(ctx.repo, p), linha=fn.lineno,
            snippet=f"def {fn.name}(...)"))


def _heuristica(ctx, p, findings):
    """Linguagens sem AST na v0.x: comentarios e literais ja foram apagados
    por `scan.grep`, entao a mencao em comentario tambem nao suprime aqui."""
    hits = scan.grep(p, DECISOES)
    if not hits:
        return
    if RX_REVISAO.search(scan.codigo_efetivo(scan.ler(p), p.suffix,
                                             sem_literais=True)):
        return
    linha, snippet = hits[0]
    findings.append(Finding(
        check_id="E-04", pack="ethics", severidade=Severidade.CRITICO,
        titulo="Decisao de alto impacto 100% automatizada",
        descricao="Acao que afeta direitos (credito, conta, beneficio) sem "
                  "nenhuma rota de revisao humana no codigo que executa.",
        recomendacao="Encaminhar decisoes limitrofes/incertas para analista "
                     "e registrar evidencia da revisao (decision log).",
        base_legal="LGPD Art. 20 §3",
        arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet))


@check("E-04", "ethics", "Decisao critica sem rota humana", base_legal="LGPD Art. 20 §3")
def hitl(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, PY):
        _python(ctx, p, findings)
    for p in scan.arquivos(ctx.repo, OUTRAS):
        _heuristica(ctx, p, findings)
    return findings
