"""Registro central de checks. Cada check tem ID estavel (P-*, S-*, E-*),
pack, titulo e base legal — o laudo referencia por ID, nunca por path."""

CHECKS: dict = {}


def check(check_id: str, pack: str, titulo: str, base_legal: str | None = None):
    def deco(fn):
        CHECKS[check_id] = {
            "id": check_id, "pack": pack, "titulo": titulo,
            "base_legal": base_legal, "fn": fn,
        }
        return fn
    return deco
