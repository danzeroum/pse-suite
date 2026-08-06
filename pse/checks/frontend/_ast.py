"""AST real de JS/JSX/TS/TSX — a alternativa ao grep que o material propõe.

O material de fundação do frontend sugere `grep -rn "consent\\|token\\|..."`.
Grep serve para achar ONDE olhar e nunca como check: e literalmente o D-01, a
mencao passando por fato. Um `// consent default on` casaria; um
`<input checked />` sem handler, quebrado em tres linhas, nao.

tree-sitter com as gramaticas javascript e tsx. Quando um arquivo nao parseia,
o modulo NAO cai para heuristica de texto: levanta indeterminacao. Sem AST nao
ha decisao pelo fato, e nao decidir bloqueia — jamais vira verde.
"""
from pse.model import CheckIndeterminado

EXTS = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}
_TSX = {".ts", ".tsx"}
_CACHE = {}


class ParserIndisponivel(CheckIndeterminado):
    """Ambiente sem gramatica instalada. Indeterminado, nunca verde."""


def _linguagem(ext: str):
    if ext in _CACHE:
        return _CACHE[ext]
    try:
        from tree_sitter import Language, Parser
        if ext in _TSX:
            import tree_sitter_typescript as ts
            lang = Language(ts.language_tsx())
        else:
            import tree_sitter_javascript as tsj
            lang = Language(tsj.language())
    except Exception as e:  # noqa: BLE001
        raise ParserIndisponivel(
            f"gramatica de {ext} indisponivel neste ambiente "
            f"({type(e).__name__}: {e}). Os checks de frontend exigem AST real; "
            f"sem ela a suite nao decide pelo fato e o resultado e "
            f"indeterminado, nunca conforme") from e
    _CACHE[ext] = Parser(lang)
    return _CACHE[ext]


def arvore(caminho, texto: str):
    """Raiz da AST. Arquivo com erro de sintaxe -> indeterminacao com motivo."""
    parser = _linguagem(caminho.suffix)
    raiz = parser.parse(texto.encode("utf-8")).root_node
    if raiz.has_error:
        linha = _primeiro_erro(raiz)
        raise CheckIndeterminado(
            f"{caminho.name} nao pode ser analisado (erro de sintaxe por volta "
            f"da linha {linha}) — sem AST nao ha como decidir pelo fato")
    return raiz


def _primeiro_erro(no) -> int:
    for sub in percorrer(no):
        if sub.type == "ERROR" or sub.is_missing:
            return sub.start_point[0] + 1
    return no.start_point[0] + 1


def percorrer(no):
    """Todos os nos, em profundidade."""
    pilha = [no]
    while pilha:
        atual = pilha.pop()
        yield atual
        pilha.extend(reversed(atual.children))


def texto_de(no, fonte: bytes) -> str:
    return fonte[no.start_byte:no.end_byte].decode("utf-8", "ignore")


def linha_de(no) -> int:
    return no.start_point[0] + 1


def e_comentario(no) -> bool:
    return no.type == "comment"


def identificadores(no, fonte: bytes):
    """Identificadores e nomes de propriedade que EXECUTAM.

    Comentarios ficam de fora por construcao: o que esta aqui e o que roda.
    """
    for sub in percorrer(no):
        if e_comentario(sub):
            continue
        if sub.type in ("identifier", "property_identifier",
                        "shorthand_property_identifier", "type_identifier"):
            yield texto_de(sub, fonte)


def literais(no, fonte: bytes):
    """Conteudo de literais de string/template que executam (nao comentarios)."""
    for sub in percorrer(no):
        if e_comentario(sub):
            continue
        if sub.type in ("string_fragment", "string"):
            yield texto_de(sub, fonte).strip("\"'`")


def nome_chamado(no, fonte: bytes) -> str:
    """`a.b.c(x)` -> 'a.b.c'."""
    if no.type != "call_expression":
        return ""
    fn = no.child_by_field_name("function")
    return texto_de(fn, fonte) if fn is not None else ""


def chamadas(raiz, fonte: bytes):
    for sub in percorrer(raiz):
        if sub.type == "call_expression" and not e_comentario(sub):
            yield sub, nome_chamado(sub, fonte)


# ------------------------------------------------------------------ JSX
def elementos_jsx(raiz):
    for sub in percorrer(raiz):
        if sub.type in ("jsx_opening_element", "jsx_self_closing_element"):
            yield sub


def tag_de(no, fonte: bytes) -> str:
    alvo = no.child_by_field_name("name")
    return texto_de(alvo, fonte) if alvo is not None else ""


def atributos(no, fonte: bytes) -> dict:
    """{nome: valor_bruto_ou_None}. `checked` sem valor -> None (literal true
    em JSX, que e exatamente o caso que FE-01 procura)."""
    saida = {}
    for filho in no.children:
        if filho.type != "jsx_attribute":
            continue
        nome_no = filho.child(0)
        if nome_no is None:
            continue
        nome = texto_de(nome_no, fonte)
        valor = None
        if filho.child_count > 1:
            valor = texto_de(filho.child(filho.child_count - 1), fonte)
        saida[nome] = valor
    return saida


def elemento_pai(no):
    """O `jsx_element` que envolve — onde mora o texto do rotulo."""
    atual = no.parent
    while atual is not None:
        if atual.type == "jsx_element":
            return atual
        atual = atual.parent
    return None


def texto_visivel(no, fonte: bytes) -> str:
    """Texto que o usuario le (jsx_text), sem comentarios.

    Nao e 'mencao': e o rotulo que o titular enxerga ao lado do toggle, e
    portanto parte do fato que se examina.
    """
    if no is None:
        return ""
    partes = [texto_de(s, fonte) for s in percorrer(no)
              if s.type == "jsx_text" and not e_comentario(s)]
    return " ".join(p.strip() for p in partes if p.strip())
