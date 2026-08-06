"""Executor do Trabalho B: descobre checks, executa por pack, agrega.

Isolamento por check (D-15): a falha de um check nao pode derrubar a
execucao inteira nem — pior — desaparecer. Excecao inesperada vira
indeterminacao *daquele* check, os demais seguem, e o laudo sai completo
com o veredito bloqueando (exit 20).
"""
import importlib
import pkgutil
import time

from pse.model import CheckIndeterminado, EntradaInvalida, SkipCheck
from .context import Contexto
from .registry import CHECKS


def _carregar_checks():
    import pse.checks as pkg
    for mod in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        importlib.import_module(mod.name)


def executar(repo_path, packs: set, config: dict | None = None) -> dict:
    _carregar_checks()
    ctx = Contexto(repo_path, config)
    inicio = time.time()
    res = {"findings": [], "checks_executados": [],
           "checks_pulados": [], "checks_indeterminados": []}

    for cid, meta in sorted(CHECKS.items()):
        if meta["pack"] not in packs:
            continue
        try:
            achados = meta["fn"](ctx) or []
        except SkipCheck as e:
            # N/A declarado: pre-condicao declarativa ausente. Nao bloqueia,
            # mas o motivo e obrigatorio e fica visivel no laudo.
            res["checks_pulados"].append({"id": cid, "motivo": str(e)})
            continue
        except EntradaInvalida:
            # Declaracao do consumidor quebrada e problema do processo, nao
            # do check: sobe para o CLI virar exit 30.
            raise
        except CheckIndeterminado as e:
            # Tentei e nao consegui decidir. Bloqueia igual a violacao.
            res["checks_indeterminados"].append({"id": cid, "motivo": str(e)})
            continue
        except Exception as e:  # noqa: BLE001 — falha inesperada nunca vira verde
            res["checks_indeterminados"].append({
                "id": cid,
                "motivo": f"erro inesperado no check: {type(e).__name__}: {e}",
            })
            continue
        res["checks_executados"].append(cid)
        res["findings"].extend(achados)

    res["duracao_s"] = round(time.time() - inicio, 2)
    return res
