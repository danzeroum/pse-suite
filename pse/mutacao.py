"""Prova de mutacao — Gap 4, o inverso canonico de cada check.

Um check que nunca foi visto reprovando nada e uma hipotese, nao uma trava.
Cada check bloqueante declara no catalogo a **violacao minima que deve
produzir vermelho**; a release so sai se todas reproduzirem, e check
implementado sem mutacao declarada **reprova a si mesmo**.

Separacao deliberada entre dado e motor (aprovacao §4b): a declaracao vive
no catalogo — e estavel, revisavel e sobrevive a troca de motor. Este
executor e **interino**, marcado como tal: se o `mutation-engine`
compartilhado da CP-A se materializar, ele consome as mesmas declaracoes e
este arquivo e deletado sem tocar em nenhum catalogo.
"""
import tempfile
from pathlib import Path

from pse import catalogo
from pse.engine.context import Contexto
from pse.engine.registry import CHECKS
from pse.engine.runner import _carregar_checks
from pse.model import CheckIndeterminado, SkipCheck

INTERINO = True   # ver docstring: motor local ate a CP-A ser confirmada


def _materializar(destino: Path, arquivos: dict):
    for nome, conteudo in (arquivos or {}).items():
        alvo = destino / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")


def provar(check_id: str) -> dict:
    """Aplica a mutacao canonica do check e exige que ele a encontre."""
    _carregar_checks()
    meta_cat = catalogo.meta(check_id)
    mut = meta_cat.get("canonical_mutation")

    if not mut:
        return {"check": check_id, "ok": False,
                "motivo": "check implementado SEM mutacao canonica declarada — "
                          "um check que nunca foi visto reprovando nada nao e "
                          "uma trava, e por isso reprova a si mesmo"}

    registrado = CHECKS.get(check_id)
    if not registrado:
        return {"check": check_id, "ok": False,
                "motivo": "declarado como implementado mas nao registrado"}

    esperada = mut.get("espera_severidade")
    with tempfile.TemporaryDirectory(prefix="pse-mut-") as tmp:
        alvo = Path(tmp)
        _materializar(alvo, mut.get("arquivos"))
        ctx = Contexto(alvo, dict(mut.get("config") or {}))
        try:
            achados = registrado["fn"](ctx) or []
        except SkipCheck as e:
            return {"check": check_id, "ok": False,
                    "motivo": f"a mutacao nao chegou a ser avaliada (pulado): {e}"}
        except CheckIndeterminado as e:
            return {"check": check_id, "ok": False,
                    "motivo": f"a mutacao deixou o check indeterminado: {e}"}
        except Exception as e:  # noqa: BLE001
            return {"check": check_id, "ok": False,
                    "motivo": f"erro ao avaliar a mutacao: {type(e).__name__}: {e}"}

    meus = [f for f in achados if f.check_id == check_id]
    if not meus:
        return {"check": check_id, "ok": False,
                "motivo": f"a mutacao canonica NAO produziu vermelho "
                          f"({mut.get('descricao')}) — o check parou de morder"}

    severidades = {f.severidade.value for f in meus}
    if esperada and esperada not in severidades:
        return {"check": check_id, "ok": False,
                "motivo": f"mutacao produziu {sorted(severidades)}, "
                          f"esperado {esperada}"}

    return {"check": check_id, "ok": True,
            "motivo": f"reprovou como esperado ({esperada}): {mut.get('descricao')}",
            "achados": len(meus)}


def provar_todas() -> dict:
    """Toda a autoprova de mutacao. Nenhum check implementado escapa."""
    resultados = [provar(cid) for cid in catalogo.implementados()]
    falhas = [r for r in resultados if not r["ok"]]
    return {
        "ok": not falhas,
        "interino": INTERINO,
        "total": len(resultados),
        "falhas": falhas,
        "provados": [r["check"] for r in resultados if r["ok"]],
    }
