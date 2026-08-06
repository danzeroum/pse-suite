"""Executor do Trabalho B: descobre checks, executa por pack, agrega."""
import importlib
import pkgutil
import time

from pse.model import SkipCheck
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
    res = {"findings": [], "checks_executados": [], "checks_pulados": []}
    for cid, meta in sorted(CHECKS.items()):
        if meta["pack"] not in packs:
            continue
        try:
            achados = meta["fn"](ctx) or []
        except SkipCheck as e:
            res["checks_pulados"].append({"id": cid, "motivo": str(e)})
            continue
        res["checks_executados"].append(cid)
        res["findings"].extend(achados)
    res["duracao_s"] = round(time.time() - inicio, 2)
    return res
