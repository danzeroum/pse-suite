"""P-16 — dataset de treino sem governanca declarada.

O E-08 dos dados de treino. E-08 cobra a trilha do dado em producao; aqui a
pergunta e sobre o conjunto que produziu o modelo: **de onde veio, para que
serve, e ate quando fica?**

Dataset de treino costuma ser o unico artefato do sistema que ninguem
inventaria. Vive num bucket, foi montado uma vez, e sobrevive a todas as
politicas de retencao porque nao esta em tabela nenhuma. Meses depois,
ninguem sabe dizer se aquele parquet ainda podia existir — e um pedido de
eliminacao do Art. 18 nao alcanca o que o inventario nao conhece.

O check nao adivinha qual arquivo e dataset: olha o que os CARREGADORES
recebem em modulos que treinam. Sem treino no codigo, nao ha o que
inventariar e o check e pulado com motivo.
"""
import ast
from pathlib import PurePosixPath

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

BASE = "LGPD Art. 6o I e V + Art. 16 (finalidade, qualidade e eliminacao)"
REGUA = "adversarial-patterns"
OBRIGATORIOS = ("finalidade", "retention_years")


def _termos(ctx, chave) -> set:
    return {t.lower() for t in ctx.data[REGUA][chave]}


def _chave_do_dataset(literal: str) -> str:
    """`dados/base_clientes.csv` -> `base_clientes`. O consumidor declara o
    nome logico, nao o caminho — que muda quando o bucket muda."""
    return PurePosixPath(str(literal)).stem.lower()


def _datasets_carregados(ctx, arvore) -> list:
    carregadores = _termos(ctx, "carregadores_de_dataset")
    saida = []
    for no, nome in scan.chamadas(arvore):
        if nome.split(".")[-1].lower() not in carregadores:
            continue
        for arg in list(no.args) + [k.value for k in no.keywords]:
            for sub in ast.walk(arg):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str) \
                        and sub.value.strip():
                    saida.append((no, sub.value))
    return saida


def _treina(ctx, arvore) -> bool:
    treino = _termos(ctx, "chamadas_de_treino")
    return any(n.split(".")[-1].lower() in treino for _, n in scan.chamadas(arvore))


@check("P-16", "privacy", "Dataset de treino sem governanca", base_legal=BASE)
def dataset_sem_governanca(ctx):
    candidatos, houve_treino = [], False
    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        if not _treina(ctx, arvore):
            continue
        houve_treino = True
        candidatos.append((p, _datasets_carregados(ctx, arvore)))

    if not houve_treino:
        raise SkipCheck("nenhuma chamada de treino no codigo — nao ha dataset "
                        "de treino a inventariar")

    cat = ctx.catalog() or {}
    declarados = {str(k).lower(): (v or {})
                  for k, v in (cat.get("datasets") or {}).items()}

    findings, vistos = [], set()
    for p, carregados in candidatos:
        linhas = scan.ler(p).splitlines()
        for no, literal in carregados:
            chave = _chave_do_dataset(literal)
            if not chave or chave in vistos:
                continue
            vistos.add(chave)
            entrada = declarados.get(chave)
            i = no.lineno
            comum = dict(
                check_id="P-16", pack="privacy", severidade=Severidade.ALTO,
                base_legal=BASE, arquivo=scan.rel(ctx.repo, p), linha=i,
                snippet=linhas[i - 1].strip()[:200] if i <= len(linhas) else None)

            if entrada is None:
                findings.append(Finding(
                    titulo=f"Dataset de treino '{chave}' sem entrada de governanca",
                    descricao=f"'{literal}' alimenta um treino e nao tem entrada "
                              f"em `datasets` no catalogo. Dataset de treino "
                              f"costuma ser o unico artefato que ninguem "
                              f"inventaria: vive num bucket, foi montado uma vez "
                              f"e sobrevive a toda politica de retencao porque "
                              f"nao esta em tabela nenhuma. Um pedido de "
                              f"eliminacao nao alcanca o que o inventario "
                              f"desconhece.",
                    recomendacao="Declarar em `datasets` no catalogo: finalidade, "
                                 "retention_years, origem e base legal — o mesmo "
                                 "rigor que se cobra de uma tabela.",
                    **comum))
                continue

            faltando = [c for c in OBRIGATORIOS if not entrada.get(c)]
            if not faltando:
                continue
            findings.append(Finding(
                titulo=f"Dataset de treino '{chave}' com governanca incompleta",
                descricao=f"A entrada existe mas nao declara: {', '.join(faltando)}. "
                          f"Sem finalidade nao da para dizer se o uso e legitimo; "
                          f"sem retencao, o conjunto fica para sempre — e o "
                          f"'para sempre' e a politica que ninguem escolheu.",
                recomendacao="Completar finalidade e retention_years na entrada "
                             "do dataset; retencao de dataset de treino tambem "
                             "precisa de job de purga (P-02).",
                **comum))
    return findings
