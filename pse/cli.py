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

from pse import catalogo, fingerprint
from pse.engine.runner import executar
from pse.evidence import montar_laudo, versao_suite
from pse.model import (EXIT_ENTRADA_INVALIDA, EXIT_VIOLACAO_CRITICA,
                       EntradaInvalida, VersaoIrresolvivel)
from pse.schemas_validate import LaudoInvalido, validar_laudo
from pse.selftest import autoprova

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


def _packs_efetivos(pedidos: set, config: dict):
    """Interseccao entre o pedido do CLI e a declaracao do consumidor (D-04).

    O `packs` do pse-config.yaml era decorativo: um consumidor que declarava
    `security: {enabled: false}` continuava sendo auditado em security. A
    declaracao passa a valer — e a omissao vira DECLARADA, com o motivo no
    laudo. Desligar tudo, porem, nao pode produzir um "conforme" barato:
    sem pack nenhum nao ha o que auditar, e isso e entrada invalida.
    """
    declarados = config.get("packs") or {}
    desabilitados = []
    for pack in sorted(pedidos):
        decl = declarados.get(pack)
        if isinstance(decl, dict) and decl.get("enabled") is False:
            desabilitados.append({
                "pack": pack,
                "motivo": "declarado enabled: false em pse-config.yaml",
            })
    efetivos = pedidos - {d["pack"] for d in desabilitados}
    if not efetivos:
        raise EntradaInvalida(
            "todos os packs pedidos estao desabilitados em pse-config.yaml — "
            "nao ha o que auditar, e um laudo vazio nao e um laudo conforme")
    return efetivos, desabilitados


def _cmd_self_test() -> int:
    r = autoprova()
    print(json.dumps(r, ensure_ascii=False, indent=2))
    if r["ok"]:
        print("autoprova OK — a trava desta versao instalada morde.",
              file=sys.stderr)
        return 0
    print(f"AUTOPROVA FALHOU: {r['motivo']}", file=sys.stderr)
    return EXIT_VIOLACAO_CRITICA


def _cmd_manifesto() -> int:
    """Manifesto de release: o que um consumidor precisa para ancorar o pin."""
    try:
        versao = versao_suite()
    except VersaoIrresolvivel as e:
        return _erro(str(e))
    prova = autoprova()
    manifesto = {
        "suite": "pse-suite",
        "suite_version": versao,
        "schema_version": fingerprint.SCHEMA_VERSION,
        "catalog_hash": fingerprint.catalog_hash(),
        "checks_implementados": catalogo.implementados(),
        "checks_previstos": [c["id"] for c in catalogo.previstos()],
        "autoprova": prova,
    }
    print(json.dumps(manifesto, ensure_ascii=False, indent=2))
    return 0 if prova["ok"] else EXIT_VIOLACAO_CRITICA


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="pse")
    ap.add_argument("--path", help="repositorio consumidor")
    ap.add_argument("--packs", default="privacy,security,ethics")
    ap.add_argument("--config", default=None,
                    help="tests/qa/pse-config.yaml do consumidor (declarativo)")
    ap.add_argument("--output", default=None, help="arquivo do laudo JSON")
    ap.add_argument("--self-test", action="store_true", dest="self_test",
                    help="audita a fixture embarcada e exige vermelho (mordida)")
    ap.add_argument("--manifesto", action="store_true",
                    help="emite o manifesto de release (versao, catalog_hash, autoprova)")
    args = ap.parse_args(argv)

    if args.self_test:
        return _cmd_self_test()
    if args.manifesto:
        return _cmd_manifesto()
    if not args.path:
        return _erro("--path e obrigatorio (ou use --self-test / --manifesto)")

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
        efetivos, desabilitados = _packs_efetivos(packs, config)
        resultados = executar(alvo, efetivos, config)
        resultados["packs_desabilitados"] = desabilitados
        laudo = montar_laudo(alvo, resultados, efetivos, args.config)
        validar_laudo(laudo)
    except EntradaInvalida as e:
        return _erro(str(e))
    except VersaoIrresolvivel as e:
        return _erro(str(e))
    except LaudoInvalido as e:
        # Defeito da suite, nao do consumidor — mas evidencia fora do schema
        # nao pode sair como evidencia valida.
        return _erro(f"{e} (defeito da suite: reporte no repositorio da PSE)")

    texto = json.dumps(laudo, ensure_ascii=False, indent=2)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(texto, encoding="utf-8")
        print(f"laudo: {out}")
    else:
        print(texto)

    if laudo["packs_desabilitados"]:
        nomes = [d["pack"] for d in laudo["packs_desabilitados"]]
        print(f"packs desabilitados por declaracao do consumidor: {nomes}",
              file=sys.stderr)
    if laudo["checks_indeterminados"]:
        print(f"INDETERMINADO: {len(laudo['checks_indeterminados'])} check(s) "
              f"nao puderam ser decididos — bloqueia igual a violacao.",
              file=sys.stderr)
    criticos = laudo["resumo"]["por_severidade"].get("CRITICO", 0)
    if criticos:
        print(f"FAIL-CLOSED: {criticos} finding(s) CRITICO(s) — gate aborta.",
              file=sys.stderr)
    return laudo["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
