"""Utilitarios de varredura estatica (Trabalho B — sem rede).

Regra que rege este modulo (D-01): **ancora no fato, nunca na mencao.**
Um check nao pode concluir nada a partir de uma string que aparece num
comentario ou dentro de um literal — nesses lugares o vigiado escreve o
que quiser, e a trava vira decoracao. Dai `codigo_efetivo()`, que apaga
comentarios e literais antes de qualquer heuristica textual, e `arvore()`,
que da o fato verdadeiro (AST) para os checks de Python.
"""
import ast
import re
from pathlib import Path

from pse.model import CheckIndeterminado

IGNORAR_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
                "dist", "build", ".mypy_cache", ".pytest_cache"}
TAMANHO_MAX = 2_000_000  # 2MB

# Comentario de linha por extensao.
_CMT_LINHA = {
    ".py": ("#",), ".sh": ("#",), ".yaml": ("#",), ".yml": ("#",),
    ".env": ("#",), ".rb": ("#",),
    ".sql": ("--",),
    ".js": ("//",), ".ts": ("//",), ".go": ("//",), ".java": ("//",),
}
# Extensoes com comentario de bloco /* ... */
_CMT_BLOCO = {".js", ".ts", ".go", ".java", ".sql", ".css"}
# HTML comenta com <!-- -->, e so com isso. Sem tratamento proprio, o
# apagador generico usaria `#` — que em HTML nao comenta nada — e um host
# dentro de `<!-- <link href="https://tracker.exemplo"> -->` valeria como
# fato. D-01 exige o contrario.
_CMT_HTML = {".html", ".htm"}
# Extensoes com string de tres aspas.
_TRIPLA = {".py"}


def _casa(p: Path, exts: set) -> bool:
    """`.env` nao tem sufixo (D-03).

    `Path('.env').suffix == ''`, entao filtrar so por sufixo tornava
    invisivel justamente o arquivo onde segredo mais aparece. Casa por
    sufixo, por nome exato, e por variantes `.env.local` / `.env.producao`.
    """
    if p.suffix in exts:
        return True
    if p.name in exts:
        return True
    return any(e.startswith(".") and p.name.startswith(e + ".") for e in exts)


def arquivos(repo: Path, exts: set):
    for p in sorted(Path(repo).rglob("*")):
        if any(part in IGNORAR_DIRS for part in p.parts):
            continue
        if p.is_file() and _casa(p, exts):
            try:
                if p.stat().st_size < TAMANHO_MAX:
                    yield p
            except OSError:
                continue


def ler(path: Path) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def codigo_efetivo(texto: str, ext: str, sem_literais: bool = False) -> str:
    """Devolve o texto com os comentarios apagados.

    Substitui por espacos em vez de remover, preservando comprimento e
    numeracao de linhas — assim o `arquivo:linha` de um achado continua
    apontando para o lugar certo do arquivo original.

    `sem_literais=True` apaga tambem os literais de string. Use para
    logica de SUPRESSAO (a mencao de um controle dentro de uma string nao
    prova que o controle existe). NAO use para DETECCAO de segredo ou PII:
    ali o literal e justamente o fato — `api_key = "sk-live-..."` e uma
    credencial hardcoded, nao uma mencao a uma.
    """
    if ext in _CMT_HTML:
        return _apagar_comentario_html(texto)
    marcas = _CMT_LINHA.get(ext, ("#",))
    bloco = ext in _CMT_BLOCO
    tripla = ext in _TRIPLA

    saida = list(texto)
    i, n = 0, len(texto)

    def apaga(ini, fim):
        for k in range(ini, min(fim, n)):
            if saida[k] != "\n":
                saida[k] = " "

    while i < n:
        c = texto[i]

        if bloco and texto.startswith("/*", i):
            fim = texto.find("*/", i + 2)
            fim = n if fim == -1 else fim + 2
            apaga(i, fim)
            i = fim
            continue

        marca = next((m for m in marcas if texto.startswith(m, i)), None)
        if marca:
            fim = texto.find("\n", i)
            fim = n if fim == -1 else fim
            apaga(i, fim)
            i = fim
            continue

        if c in "\"'":
            if not sem_literais:
                # Docstring de tres aspas ainda e comentario na pratica:
                # nao executa nada e e onde texto livre mora.
                if tripla and texto.startswith(c * 3, i):
                    fim = texto.find(c * 3, i + 3)
                    fim = n if fim == -1 else fim + 3
                    apaga(i, fim)
                    i = fim
                    continue
                j = i + 1
                while j < n and texto[j] != c and texto[j] != "\n":
                    j += 2 if texto[j] == "\\" else 1
                i = min(j + 1, n)
                continue
            if tripla and texto.startswith(c * 3, i):
                fim = texto.find(c * 3, i + 3)
                fim = n if fim == -1 else fim + 3
            else:
                j = i + 1
                while j < n and texto[j] != c and texto[j] != "\n":
                    j += 2 if texto[j] == "\\" else 1
                fim = min(j + 1, n)
            apaga(i, fim)
            i = fim
            continue

        i += 1

    return "".join(saida)


def _apagar_comentario_html(texto: str) -> str:
    """`<!-- ... -->` apagado, preservando posicao e numero de linha.

    Literais NAO sao apagados, e isso e deliberado: em HTML o valor do
    atributo E o fato. `<link href="https://fonts.googleapis.com/...">` nao e
    a mencao de um terceiro — e o egresso acontecendo.
    """
    saida = list(texto)
    i, n = 0, len(texto)
    while i < n:
        if texto.startswith("<!--", i):
            fim = texto.find("-->", i + 4)
            fim = n if fim == -1 else fim + 3
            for k in range(i, min(fim, n)):
                if saida[k] != "\n":
                    saida[k] = " "
            i = fim
            continue
        i += 1
    return "".join(saida)


def arvore(path: Path) -> ast.Module:
    """AST de um arquivo Python — o fato, nao a mencao.

    Arquivo que nao parseia e indeterminacao honesta, nunca 'conforme':
    o check nao conseguiu olhar, e isso bloqueia (exit 20).
    """
    try:
        return ast.parse(ler(path))
    except SyntaxError as e:
        raise CheckIndeterminado(
            f"{path.name} nao pode ser analisado (SyntaxError linha {e.lineno}) "
            f"— sem AST nao ha como decidir pelo fato") from e


def nome_chamado(no: ast.AST) -> str:
    """Nome do alvo de uma chamada: `a.b.c(x)` -> 'a.b.c'."""
    alvo = no.func if isinstance(no, ast.Call) else no
    partes = []
    while isinstance(alvo, ast.Attribute):
        partes.append(alvo.attr)
        alvo = alvo.value
    if isinstance(alvo, ast.Name):
        partes.append(alvo.id)
    return ".".join(reversed(partes))


def nome_casa(nome: str, marcas) -> bool:
    """A marca casa com um TOKEN do nome, nao com substring perdida no meio.

    `delimitar` contem `limitar`: com casamento por substring, delimitar uma
    entrada passava a valer como limitar o tamanho dela, e um vetor de
    injecao inteiro sumia em silencio. Tokenizar por `.` e `_` e exigir
    prefixo resolve — `delimitar`.startswith(`limitar`) e falso, e
    `delimitar`.startswith(`delimit`) e verdadeiro.
    """
    tokens = re.split(r"[._]+", str(nome).lower())
    return any(t.startswith(m.lower()) for t in tokens if t for m in marcas)


def _tokens(nome: str) -> list:
    return [t for t in re.split(r"[._]+", str(nome).lower()) if t]


def nome_casa_tokens(nome: str, marcas) -> bool:
    """A marca e um CONJUNTO de tokens, e todos tem de aparecer no nome.

    `nome_casa` resolve marca de um token so (`limitar`). Nao resolve marca
    composta: `validar_filtro` vira os tokens ['validar', 'filtro'], e
    nenhum token de `validar_filtros` comeca com a string inteira.

    Aqui cada token da marca precisa ser prefixo de algum token do nome —
    o que faz `validar_filtro` casar com `validar_filtros` (plural) e com
    `validar_filtros_permitidos`, e NAO casar com `validar_email`. Sem a
    exigencia de todos os tokens, `filtro` sozinho casaria com qualquer
    funcao de filtragem e a guarda viraria um passe livre.
    """
    tokens = _tokens(nome)
    if not tokens:
        return False
    for marca in marcas:
        exigidos = _tokens(marca)
        if exigidos and all(any(t.startswith(e) for t in tokens)
                            for e in exigidos):
            return True
    return False


def chamadas(no: ast.AST):
    """Todas as chamadas dentro de um no, com nome resolvido."""
    for sub in ast.walk(no):
        if isinstance(sub, ast.Call):
            yield sub, nome_chamado(sub)


def grep(path: Path, pattern: str, flags=re.IGNORECASE, efetivo: bool = True):
    """Linhas que casam com o regex: [(numero_da_linha, snippet<=200c)].

    Por padrao ignora comentarios e literais (`efetivo=True`) — o que a
    heuristica textual ve e so o codigo que executa.
    """
    rx = re.compile(pattern, flags)
    texto = ler(path)
    alvo = codigo_efetivo(texto, Path(path).suffix) if efetivo else texto
    originais = texto.splitlines()
    out = []
    for i, linha in enumerate(alvo.splitlines(), 1):
        if rx.search(linha):
            bruto = originais[i - 1] if i <= len(originais) else linha
            out.append((i, bruto.strip()[:200]))
    return out


def rel(repo: Path, p: Path) -> str:
    try:
        return str(Path(p).relative_to(repo))
    except ValueError:
        return str(p)
