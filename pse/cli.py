"""CLI da PSE Suite — Trabalho B (inventario estatico).

Fail-closed: qualquer finding CRITICO -> exit 1. Nao existe flag para
desligar — uma trava que o vigiado pode desligar em silencio nao e trava.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

from pse.engine.runner import executar
from pse.evidence import montar_laudo

PACKS_VALIDOS = {"privacy", "security", "ethics"}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pse")
    ap.add_argument("--path", required=True, help="repositorio consumidor")
    ap.add_argument("--packs", default="privacy,security,ethics")
    ap.add_argument("--config", default=None,
                    help="tests/qa/pse-config.yaml do consumidor (declarativo)")
    ap.add_argument("--output", default=None, help="arquivo do laudo JSON")
    args = ap.parse_args(argv)

    packs = {p.strip() for p in args.packs.split(",") if p.strip()}
    invalidos = packs - PACKS_VALIDOS
    if invalidos:
        print(f"packs invalidos: {sorted(invalidos)}", file=sys.stderr)
        return 2

    config = {}
    if args.config:
        raw = yaml.safe_load(Path(args.config).read_text(encoding="utf-8")) or {}
        config = raw.get("pse_suite", raw)

    resultados = executar(args.path, packs, config)
    laudo = montar_laudo(args.path, resultados, packs, args.config)
    texto = json.dumps(laudo, ensure_ascii=False, indent=2)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(texto, encoding="utf-8")
        print(f"laudo: {out}")
    else:
        print(texto)

    criticos = laudo["resumo"]["por_severidade"].get("CRITICO", 0)
    if criticos:
        print(f"FAIL-CLOSED: {criticos} finding(s) CRITICO(s) — gate aborta.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
