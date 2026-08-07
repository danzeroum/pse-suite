"""Verifica que a triagem cobre exatamente os achados de cada laudo — sem
sobra, sem repeticao, sem indice inventado. Um relatorio cuja contagem nao
fecha e um relatorio que ninguem consegue conferir."""
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent / "docs" / "reconhecimento"
CLASSES = ("V", "F", "I")
ROTULO = {"V": "VIOLACAO-PROVAVEL", "F": "FALSO-POSITIVO-PROVAVEL", "I": "INCERTO"}


def main() -> int:
    triagem = json.loads((BASE / "triagem.json").read_text(encoding="utf-8"))
    erros, tot = [], dict.fromkeys(CLASSES, 0)
    linhas = []

    for alvo, mapa in triagem.items():
        if alvo.startswith("_"):
            continue
        laudo = json.loads((BASE / "laudos" / f"laudo-{alvo}.json").read_text(encoding="utf-8"))
        n = len(laudo["findings"])
        idx = [i for c in CLASSES for i in mapa[c]]

        if sorted(idx) != list(range(n)):
            faltando = sorted(set(range(n)) - set(idx))
            repetido = sorted({i for i in idx if idx.count(i) > 1})
            invalido = sorted(i for i in idx if i >= n)
            erros.append(f"{alvo}: {n} achados; faltando={faltando} "
                         f"repetido={repetido} invalido={invalido}")

        for c in CLASSES:
            tot[c] += len(mapa[c])
        linhas.append((alvo, n, *(len(mapa[c]) for c in CLASSES)))

    print(f"{'alvo':32} {'total':>6} {'V':>4} {'F':>4} {'I':>4}")
    for alvo, n, v, f, i in linhas:
        print(f"{alvo:32} {n:6} {v:4} {f:4} {i:4}")
    total = sum(tot.values())
    print(f"{'TOTAL':32} {total:6} {tot['V']:4} {tot['F']:4} {tot['I']:4}")
    for c in CLASSES:
        print(f"  {ROTULO[c]:24} {tot[c]:3}  ({round(100 * tot[c] / total)}%)")

    if erros:
        print("\nFALHA:", file=sys.stderr)
        for e in erros:
            print("  " + e, file=sys.stderr)
        return 1
    print("\nOK — a triagem cobre exatamente os achados de cada laudo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
