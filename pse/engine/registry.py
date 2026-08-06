"""Registro central de checks. Cada check tem ID estavel (P-*, S-*, E-*),
pack, titulo e base legal — o laudo referencia por ID, nunca por path.

O ID e validado contra o catalogo (pse/data/checks-catalog.yaml) no momento
do registro: check que nao esta declarado no catalogo nao entra. E o que
impede o registro e a declaracao de derivarem um do outro (D-12/D-14).
"""
from pse import catalogo

CHECKS: dict = {}


class CheckNaoCatalogado(Exception):
    """Check registrado sem entrada no catalogo da suite."""


def check(check_id: str, pack: str, titulo: str, base_legal: str | None = None):
    def deco(fn):
        if not catalogo.existe(check_id):
            raise CheckNaoCatalogado(
                f"{check_id} nao consta em pse/data/checks-catalog.yaml. "
                f"Todo check declara-se no catalogo antes de existir em codigo "
                f"— e o catalogo que torna a cobertura calculavel.")
        esperado = catalogo.pilar_esperado(check_id)
        if esperado is None:
            raise CheckNaoCatalogado(
                f"prefixo de {check_id} fora do vocabulario de pilares "
                f"{sorted(catalogo.PREFIXO_DO_PILAR.values())}. O prefixo do ID "
                f"codifica o PILAR, sempre — dominio e multivalorado e vive em "
                f"`domain`, nunca no prefixo.")
        if esperado != pack:
            raise CheckNaoCatalogado(
                f"{check_id} tem prefixo de '{esperado}' e foi registrado no "
                f"pack '{pack}' — o prefixo do ID e a declaracao do pilar.")
        meta = catalogo.meta(check_id)
        if meta.get("pack") != pack:
            raise CheckNaoCatalogado(
                f"{check_id} registrado no pack '{pack}' mas catalogado em "
                f"'{meta.get('pack')}'")
        CHECKS[check_id] = {
            "id": check_id,
            "pack": pack,
            "titulo": meta.get("titulo", titulo),
            # Fonte unica: o catalogo. O argumento do decorator fica como
            # fallback para nao quebrar checks em desenvolvimento.
            "base_legal": meta.get("base_legal", base_legal),
            "domain": catalogo.dominios(check_id),
            "guarda_de_pack": bool(meta.get("guarda_de_pack")),
            "fn": fn,
        }
        return fn
    return deco
