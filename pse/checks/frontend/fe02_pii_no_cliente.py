"""FE-02 — dado pessoal no armazenamento do navegador ou na URL.

O analogo frontend do P-01, e a mesma logica de argumentos: nao se pergunta
"a palavra cpf aparece?", pergunta-se "o que esta chamada RECEBE?".

Dois caminhos, um risco:
  - **storage do cliente**: localStorage/sessionStorage sobrevivem a sessao,
    sao legiveis por qualquer script da pagina (uma dependencia comprometida
    basta) e nao expiram sozinhos;
  - **URL**: query param vaza em historico do navegador, log de servidor,
    header Referer para terceiros e barra de endereco compartilhada por
    screenshot. E o vazamento que a pessoa faz sem saber que fez.

D-08 herdado: valor que passa por funcao de mascaramento nao dispara. Punir
`mask(user.cpf)` seria punir quem acertou.
"""
import re

from pse.checks.privacy.p01_pii_em_logs import RX_MASCARA
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.sanitize import RX_CPF, RX_EMAIL, RX_TELEFONE
from . import _ast

BASE_LEGAL = "LGPD Art. 46 + Art. 6o VII (seguranca e prevencao)"
RX_QUERY = re.compile(r"[?&][A-Za-z0-9_\-]+=")
RX_VALOR_PII = (RX_CPF, RX_EMAIL, RX_TELEFONE)


def _termos_pii(ctx) -> set:
    return {t.lower() for grupo in ctx.data["pii-patterns"].values() for t in grupo}


def _armazenamento(ctx) -> set:
    return {t.lower() for t in ctx.data["frontend-terms"]["armazenamento_cliente"]}


def _mascarado(no, fonte: bytes) -> bool:
    """Algum identificador do no e funcao de mascaramento que EXECUTA?"""
    for _, nome in _ast.chamadas(no, fonte):
        if RX_MASCARA.search(nome):
            return True
    return False


def _carrega_pii(no, fonte: bytes, termos: set) -> str | None:
    if _mascarado(no, fonte):
        return None
    for ident in _ast.identificadores(no, fonte):
        if ident.lower() in termos:
            return ident
    for lit in _ast.literais(no, fonte):
        if any(rx.search(lit) for rx in RX_VALOR_PII):
            return "valor de PII escrito no proprio codigo"
    return None


def _storage(ctx, raiz, fonte, p, termos, stores, findings):
    for no, nome in _ast.chamadas(raiz, fonte):
        alvo = nome.lower()
        if not (alvo.endswith(".setitem") and any(s in alvo for s in stores)):
            continue
        args = no.child_by_field_name("arguments")
        if args is None:
            continue
        achado = _carrega_pii(args, fonte, termos)
        if not achado:
            continue
        findings.append(Finding(
            check_id="FE-02", pack="privacy", severidade=Severidade.CRITICO,
            titulo="Dado pessoal gravado no armazenamento do navegador",
            descricao=f"`{nome}` recebe dado pessoal ({achado}) sem "
                      f"mascaramento. O storage do cliente sobrevive a sessao, e "
                      f"legivel por qualquer script da pagina — uma dependencia "
                      f"comprometida basta — e nao expira sozinho.",
            recomendacao="Nao persistir PII no cliente. Se precisar de estado, "
                         "usar store em memoria que morre com a sessao, ou "
                         "guardar so um identificador opaco.",
            base_legal=BASE_LEGAL,
            arquivo=scan.rel(ctx.repo, p), linha=_ast.linha_de(no),
            snippet=_ast.texto_de(no, fonte)[:200]))


def _url(ctx, raiz, fonte, p, termos, findings):
    """Concatenacao ou template que monta query string com PII."""
    vistos = set()
    for no in _ast.percorrer(raiz):
        if no.type not in ("binary_expression", "template_string"):
            continue
        if _ast.e_comentario(no):
            continue
        bruto = _ast.texto_de(no, fonte)
        if not RX_QUERY.search(bruto):
            continue
        achado = _carrega_pii(no, fonte, termos)
        if not achado:
            continue
        linha = _ast.linha_de(no)
        if linha in vistos:
            continue
        vistos.add(linha)
        findings.append(Finding(
            check_id="FE-02", pack="privacy", severidade=Severidade.CRITICO,
            titulo="Dado pessoal na URL",
            descricao=f"A URL e montada com dado pessoal ({achado}). Query "
                      f"param vaza em historico do navegador, log de servidor, "
                      f"header Referer para terceiros e em qualquer screenshot "
                      f"da barra de endereco — e o vazamento que a pessoa faz "
                      f"sem saber que fez.",
            recomendacao="Usar POST ou path param opaco; para link "
                         "compartilhavel, token temporario emitido pelo backend.",
            base_legal=BASE_LEGAL,
            arquivo=scan.rel(ctx.repo, p), linha=linha,
            snippet=bruto[:200]))


@check("FE-02", "privacy", "PII no cliente ou na URL", base_legal=BASE_LEGAL)
def pii_no_cliente(ctx):
    termos = _termos_pii(ctx)
    stores = _armazenamento(ctx)
    findings = []
    for p in scan.arquivos(ctx.repo, _ast.EXTS):
        texto = scan.ler(p)
        fonte = texto.encode("utf-8")
        raiz = _ast.arvore(p, texto)          # sem AST -> CheckIndeterminado
        _storage(ctx, raiz, fonte, p, termos, stores, findings)
        _url(ctx, raiz, fonte, p, termos, findings)
    return findings
