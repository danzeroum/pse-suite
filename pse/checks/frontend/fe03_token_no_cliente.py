"""FE-03 — token de sessao vivendo no cliente.

Token em `localStorage` e legivel por qualquer script da pagina: um XSS, ou
uma dependencia que um dia adicionou telemetria (o mesmo buraco do E-13),
rouba a sessao inteira sem tocar na senha. Cookie escrito por
`document.cookie` tem o mesmo problema por construcao — o que JavaScript
escreve, JavaScript le, entao `HttpOnly` e inalcancavel dali.

O lugar do token e um cookie `HttpOnly; Secure; SameSite`, emitido pelo
servidor. E por isso que a fixture conforme nao tem "a forma certa de
guardar token no cliente": ela simplesmente NAO guarda — usa
`credentials: "include"` e deixa o cookie fazer o trabalho.
"""
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade
from . import _ast

BASE_LEGAL = "LGPD Art. 46 (seguranca) + OWASP A07"


def _segredos(ctx) -> set:
    return {t.lower() for t in ctx.data["frontend-terms"]["segredos_cliente"]}


def _armazenamento(ctx) -> set:
    return {t.lower() for t in ctx.data["frontend-terms"]["armazenamento_cliente"]}


def _cheira_a_segredo(no, fonte: bytes, segredos: set) -> str | None:
    for ident in _ast.identificadores(no, fonte):
        if ident.lower() in segredos:
            return ident
    for lit in _ast.literais(no, fonte):
        alvo = lit.lower()
        if any(s == alvo or f"{s}=" in alvo for s in segredos):
            return lit[:40]
    return None


@check("FE-03", "security", "Token sensivel no cliente", base_legal=BASE_LEGAL)
def token_no_cliente(ctx):
    segredos = _segredos(ctx)
    stores = _armazenamento(ctx)
    findings = []

    for p in scan.arquivos(ctx.repo, _ast.EXTS):
        texto = scan.ler(p)
        fonte = texto.encode("utf-8")
        raiz = _ast.arvore(p, texto)          # sem AST -> CheckIndeterminado
        arq = scan.rel(ctx.repo, p)

        for no, nome in _ast.chamadas(raiz, fonte):
            alvo = nome.lower()
            if not (alvo.endswith(".setitem") and any(s in alvo for s in stores)):
                continue
            args = no.child_by_field_name("arguments")
            achado = _cheira_a_segredo(args, fonte, segredos) if args else None
            if not achado:
                continue
            findings.append(Finding(
                check_id="FE-03", pack="security", severidade=Severidade.ALTO,
                titulo="Token de sessao persistido no armazenamento do cliente",
                descricao=f"`{nome}` guarda '{achado}' no navegador. Qualquer "
                          f"script da pagina le esse valor: um XSS, ou uma "
                          f"dependencia que um dia adicionou telemetria, leva a "
                          f"sessao inteira sem tocar na senha.",
                recomendacao="Mover a sessao para cookie HttpOnly + Secure + "
                             "SameSite, emitido pelo servidor; no cliente, usar "
                             "credentials: 'include' e nao guardar nada.",
                base_legal=BASE_LEGAL,
                arquivo=arq, linha=_ast.linha_de(no),
                snippet=_ast.texto_de(no, fonte)[:200]))

        # `document.cookie = ...`: o que JS escreve, JS le. HttpOnly e
        # inalcancavel daqui, entao a forma ja e o defeito.
        for no in _ast.percorrer(raiz):
            if no.type != "assignment_expression" or _ast.e_comentario(no):
                continue
            esq = no.child_by_field_name("left")
            if esq is None or "document.cookie" not in _ast.texto_de(esq, fonte):
                continue
            dir_ = no.child_by_field_name("right")
            achado = _cheira_a_segredo(dir_, fonte, segredos) if dir_ else None
            if not achado:
                continue
            findings.append(Finding(
                check_id="FE-03", pack="security", severidade=Severidade.ALTO,
                titulo="Token escrito em cookie pelo JavaScript",
                descricao=f"`document.cookie` recebe '{achado}'. Cookie escrito "
                          f"pelo cliente nao pode ser HttpOnly — o que "
                          f"JavaScript escreve, JavaScript le — entao a propria "
                          f"forma ja anula a protecao que o cookie deveria dar.",
                recomendacao="Emitir o cookie no servidor com HttpOnly, Secure "
                             "e SameSite; o cliente nunca toca no valor.",
                base_legal=BASE_LEGAL,
                arquivo=arq, linha=_ast.linha_de(no),
                snippet=_ast.texto_de(no, fonte)[:200]))
    return findings
