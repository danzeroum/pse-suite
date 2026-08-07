"""S-13 — o erro como canal de saida: pilha, caminho e versao.

A borda e onde a excecao vira resposta HTTP, e a resposta de erro e o unico
lugar do sistema em que o comportamento anormal e desenhado com pressa. S-03
ja pergunta se ha PII no payload de erro. Este pergunta pela ESTRUTURA:

  - PILHA — `traceback.format_exc()` no corpo entrega nomes de modulo,
    funcoes internas e a ordem exata em que elas se chamam.
  - CAMINHO — `__file__`, `os.getcwd()` entregam a topologia do disco e,
    de quebra, o usuario que roda o processo.
  - VERSAO — `sys.version`, `framework.__version__` entregam a lista de
    CVEs aplicaveis, prontinha, sem o atacante precisar tentar nada.
  - DEBUG LIGADO — `app.run(debug=True)` e o console interativo do
    Werkzeug: traceback navegavel, e em algumas versoes um shell, para
    qualquer requisicao que estoure. E o mesmo defeito com outra roupa.

A DISTINCAO QUE O CHECK PRECISA FAZER: `log.exception(...)` manda a pilha
para o lado de DENTRO, e isso e observabilidade, nao vazamento. Punir o log
empurraria o time a apagar o traceback em vez de sanear a resposta — o
oposto do que se quer. Por isso o achado exige que o internals chegue a um
RETORNO ou a um construtor de resposta, nunca a uma chamada de log.

D-01: o achado nasce da AST. `# devolve traceback so em dev` num comentario
nao devolve nada, e uma string com a palavra "traceback" tampouco.
"""
import ast

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

BASE = "LGPD Art. 46 (seguranca) + Art. 6o VIII (prevencao)"
REGUA = "api-contract"

RECOMENDACAO = (
    "Devolver um erro estavel — codigo, mensagem generica e um id de "
    "correlacao — e mandar a pilha para o log estruturado, que fica do lado "
    "de dentro. O id e o que permite ao suporte achar o evento sem publicar "
    "a topologia do sistema.")


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _e_handler_de_erro(no, decoradores) -> bool:
    for dec in no.decorator_list:
        alvo = dec.func if isinstance(dec, ast.Call) else dec
        if scan.nome_chamado(alvo).split(".")[-1].lower() in decoradores:
            return True
    return False


def _escopos_de_erro(arvore, decoradores):
    """Onde uma excecao vira resposta: handler decorado e bloco `except`."""
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and \
                _e_handler_de_erro(no, decoradores):
            yield no
        elif isinstance(no, ast.ExceptHandler):
            yield no


def _saidas(escopo, construtores):
    """Nos que efetivamente SAEM: `return ...` e construtor de resposta.

    E o que separa vazamento de observabilidade — `log.exception(exc)` nao
    passa por aqui, e nao deve mesmo.
    """
    for sub in ast.walk(escopo):
        if isinstance(sub, ast.Return) and sub.value is not None:
            yield sub.value
        elif isinstance(sub, ast.Call) and scan.nome_chamado(
                sub).split(".")[-1] in construtores:
            yield sub


def _categoria(nome: str, ponteado: str, grupos: dict):
    """Primeira categoria que reconhece o nome — curto ou pontuado inteiro.

    `sys.version` so casa pelo nome inteiro: `version` sozinho casaria com
    qualquer campo de negocio chamado assim, e um check que reprova
    `{"version": "2.1"}` na resposta de erro perde a confianca do time no
    primeiro dia.
    """
    for cat, termos in grupos.items():
        if nome in termos or ponteado in termos:
            return cat
    return None


def _vazamentos(no, chamadas: dict, atributos: dict) -> dict:
    """{categoria: [evidencia]} do que este no entrega ao cliente."""
    achados = {}
    for sub in ast.walk(no):
        if isinstance(sub, ast.Call):
            ultimo = scan.nome_chamado(sub).split(".")[-1]
            cat = _categoria(ultimo, ultimo, chamadas)
            if cat:
                achados.setdefault(cat, []).append(f"{ultimo}()")
        elif isinstance(sub, ast.Attribute):
            cat = _categoria(sub.attr, scan.nome_chamado(sub), atributos)
            if cat:
                achados.setdefault(cat, []).append(scan.nome_chamado(sub))
        elif isinstance(sub, ast.Name):
            cat = _categoria(sub.id, sub.id, atributos)
            if cat:
                achados.setdefault(cat, []).append(sub.id)
    return achados


EXPLICACAO = {
    "traceback": "a pilha entrega nomes de modulo, funcoes internas e a ordem "
                 "exata em que se chamam",
    "caminho": "o caminho no disco entrega a topologia do sistema de arquivos "
               "e o usuario que roda o processo",
    "versao": "a versao entrega a lista de CVEs aplicaveis pronta, sem o "
              "atacante precisar tentar nada",
}


@check("S-13", "security", "Erro expoe internals ao cliente", base_legal=BASE)
def erro_expoe_internals(ctx):
    grupos = {cat: set(termos) for cat, termos in _r(ctx, "internals").items()}
    atributos = {cat: set(termos)
                 for cat, termos in _r(ctx, "atributos_internos").items()}
    construtores = set(_r(ctx, "construtores_de_resposta"))
    decoradores = {d.lower() for d in _r(ctx, "decoradores_de_erro")}
    ligadores = {d.lower() for d in _r(ctx, "ligadores_de_debug")}
    findings, vistos = [], set()

    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        rel = scan.rel(ctx.repo, p)
        linhas = scan.ler(p).splitlines()

        for escopo in _escopos_de_erro(arvore, decoradores):
            for saida in _saidas(escopo, construtores):
                vazou = _vazamentos(saida, grupos, atributos)
                if not vazou:
                    continue
                linha = getattr(saida, "lineno", getattr(escopo, "lineno", 1))
                chave = (rel, linha)
                if chave in vistos:
                    continue
                vistos.add(chave)
                cats = sorted(vazou)
                findings.append(Finding(
                    check_id="S-13", pack="security", severidade=Severidade.ALTO,
                    titulo=f"Resposta de erro expoe {', '.join(cats)} ao cliente",
                    descricao=(
                        "O payload devolvido carrega: " +
                        "; ".join(f"{cat} ({', '.join(sorted(set(vazou[cat])))}) "
                                  f"— {EXPLICACAO.get(cat, '')}"
                                  for cat in cats) +
                        ". S-03 cuida da PII no erro; aqui o que vaza e a "
                        "estrutura, que e o mapa que o atacante usaria para "
                        "escolher o proximo passo."),
                    recomendacao=RECOMENDACAO,
                    base_legal=BASE, arquivo=rel, linha=linha,
                    snippet=(linhas[linha - 1].strip()[:200]
                             if linha <= len(linhas) else None)))

        # --------------------------------------------- debug ligado no servidor
        for no, nome in scan.chamadas(arvore):
            if nome.split(".")[-1].lower() not in ligadores:
                continue
            for kw in no.keywords:
                if kw.arg != "debug":
                    continue
                if not (isinstance(kw.value, ast.Constant)
                        and kw.value.value is True):
                    continue
                linha = no.lineno
                chave = (rel, linha)
                if chave in vistos:
                    continue
                vistos.add(chave)
                findings.append(Finding(
                    check_id="S-13", pack="security", severidade=Severidade.ALTO,
                    titulo=f"Servidor sobe com debug ligado em `{nome}`",
                    descricao=(
                        "Com `debug=True` o proprio framework devolve o "
                        "traceback ao cliente em qualquer excecao nao tratada "
                        "— e o console do Werkzeug ainda oferece avaliacao "
                        "interativa de expressoes no frame que estourou. Nao "
                        "adianta sanear handler nenhum se o modo de "
                        "depuracao contorna todos eles."),
                    recomendacao=(
                        "Ligar depuracao por variavel de ambiente que so exista "
                        "na maquina do desenvolvedor, nunca por literal no "
                        "codigo. " + RECOMENDACAO),
                    base_legal=BASE, arquivo=rel, linha=linha,
                    snippet=(linhas[linha - 1].strip()[:200]
                             if linha <= len(linhas) else None)))
    return findings
