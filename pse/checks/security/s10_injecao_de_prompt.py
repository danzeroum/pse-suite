"""S-10 — o que ENTRA no modelo: injecao de prompt, nos tres vetores.

E-11 pergunta se PII vai para o modelo. S-10 pergunta outra coisa: se o
texto que um ESTRANHO controla chega ao modelo sem tratamento. Sao riscos
distintos — o primeiro vaza dado do titular, o segundo entrega o
comportamento do sistema a quem escreveu a entrada.

Tres vetores, um check e uma severidade, porque sao o mesmo ponto de
entrada e a mesma consequencia:

  1. INSTRUCAO CONCATENADA — o classico. Texto de fora emendado ao prompt
     sem delimitacao: o modelo nao distingue a sua instrucao da do atacante.
  2. CARACTERE INVISIVEL — zero-width e controles bidi. Nao aparecem na
     revisao de codigo nem no diff, e mudam o que o modelo le. E a injecao
     que sobrevive a inspecao humana.
  3. TOKEN FLOODING — entrada sem teto de tamanho. Estoura contexto (empurra
     a instrucao do sistema para fora da janela) e estoura custo.

ANCORA NO FATO (D-01): so protege quem EXECUTA. `# sanitize later` num
comentario nao sanitiza nada, e o check enxerga a chamada, nao o texto.

D-08: um pipeline que ja normaliza (NFKC), trunca e delimita nao pode
receber CRITICO — puni-lo ensinaria o time a ignorar o pack no primeiro dia.
Sanitizador generico cobre os tres; protecao especifica cobre o seu vetor.

Toda lista — fontes de entrada, codepoints invisiveis, teto de tamanho e
nomes de protecao — vive em `pse/data/adversarial-patterns.yaml`. Um check
com lista propria e um check que so o autor sabe o que cobre.
"""
import ast
import re

from pse.checks.ethics import _llm
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

BASE_LEGAL = "LGPD Art. 46 (seguranca) + OWASP LLM01"
REGUA = "adversarial-patterns"


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _termos(ctx, chave) -> set:
    return {t.lower() for t in _r(ctx, chave)}


def _protecoes_aplicadas(no, ctx) -> set:
    """Quais protecoes EXECUTAM no caminho deste argumento.

    `sanitizacao` e generica: cobre os tres vetores. As demais cobrem o seu.
    Fatia com limite superior (`texto[:4000]`) conta como limite declarado —
    e truncamento de verdade, so escrito sem funcao.
    """
    grupos = _r(ctx, "protecoes")
    aplicadas = set()
    for sub in ast.walk(no):
        if isinstance(sub, ast.Call):
            nome = scan.nome_chamado(sub)
            for grupo, marcas in grupos.items():
                if scan.nome_casa(nome, marcas):
                    aplicadas.add(grupo)
        elif isinstance(sub, ast.Subscript) and isinstance(sub.slice, ast.Slice):
            if sub.slice.upper is not None:
                aplicadas.add("limite")
    if "sanitizacao" in aplicadas:
        aplicadas |= {"normalizacao", "limite", "delimitacao"}
    return aplicadas


def _vem_do_usuario(no, fontes: set) -> str | None:
    for sub in ast.walk(no):
        ident = None
        if isinstance(sub, ast.Name):
            ident = sub.id
        elif isinstance(sub, ast.Attribute):
            ident = sub.attr
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            continue
        if ident and ident.lower() in fontes:
            return ident
        if isinstance(sub, ast.Call) and scan.nome_chamado(sub) == "input":
            return "input()"
    return None


def _invisiveis_no_literal(no, invisiveis: set) -> list:
    achados = []
    for sub in ast.walk(no):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            for c in invisiveis:
                if c in sub.value:
                    achados.append(f"U+{ord(c):04X}")
    return sorted(set(achados))


def _teto(ctx) -> int:
    return int(_r(ctx, "token_flooding")["caracteres_maximos_aceitos"])


@check("S-10", "security", "Injecao de prompt", base_legal=BASE_LEGAL)
def injecao_de_prompt(ctx):
    fontes = _termos(ctx, "fontes_de_entrada_do_usuario")
    invisiveis = set(_r(ctx, "caracteres_invisiveis"))
    findings = []

    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        texto = scan.ler(p)
        linhas = texto.splitlines()
        modulo_llm = _llm.modulo_fala_com_llm(
            scan.codigo_efetivo(texto, ".py", sem_literais=True), ctx)

        for no, nome in scan.chamadas(arvore):
            if not _llm.e_chamada_llm(nome, ctx, modulo_llm):
                continue
            args = ast.Tuple(elts=list(no.args) + [k.value for k in no.keywords],
                             ctx=ast.Load())
            protegido = _protecoes_aplicadas(no, ctx)
            origem = _vem_do_usuario(args, fontes)
            marcas = _invisiveis_no_literal(args, invisiveis)

            vetores = []
            if origem and "delimitacao" not in protegido:
                vetores.append(
                    f"instrucao concatenada — '{origem}' entra no prompt sem "
                    f"delimitacao, e o modelo nao distingue a sua instrucao da "
                    f"de quem escreveu a entrada")
            if marcas:
                vetores.append(
                    f"caractere invisivel no proprio literal ({', '.join(marcas)}) "
                    f"— nao aparece na revisao de codigo nem no diff, e muda o "
                    f"que o modelo le")
            elif origem and "normalizacao" not in protegido:
                vetores.append(
                    "caractere invisivel — a entrada nao passa por normalizacao "
                    "Unicode, entao zero-width e controles bidi chegam intactos "
                    "ao modelo")
            if origem and "limite" not in protegido:
                vetores.append(
                    f"token flooding — a entrada nao tem teto de tamanho "
                    f"(a suite aceita ate {_teto(ctx)} caracteres); sem ele o "
                    f"atacante empurra a instrucao do sistema para fora da "
                    f"janela de contexto, e ainda escolhe a sua fatura")
            if not vetores:
                continue

            i = no.lineno
            findings.append(Finding(
                check_id="S-10", pack="security", severidade=Severidade.CRITICO,
                titulo=f"Entrada nao tratada chega ao modelo em `{nome}`",
                descricao="Vetores abertos nesta chamada: " +
                          "; ".join(f"({n}) {v}" for n, v in enumerate(vetores, 1)) +
                          ". Sao o mesmo ponto de entrada, entao contam como um "
                          "achado so — o que muda e por quantos caminhos ele "
                          "pode ser explorado.",
                recomendacao="Antes da chamada: normalizar (NFKC), truncar com "
                             "teto explicito e delimitar a entrada num bloco que "
                             "o modelo saiba nao ser instrucao. Uma funcao de "
                             "guarda que faca os tres cobre o check inteiro.",
                base_legal=BASE_LEGAL,
                arquivo=scan.rel(ctx.repo, p), linha=i,
                snippet=linhas[i - 1].strip()[:200] if i <= len(linhas) else None))
    return findings
