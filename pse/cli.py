"""CLI da PSE Suite — Trabalho B (inventario estatico).

Fail-closed sem valvula: nao existe flag que rebaixe o gate. A suite reporta
a verdade em codigos distintos e a politica de bloqueio vive no CI do
consumidor, declarativa e protegida por CODEOWNERS — onde o dono da decisao
e visivel.

Mapa de saida (Etapa 3 §2.2), precedencia 30 > 10 > 20 > 11 > 0:

    0   conforme
    10  violacao com CRITICO
    11  violacao com ALTO, sem CRITICO
    20  indeterminado — 'nao consegui auditar' bloqueia igual
    30  entrada invalida — path/config/catalogo/versao irresolviveis

'Nao olhei' nunca compartilha codigo de saida com 'conforme'.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

from pse.engine.runner import executar
from pse.evidence import montar_laudo
from pse.model import (EXIT_ENTRADA_INVALIDA, EntradaInvalida,
                       VersaoIrresolvivel)

PACKS_VALIDOS = {"privacy", "security", "ethics"}


def _erro(msg: str) -> int:
    print(f"ENTRADA INVALIDA: {msg}", file=sys.stderr)
    return EXIT_ENTRADA_INVALIDA


def _carregar_config(caminho):
    if not caminho:
        return {}
    p = Path(caminho)
    if not p.exists():
        raise EntradaInvalida(f"config declarada e inexistente: {caminho}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise EntradaInvalida(f"config ilegivel ({caminho}): {e}") from e
    if not isinstance(raw, dict):
        raise EntradaInvalida(f"config nao e um mapeamento: {caminho}")
    return raw.get("pse_suite", raw)


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
        return _erro(f"packs invalidos: {sorted(invalidos)}")
    if not packs:
        return _erro("nenhum pack selecionado")

    # Auditar o que nao existe jamais e 'conforme' (Gap 2). Em 1eb616b um
    # diretorio inexistente saia exit 0 com 9 checks 'executados'.
    alvo = Path(args.path)
    if not alvo.exists():
        return _erro(f"path do alvo nao existe: {args.path}")
    if not alvo.is_dir():
        return _erro(f"path do alvo nao e um diretorio: {args.path}")

    try:
        config = _carregar_config(args.config)
        resultados = executar(alvo, packs, config)
        laudo = montar_laudo(alvo, resultados, packs, args.config)
    except EntradaInvalida as e:
        return _erro(str(e))
    except VersaoIrresolvivel as e:
        return _erro(str(e))

    texto = json.dumps(laudo, ensure_ascii=False, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(texto, encoding="utf-8")
        print(f"laudo: {out}")
    else:
        print(texto)

    codigo = laudo["exit_code"]
    if laudo["checks_indeterminados"]:
        print(f"INDETERMINADO: {len(laudo['checks_indeterminados'])} check(s) "
              f"nao puderam ser decididos — bloqueia igual a violacao.",
              file=sys.stderr)
    criticos = laudo["resumo"]["por_severidade"].get("CRITICO", 0)
    if criticos:
        print(f"FAIL-CLOSED: {criticos} finding(s) CRITICO(s) — gate aborta.",
              file=sys.stderr)
    return codigo


if __name__ == "__main__":
    sys.exit(main())
