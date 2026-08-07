"""E-00 — guarda de escopo do pacote de Etica (o EBD-000 do plano v1).

Os checks de etica rodavam sem verificar antes se o alvo decide sobre
pessoas. Num alvo sem nenhuma IA ou decisao automatizada isso produz
findings de etica que nao se aplicam — ruido que ensina o consumidor a
ignorar justamente o pacote mais valioso.

A condicao e COMPUTADA, nunca presumida, e confrontada com a declaracao:

  codigo diz "nao ha"  + consumidor declara `none`     -> pack N/A declarado
  codigo diz "ha"      + consumidor declara `none`     -> ACHADO (divergencia)
  consumidor declara `assistive`/`automated`           -> pack em escopo
  nada declarado + nenhum indicio                      -> pack N/A computado

N/A e conforme sao estados distintos no laudo: um pack fora de escopo sai
com motivo, nunca em verde silencioso.
"""
import ast
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck
from . import _llm

RX_ML = re.compile(
    r"^(?:import|from)\s+(sklearn|torch|tensorflow|xgboost|lightgbm|keras"
    r"|transformers|catboost|statsmodels)\b", re.M)
RX_DECISAO = re.compile(
    r"score|pontuacao|predict|classific|triagem|decidir|decisao|recomend"
    r"|negar_|aprovar_|bloquear_|avaliar_risco", re.I)
RX_INFERENCIA = re.compile(r"^(predict|predict_proba|fit|transform|infer|score)$", re.I)

DECLARACOES = {"none", "assistive", "automated"}


def _indicios(ctx) -> list:
    """Fatos que sugerem decisao automatizada sobre pessoas."""
    achados = []
    for p in scan.arquivos(ctx.repo, {".py"}):
        arq = scan.rel(ctx.repo, p)
        texto = scan.ler(p)
        # Chamar um LLM sobre pessoas e processamento automatizado: poe o pack
        # de etica em escopo tanto quanto um modelo treinado em casa (E-11).
        efetivo = scan.codigo_efetivo(texto, ".py", sem_literais=True)
        modulo_llm = _llm.modulo_fala_com_llm(efetivo, ctx)
        m = RX_ML.search(scan.codigo_efetivo(texto, ".py", sem_literais=True))
        if m:
            linha = texto[:m.start()].count("\n") + 1
            achados.append((arq, linha, f"dependencia de ML: {m.group(1)}"))
        arvore = scan.arvore(p)      # SyntaxError -> CheckIndeterminado
        for no in ast.walk(arvore):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and RX_DECISAO.search(no.name):
                achados.append((arq, no.lineno, f"rotina de decisao: {no.name}()"))
        for no, nome in scan.chamadas(arvore):
            if RX_INFERENCIA.match(nome.split(".")[-1]) and "." in nome:
                achados.append((arq, no.lineno, f"chamada de inferencia: {nome}()"))
            elif _llm.e_chamada_llm(nome, ctx, modulo_llm):
                achados.append((arq, no.lineno, f"chamada a modelo de linguagem: {nome}()"))
    return achados


@check("E-00", "ethics", "Escopo do pack de etica", base_legal="EbD-AI")
def escopo(ctx):
    declarado = str(ctx.config.get("decision_making", "")).strip().lower() or None
    if declarado and declarado not in DECLARACOES:
        raise SkipCheck(
            f"decision_making={declarado!r} invalido — use "
            f"{sorted(DECLARACOES)}; pack de etica fora de escopo por "
            f"declaracao ilegivel")

    indicios = _indicios(ctx)

    if declarado in ("assistive", "automated"):
        return []                                  # em escopo, por declaracao

    if indicios:
        if declarado == "none":
            arq, linha, o_que = indicios[0]
            return [Finding(
                check_id="E-00", pack="ethics", severidade=Severidade.ALTO,
                titulo="Escopo declarado diverge do codigo",
                descricao=f"O consumidor declara decision_making: none, mas o "
                          f"codigo mostra {o_que} "
                          f"({len(indicios)} indicio(s) no total). A divergencia "
                          f"entre declaracao e fato e o que um auditor precisa ver.",
                recomendacao="Corrigir a declaracao em pse-config.yaml para "
                             "'assistive'/'automated', ou remover do codigo o que "
                             "sugere decisao automatizada sobre pessoas.",
                base_legal="EbD-AI",
                arquivo=arq, linha=linha, snippet=o_que)]
        return []                                  # em escopo, por fato computado

    motivo = ("nenhum indicio de decisao automatizada sobre pessoas no codigo "
              "(sem dependencia de ML, rotina de decisao ou chamada de inferencia)")
    if declarado == "none":
        motivo += " e o consumidor declara decision_making: none"
    else:
        motivo += " e nada foi declarado em decision_making"
    raise SkipCheck(f"pack de etica fora de escopo: {motivo}")
