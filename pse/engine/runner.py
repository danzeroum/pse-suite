"""Executor do Trabalho B: descobre checks, executa por pack, agrega.

Duas regras estruturais:

**Isolamento por check (D-15).** A falha de um check nao pode derrubar a
execucao inteira nem — pior — desaparecer. Excecao inesperada vira
indeterminacao *daquele* check, os demais seguem, e o laudo sai completo
com o veredito bloqueando (exit 20).

**Guarda de pack (E-00).** Um pack pode declarar um check-guarda que decide
se o pack esta em escopo. Guarda que pula tira o pack inteiro de escopo com
o motivo computado — N/A declarado, jamais verde silencioso.
"""
import importlib
import pkgutil
import time

from pse import catalogo
from pse.model import CheckIndeterminado, EntradaInvalida, SkipCheck
from .context import Contexto
from .registry import CHECKS


def _carregar_checks():
    import pse.checks as pkg
    for mod in pkgutil.walk_packages(pkg.__path__, pkg.__name__ + "."):
        importlib.import_module(mod.name)


def _executar_um(cid, meta, ctx, res):
    """Devolve True se o check decidiu (executou), False se nao decidiu."""
    try:
        achados = meta["fn"](ctx) or []
    except SkipCheck as e:
        # N/A declarado: pre-condicao declarativa ausente. Nao bloqueia,
        # mas o motivo e obrigatorio e fica visivel no laudo.
        res["checks_pulados"].append({"id": cid, "motivo": str(e)})
        return False
    except EntradaInvalida:
        # Declaracao do consumidor quebrada e problema do processo, nao do
        # check: sobe para o CLI virar exit 30.
        raise
    except CheckIndeterminado as e:
        # Tentei e nao consegui decidir. Bloqueia igual a violacao.
        res["checks_indeterminados"].append({"id": cid, "motivo": str(e)})
        return False
    except Exception as e:  # noqa: BLE001 — falha inesperada nunca vira verde
        res["checks_indeterminados"].append({
            "id": cid,
            "motivo": f"erro inesperado no check: {type(e).__name__}: {e}",
        })
        return False
    res["checks_executados"].append(cid)
    res["findings"].extend(achados)
    return True


def executar(repo_path, packs: set, config: dict | None = None) -> dict:
    _carregar_checks()
    ctx = Contexto(repo_path, config)
    inicio = time.time()
    res = {"findings": [], "checks_executados": [],
           "checks_pulados": [], "checks_indeterminados": []}

    fora_de_escopo = {}
    for pack in sorted(packs):
        for gid in catalogo.guardas_de(pack):
            meta = CHECKS.get(gid)
            if not meta:
                continue
            antes = len(res["checks_pulados"])
            _executar_um(gid, meta, ctx, res)
            if len(res["checks_pulados"]) > antes:
                # A guarda pulou: o pack inteiro sai de escopo com o motivo dela.
                fora_de_escopo[pack] = res["checks_pulados"][-1]["motivo"]

    for cid, meta in sorted(CHECKS.items()):
        if meta["pack"] not in packs or meta["guarda_de_pack"]:
            continue
        if meta["pack"] in fora_de_escopo:
            res["checks_pulados"].append({
                "id": cid,
                "motivo": f"pack '{meta['pack']}' fora de escopo por E-00: "
                          f"{fora_de_escopo[meta['pack']]}",
            })
            continue
        _executar_um(cid, meta, ctx, res)

    res["packs_fora_de_escopo"] = [
        {"pack": p, "motivo": m} for p, m in sorted(fora_de_escopo.items())]
    # Previsto e ausente: o catalogo torna dizivel o que o registro nao sabe.
    res["checks_previstos"] = catalogo.previstos(packs)
    res["duracao_s"] = round(time.time() - inicio, 2)
    return res
