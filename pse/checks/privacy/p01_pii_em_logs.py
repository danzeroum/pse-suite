"""P-01 — dado pessoal em log sem mascaramento.

ANCORA NO FATO (D-08): a pergunta nao e "a palavra 'cpf' aparece nesta
linha?", e "o que esta chamada de log recebe como argumento?". A regex de
linha unica de 1eb616b errava nos dois sentidos, medido:

  - punia `logger.info("cpf=%s", mascarar(cpf))` com CRITICO — falso-positivo
    no mascaramento CORRETO, o caminho mais curto para o operador aprender a
    ignorar o laudo (plano §9 risco 1);
  - perdia a mesma chamada quebrada em tres linhas — falso-negativo.

Duas formas de violacao, ambas ancoradas no que executa:
  1. valor de PII literal dentro da string (um CPF real no codigo);
  2. variavel de PII passada crua, sem passar por funcao de mascaramento.

Uma string de formato que apenas *cita* `cpf=%s` nao e violacao: o valor
vem dos argumentos, e sao eles que sao julgados.
"""
import ast
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.sanitize import RX_CPF, RX_EMAIL, RX_TELEFONE

OUTRAS = {".js", ".ts", ".go", ".java"}

RX_LOG = re.compile(r"^(logger|logging|log|console)$|^(logger|logging|console)\.|"
                    r"^print$|\.(info|warn|warning|error|debug|critical|exception|log)$",
                    re.I)
RX_MASCARA = re.compile(
    r"mascar|mask|redact|anonimiz|pseudonim|obfusc|scrub|sanitiz|hash|sha\d", re.I)
RX_VALOR_PII = (RX_CPF, RX_EMAIL, RX_TELEFONE)


def _termos(ctx) -> set:
    return {t.lower() for grupo in ctx.data["pii-patterns"].values() for t in grupo}


def _e_log(nome: str) -> bool:
    if not nome:
        return False
    return bool(RX_LOG.search(nome) or RX_LOG.match(nome))


def _mascarado(no: ast.AST) -> bool:
    """O argumento passa por uma funcao de mascaramento que executa?"""
    return isinstance(no, ast.Call) and bool(RX_MASCARA.search(scan.nome_chamado(no)))


def _valor_pii_literal(no: ast.AST) -> bool:
    """Valor de PII escrito no proprio codigo (CPF, e-mail, telefone)."""
    for sub in ast.walk(no):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            if any(rx.search(sub.value) for rx in RX_VALOR_PII):
                return True
    return False


def _nome_pii(no: ast.AST, termos: set) -> str | None:
    """Identificador de variavel que carrega PII, passado sem mascaramento."""
    if _mascarado(no):
        return None
    for sub in ast.walk(no):
        if isinstance(sub, ast.Call) and _mascarado(sub):
            continue
        ident = None
        if isinstance(sub, ast.Name):
            ident = sub.id
        elif isinstance(sub, ast.Attribute):
            ident = sub.attr
        if ident and ident.lower() in termos:
            return ident
    return None


def _argumentos(no: ast.Call):
    """Argumentos julgaveis: posicionais, nomeados e as interpolacoes de f-string."""
    for arg in list(no.args) + [k.value for k in no.keywords]:
        if isinstance(arg, ast.JoinedStr):
            for parte in arg.values:
                yield parte.value if isinstance(parte, ast.FormattedValue) else parte
        else:
            yield arg


def _python(ctx, p, termos, findings):
    arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
    linhas = scan.ler(p).splitlines()
    for no, nome in scan.chamadas(arvore):
        if not _e_log(nome):
            continue
        motivo = None
        for arg in _argumentos(no):
            if _valor_pii_literal(arg):
                motivo = "valor de dado pessoal escrito no proprio codigo"
                break
            ident = _nome_pii(arg, termos)
            if ident:
                motivo = f"variavel '{ident}' vai crua para o log"
                break
        if not motivo:
            continue
        i = no.lineno
        findings.append(Finding(
            check_id="P-01", pack="privacy", severidade=Severidade.CRITICO,
            titulo="Log grava dado pessoal sem mascaramento",
            descricao=f"Chamada de log recebe dado pessoal sem pseudonimizacao "
                      f"({motivo}) — risco de exposicao em vazamento de logs.",
            recomendacao="Mascarar PII antes de logar (ex.: mascarar(cpf)); "
                         "logs sensiveis com chave KMS separada.",
            base_legal="LGPD Art. 46",
            arquivo=scan.rel(ctx.repo, p), linha=i,
            snippet=linhas[i - 1].strip()[:200] if i <= len(linhas) else None))


def _heuristica(ctx, p, termos, findings):
    """Sem AST na v0.x. Severidade rebaixada para ALTO: a heuristica de linha
    nao distingue mascaramento correto de ausencia dele, e falso-positivo em
    CRITICO custa a credibilidade do laudo inteiro."""
    padrao = (rf"(logger\.\w+\(|logging\.\w+\(|\blog\(|console\.\w+\(|\bprint\()"
              rf".*\b({'|'.join(re.escape(t) for t in sorted(termos))})\b")
    for linha, snippet in scan.grep(p, padrao):
        if RX_MASCARA.search(snippet):
            continue
        findings.append(Finding(
            check_id="P-01", pack="privacy", severidade=Severidade.ALTO,
            titulo="Log possivelmente grava dado pessoal sem mascaramento",
            descricao="Identificador pessoal aparece em chamada de log. Sem AST "
                      "para esta linguagem, a suite nao consegue provar se ha "
                      "mascaramento — severidade rebaixada, revisao manual.",
            recomendacao="Mascarar PII antes de logar; confirmar manualmente "
                         "ate a suite ganhar AST para esta linguagem.",
            base_legal="LGPD Art. 46",
            arquivo=scan.rel(ctx.repo, p), linha=linha, snippet=snippet))


@check("P-01", "privacy", "PII em logs sem mascaramento", base_legal="LGPD Art. 46")
def pii_em_logs(ctx):
    termos = _termos(ctx)
    findings = []
    for p in scan.arquivos(ctx.repo, {".py"}):
        _python(ctx, p, termos, findings)
    for p in scan.arquivos(ctx.repo, OUTRAS):
        _heuristica(ctx, p, termos, findings)
    return findings
