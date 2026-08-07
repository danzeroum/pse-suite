"""Alcance TEXTUAL ANCORADO a Rust. **Isto nao e um parser.**

A decisao que originou este modulo esta medida em `docs/cobertura-btv.md`:
53% do primeiro alvo real e Rust, a suite lia zero, e a resposta obvia
seria um parser. A resposta medida foi outra — o Rust do btv e motor de
execucao, e um parser inteiro compraria sobretudo checks NAO-APLICAVEIS.
Sobraram quatro vetores com existencia real em Rust, e os quatro cabem no
degrau que o proprio mapa chamou de `literal`: literal de string com
posicao, e chamada com o span dos argumentos.

O QUE ESTE MODULO FAZ, E O QUE ELE NAO FAZ:

  faz     apaga comentario e resolve literal de string com as regras de
          Rust; acha LIGACOES (`let`/`const`/`static`) com valor literal;
          acha CHAMADAS com o texto bruto do argumento delimitado por
          parenteses balanceados; acha invocacao de MACRO.

  NAO faz arvore, tipos, escopo, resolucao de `use`, generics, traits,
          `impl`, macro expandida, ou qualquer coisa que dependa de saber
          o que um identificador SIGNIFICA. Um check que precise disso nao
          pode ser escrito sobre este modulo — tem de continuar declarando
          Rust fora do seu alcance.

PRECISAO SOBRE RECALL. Sem arvore o casamento e mais fragil que o de
Python, e a regra e errar para MENOS achado. Onde o texto e ambiguo, quem
chama levanta `CheckIndeterminado` com motivo — nunca inventa achado, e
nunca devolve verde por conveniencia.

POR QUE NAO REUSAR `scan.codigo_efetivo`. Rust tem tres construcoes que o
apagador generico erra, e cada uma erra para um lado perigoso:

  * COMENTARIO DE BLOCO ANINHADO. `/* a /* b */ c */` e valido em Rust. O
    apagador generico para no primeiro `*/` e deixa ` c */` como codigo —
    entao um segredo comentado voltaria a valer como fato. Erra para MAIS
    achado.
  * TEMPO DE VIDA. `&'a str` comeca com aspa simples. O apagador generico
    trata `'` como abertura de literal e engole tudo ate a proxima aspa —
    podendo apagar linhas inteiras de codigo real. Erra para MENOS achado,
    em silencio.
  * STRING CRUA. `r#"conteudo com " dentro"#` e comum em SQL e JSON
    embutidos. Sem entende-la, o fim do literal cai no lugar errado e o
    resto do arquivo desalinha.

Nenhuma das tres e opcional: as tres aparecem em codigo Rust rotineiro.
"""
import re

RESERVADAS_DE_LIGACAO = ("let", "const", "static")


def _fim_do_bloco(texto: str, i: int, n: int) -> int:
    """Fim de um `/* ... */` **contando aninhamento**, como Rust exige."""
    profundidade, j = 0, i
    while j < n:
        if texto.startswith("/*", j):
            profundidade += 1
            j += 2
        elif texto.startswith("*/", j):
            profundidade -= 1
            j += 2
            if profundidade == 0:
                return j
        else:
            j += 1
    return n


def _fim_da_string_crua(texto: str, i: int, n: int):
    """`r"..."`, `r#"..."#`, `br##"..."##`. Devolve (inicio_do_conteudo, fim)
    ou None se o que comeca em `i` nao e uma string crua."""
    # `i >= n` acontece de verdade: uma ligacao pode ter valor VAZIO quando o
    # `=` fecha a linha e a expressao segue abaixo, e o btv tem casos assim.
    # Sem esta guarda o check inteiro morria com IndexError e virava
    # indeterminado — bloqueando por defeito da suite, nao do alvo.
    if i >= n:
        return None
    j = i
    if texto.startswith("br", j):
        j += 2
    elif texto[j] == "r":
        j += 1
    else:
        return None
    cercas = 0
    while j < n and texto[j] == "#":
        cercas += 1
        j += 1
    if j >= n or texto[j] != '"':
        return None
    inicio = j + 1
    fecho = '"' + "#" * cercas
    fim = texto.find(fecho, inicio)
    if fim == -1:
        return inicio, n, n
    return inicio, fim, fim + len(fecho)


def _fim_da_string(texto: str, i: int, n: int):
    """`"..."` comum, com escapes. Devolve (inicio_do_conteudo, fim_do_conteudo,
    fim_do_token)."""
    j = i + 1
    while j < n:
        if texto[j] == "\\":
            j += 2
            continue
        if texto[j] == '"':
            return i + 1, j, j + 1
        j += 1
    return i + 1, n, n


# `'a` (tempo de vida) contra `'a'` (literal de caractere). A diferenca e o
# fecho: um literal de caractere fecha na mesma linha, apos um caractere ou
# um escape. Qualquer outra coisa e tempo de vida, e nao abre literal
# nenhum. Errar isto apaga codigo real em silencio.
_CHAR = re.compile(r"'(?:\\(?:x[0-9a-fA-F]{2}|u\{[0-9a-fA-F]{1,6}\}|.)|[^'\\\n])'")


def efetivo(texto: str, sem_literais: bool = False) -> str:
    """Texto com comentarios apagados, mantendo posicao e numero de linha.

    Substitui por espaco em vez de remover para que `arquivo:linha` de um
    achado continue apontando para o lugar certo do arquivo original — a
    mesma disciplina de `scan.codigo_efetivo`.

    `sem_literais=True` apaga tambem o conteudo das strings. Use para
    logica de SUPRESSAO: a mencao de `crypto_shred` dentro de uma string
    nao prova que a rotina existe. NAO use para deteccao de segredo — ali o
    literal E o fato.
    """
    n = len(texto)
    saida = list(texto)
    i = 0

    def apaga(ini, fim):
        for k in range(ini, min(fim, n)):
            if saida[k] != "\n":
                saida[k] = " "

    while i < n:
        if texto.startswith("/*", i):
            fim = _fim_do_bloco(texto, i, n)
            apaga(i, fim)
            i = fim
            continue
        if texto.startswith("//", i):
            fim = texto.find("\n", i)
            fim = n if fim == -1 else fim
            apaga(i, fim)
            i = fim
            continue
        if texto[i] in "rb" and (cru := _fim_da_string_crua(texto, i, n)):
            inicio, fim_conteudo, fim_token = cru
            if sem_literais:
                apaga(inicio, fim_conteudo)
            i = fim_token
            continue
        if texto[i] == '"':
            _, fim_conteudo, fim_token = _fim_da_string(texto, i, n)
            if sem_literais:
                apaga(i + 1, fim_conteudo)
            i = fim_token
            continue
        if texto[i] == "'":
            m = _CHAR.match(texto, i)
            if m:
                i = m.end()
            else:
                i += 1          # tempo de vida: nao abre literal nenhum
            continue
        i += 1

    return "".join(saida)


def _linha_de(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


# --------------------------------------------------------------- ligacoes
# `let NOME: TIPO = VALOR;` / `const NOME: TIPO = VALOR;` / `static ...`.
# A ancora e a palavra reservada MAIS o `=`: sem as duas, `api_key` num
# campo de struct ou num argumento nomeado viraria candidato. Estrutura, e
# nao mencao — e o D-01 aplicado onde nao ha arvore para garanti-lo.
_LIGACAO = re.compile(
    r"\b(?P<kw>let|const|static)\s+(?:mut\s+)?(?P<nome>[A-Za-z_][A-Za-z0-9_]*)"
    r"(?:\s*:\s*[^=;{]+?)?\s*=\s*",
    re.MULTILINE)


class Ligacao:
    """Uma ligacao `let/const/static` e o texto do valor atribuido."""

    __slots__ = ("kw", "nome", "valor_bruto", "linha", "literal", "pos")

    def __init__(self, kw, nome, valor_bruto, linha, literal, pos):
        self.kw = kw
        self.nome = nome
        self.valor_bruto = valor_bruto
        self.linha = linha
        self.literal = literal          # str, se o valor E um literal; senao None
        self.pos = pos

    def __repr__(self):
        return f"Ligacao({self.kw} {self.nome} @{self.linha} = {self.valor_bruto!r})"


def _valor_ate_o_fim(texto: str, i: int) -> str:
    """Do `=` ate o `;` de mesmo nivel, respeitando parenteses e literais.

    Parar no primeiro `;` seria errado: `let x = f(a; b)` nao existe, mas
    `let x = vec![1, 2];` e `let x = Foo { a: 1 };` existem, e um `;` dentro
    de string crua e comum em SQL embutido.
    """
    n = len(texto)
    prof, j = 0, i
    while j < n:
        c = texto[j]
        if c in "([{":
            prof += 1
        elif c in ")]}":
            if prof == 0:
                break
            prof -= 1
        elif c == '"':
            _, _, j = _fim_da_string(texto, j, n)
            continue
        elif c in "rb" and (cru := _fim_da_string_crua(texto, j, n)):
            j = cru[2]
            continue
        elif c == ";" and prof == 0:
            break
        elif c == "\n" and prof == 0 and texto[i:j].strip():
            # Ligacao sem `;` na linha: para no fim da linha em vez de
            # engolir o arquivo inteiro.
            seguinte = texto[j:j + 200].lstrip()
            if seguinte.startswith(("let ", "const ", "static ", "fn ", "}")):
                break
        j += 1
    return texto[i:j]


def ligacoes(texto: str):
    """Todas as ligacoes do arquivo, sobre o codigo EFETIVO.

    Trabalha no texto sem comentario mas COM literais: a deteccao de
    segredo precisa do literal, que ali e o fato e nao a mencao.
    """
    codigo = efetivo(texto)
    for m in _LIGACAO.finditer(codigo):
        valor = _valor_ate_o_fim(codigo, m.end()).strip()
        literal = None
        if valor.startswith('"'):
            ini, fim, _ = _fim_da_string(valor, 0, len(valor))
            literal = valor[ini:fim]
        elif (cru := _fim_da_string_crua(valor, 0, len(valor))):
            literal = valor[cru[0]:cru[1]]
        yield Ligacao(m.group("kw"), m.group("nome"), valor,
                      _linha_de(codigo, m.start()), literal, m.start())


# --------------------------------------------------------------- chamadas
# `caminho::da::fn(` e `receptor.metodo(`. O nome e o texto a esquerda do
# parenteses; os argumentos sao o span ate o fecha-parenteses balanceado.
# Sem arvore nao ha como saber o que cada argumento E — so o que ele DIZ, e
# e por isso que todo check construido aqui confere estrutura (a chamada) e
# nao apenas presenca de palavra.
_CHAMADA = re.compile(
    r"(?P<nome>[A-Za-z_][A-Za-z0-9_]*(?:\s*(?:::|\.)\s*[A-Za-z_][A-Za-z0-9_]*)*)"
    r"\s*\(")


class Chamada:
    __slots__ = ("nome", "args", "linha", "pos")

    def __init__(self, nome, args, linha, pos):
        self.nome = nome
        self.args = args               # texto bruto entre os parenteses
        self.linha = linha
        self.pos = pos

    def __repr__(self):
        return f"Chamada({self.nome} @{self.linha})"


def _span_balanceado(texto: str, i: int) -> tuple:
    """De um `(` ate o `)` correspondente. Devolve (conteudo, fim)."""
    n = len(texto)
    prof, j = 0, i
    while j < n:
        c = texto[j]
        if c == '"':
            _, _, j = _fim_da_string(texto, j, n)
            continue
        if c in "rb" and (cru := _fim_da_string_crua(texto, j, n)):
            j = cru[2]
            continue
        if c == "(":
            prof += 1
        elif c == ")":
            prof -= 1
            if prof == 0:
                return texto[i + 1:j], j + 1
        j += 1
    return texto[i + 1:n], n


# `fn nome(...)` e DEFINICAO, nao chamada — e a lista de parametros nao e
# um span de argumento. A triagem do btv achou isto: `fn append(&mut self,
# kind: &str, payload: Value)` entrava como producao de evento, e o span
# varrido era a assinatura. Num repositorio onde a assinatura fosse
# `fn append(&mut self, cpf: &str)`, o check acusaria a PROPRIA DECLARACAO
# da funcao — um achado que nao tem como ser corrigido, porque nao ha
# defeito nenhum ali. Vale para os quatro checks: `fn connect(...)` viraria
# chamada de persistencia em S-16 pelo mesmo caminho.
_DEFINICAO = re.compile(r"\bfn\s+$")


def chamadas(texto: str):
    """Chamadas do arquivo, sobre o codigo efetivo, com o span de argumento.

    Uma macro (`nome!(...)`) NAO e devolvida aqui: o `!` fica de fora do
    nome capturado e a distincao importa. `tracing::info!` e macro e
    `logger.info()` e chamada; um check que so olhasse um dos dois acharia
    zero em Rust e diria que esta limpo, que e o modo de falhar mais caro
    desta suite. Use `macros()` para o outro lado.

    DEFINICAO tambem nao e devolvida. Ver `_DEFINICAO`.
    """
    codigo = efetivo(texto)
    for m in _CHAMADA.finditer(codigo):
        abre = codigo.index("(", m.end() - 1)
        if abre > 0 and codigo[abre - 1] == "!":
            continue                    # macro: sai por `macros()`
        if _DEFINICAO.search(codigo, max(0, m.start() - 16), m.start()):
            continue                    # definicao: a assinatura nao e argumento
        args, _ = _span_balanceado(codigo, abre)
        yield Chamada(re.sub(r"\s+", "", m.group("nome")), args,
                      _linha_de(codigo, m.start()), m.start())


_MACRO = re.compile(
    r"(?P<nome>[A-Za-z_][A-Za-z0-9_]*(?:\s*::\s*[A-Za-z_][A-Za-z0-9_]*)*)"
    r"\s*!\s*[\(\[\{]")


def macros(texto: str):
    """Invocacoes de macro, com o span dos argumentos.

    Existe por P-01 e P-19: em Rust o logger e `tracing::info!` e nao
    `logger.info()`. Um check que so olhasse chamadas acharia zero.
    """
    codigo = efetivo(texto)
    for m in _MACRO.finditer(codigo):
        abre = m.end() - 1
        fecha = {"(": ")", "[": "]", "{": "}"}[codigo[abre]]
        prof, j, n = 0, abre, len(codigo)
        while j < n:
            c = codigo[j]
            if c == '"':
                _, _, j = _fim_da_string(codigo, j, n)
                continue
            if c == codigo[abre]:
                prof += 1
            elif c == fecha:
                prof -= 1
                if prof == 0:
                    break
            j += 1
        yield Chamada(re.sub(r"\s+", "", m.group("nome")),
                      codigo[abre + 1:j], _linha_de(codigo, m.start()),
                      m.start())


def macro_nao_resolvivel(valor: str, macros_ambiguas) -> str | None:
    """A UNICA fonte de indeterminacao deste alcance, e ela e estreita.

    `env!("API_KEY")` nao le o ambiente em execucao: ele grava o valor no
    binario em tempo de compilacao. Se o valor for um segredo, o binario
    carrega um segredo — e o texto do `.rs` nao diz qual. Chamar de achado
    seria inventar; chamar de limpo seria o verde por conveniencia. E o
    caso exato de "pode ou nao ser o vetor", e a resposta e indeterminado
    com motivo.

    Devolve o nome da macro, ou None.
    """
    m = _MACRO.match(str(valor).strip())
    if not m:
        return None
    nome = re.sub(r"\s+", "", m.group("nome")).split("::")[-1].lower()
    return nome if nome in {x.lower() for x in macros_ambiguas} else None


def contem_token(texto: str, marcas) -> bool:
    """Marca presente como TOKEN, nunca como substring perdida no meio.

    `keyboard` nao pode satisfazer `key`, pelo mesmo motivo que `delimitar`
    nao satisfaz `limitar` em `scan.nome_casa` — e a fragilidade e maior
    aqui, onde nao ha arvore para desempatar.
    """
    baixo = str(texto).lower()
    for marca in marcas:
        m = str(marca).lower()
        if not m:
            continue
        if not re.fullmatch(r"[a-z0-9_:./-]+", m):
            if m in baixo:
                return True
            continue
        if re.search(r"(?<![a-z0-9_])" + re.escape(m) + r"(?![a-z0-9_])", baixo):
            return True
    return False


def tokens_presentes(texto: str, marcas) -> list:
    """Quais marcas aparecem — para o achado poder NOMEAR o que achou."""
    return sorted({str(m).lower() for m in marcas
                   if contem_token(texto, [m])})
