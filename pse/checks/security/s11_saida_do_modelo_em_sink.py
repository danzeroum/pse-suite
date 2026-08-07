"""S-11 — o que SAI do modelo chegando a sink perigoso sem validacao.

S-10 cuida da entrada; este cuida do outro lado, e o outro lado e pior.
Texto gerado por um modelo **nao e codigo confiavel**: e a saida de uma
funcao cujo comportamento depende de um prompt que alguem de fora talvez
tenha influenciado. Passar isso direto para `exec`, para o banco, para o
shell ou para uma requisicao e dar ao atacante o interpretador — a injecao
de prompt vira execucao remota sem nenhum passo intermediario.

O check faz um rastreio de fluxo curto e honesto dentro de cada funcao:
  - aninhamento direto: `exec(llm.complete(p))`
  - uma variavel: `r = llm.complete(p)` ... `db.query(r)`

Nao tenta ir alem disso. Fluxo que atravessa modulos e indecidivel
estaticamente sem analise interprocedural, e prometer o que nao se entrega
seria pior que a lacuna: o consumidor confiaria numa cobertura que nao
existe. O que este check afirma, ele prova.

D-08: saida validada, parseada contra schema ou escapada antes do sink nao
dispara. Um pipeline que ja trata a resposta do modelo como dado nao pode
receber CRITICO.
"""
import ast

from pse.checks.ethics import _llm
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

BASE_LEGAL = "LGPD Art. 46 (seguranca) + OWASP LLM02"
REGUA = "adversarial-patterns"


def _sinks(ctx) -> dict:
    return {cat: {t.lower() for t in termos}
            for cat, termos in ctx.data[REGUA]["sinks_perigosos"].items()}


def _validacoes(ctx) -> set:
    return {t.lower() for t in ctx.data[REGUA]["validacoes_de_saida"]}


def _categoria_do_sink(nome: str, sinks: dict) -> str | None:
    ultimo = nome.split(".")[-1].lower()
    for cat, termos in sinks.items():
        if ultimo in termos:
            return cat
    return None


def _validado(no, validacoes: set) -> bool:
    for sub in ast.walk(no):
        if isinstance(sub, ast.Call):
            if scan.nome_casa(scan.nome_chamado(sub), validacoes):
                return True
    return False


def _saidas_do_modelo(escopo, ctx, modulo_llm: bool) -> set:
    """Variaveis que recebem, direta ou nomeadamente, a resposta do modelo."""
    nomes = set()
    for no in ast.walk(escopo):
        if not isinstance(no, (ast.Assign, ast.AnnAssign)):
            continue
        valor = no.value
        if valor is None:
            continue
        veio_do_llm = any(
            _llm.e_chamada_llm(scan.nome_chamado(sub), ctx, modulo_llm)
            for sub in ast.walk(valor) if isinstance(sub, ast.Call))
        if not veio_do_llm:
            continue
        alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
        for alvo in alvos:
            for sub in ast.walk(alvo):
                if isinstance(sub, ast.Name):
                    nomes.add(sub.id)
    return nomes


def _usa(no, nomes: set) -> str | None:
    for sub in ast.walk(no):
        if isinstance(sub, ast.Name) and sub.id in nomes:
            return sub.id
    return None


@check("S-11", "security", "Saida do modelo em sink perigoso", base_legal=BASE_LEGAL)
def saida_em_sink(ctx):
    sinks, validacoes = _sinks(ctx), _validacoes(ctx)
    findings = []

    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        texto = scan.ler(p)
        linhas = texto.splitlines()
        modulo_llm = _llm.modulo_fala_com_llm(
            scan.codigo_efetivo(texto, ".py", sem_literais=True), ctx)
        if not modulo_llm and not any(
                _llm.e_chamada_llm(n, ctx, False) for _, n in scan.chamadas(arvore)):
            continue

        escopos = [n for n in ast.walk(arvore)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef,
                                     ast.Module))] or [arvore]
        vistos = set()
        for escopo in escopos:
            do_modelo = _saidas_do_modelo(escopo, ctx, modulo_llm)
            for no, nome in scan.chamadas(escopo):
                cat = _categoria_do_sink(nome, sinks)
                if cat is None:
                    continue
                args = ast.Tuple(elts=list(no.args) + [k.value for k in no.keywords],
                                 ctx=ast.Load())
                direto = any(
                    _llm.e_chamada_llm(scan.nome_chamado(sub), ctx, modulo_llm)
                    for sub in ast.walk(args) if isinstance(sub, ast.Call))
                via_variavel = _usa(args, do_modelo)
                if not direto and not via_variavel:
                    continue
                if _validado(args, validacoes):
                    continue             # a saida e tratada como dado — conforme
                chave = (scan.rel(ctx.repo, p), no.lineno)
                if chave in vistos:
                    continue
                vistos.add(chave)
                origem = ("aninhada na propria chamada" if direto
                          else f"via a variavel '{via_variavel}'")
                i = no.lineno
                findings.append(Finding(
                    check_id="S-11", pack="security", severidade=Severidade.CRITICO,
                    titulo=f"Resposta do modelo chega a `{nome}` sem validacao",
                    descricao=f"A saida do modelo ({origem}) e entregue a um sink "
                              f"de {cat} sem passar por validacao. Texto gerado "
                              f"por modelo nao e codigo confiavel: e a saida de "
                              f"uma funcao cujo comportamento depende de um "
                              f"prompt que alguem de fora talvez controle. Aqui "
                              f"a injecao de prompt deixa de ser problema de "
                              f"conteudo e vira execucao.",
                    recomendacao="Tratar a resposta como dado nao confiavel: "
                                 "parsear contra schema, validar contra "
                                 "allowlist e escapar antes do sink. Para SQL, "
                                 "consulta parametrizada; para acao, um "
                                 "vocabulario fechado de operacoes permitidas.",
                    base_legal=BASE_LEGAL,
                    arquivo=scan.rel(ctx.repo, p), linha=i,
                    snippet=linhas[i - 1].strip()[:200] if i <= len(linhas) else None))
    return findings
