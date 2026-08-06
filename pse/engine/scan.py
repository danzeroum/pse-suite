"""Utilitarios de varredura estatica (Trabalho B — sem rede)."""
import re
from pathlib import Path

IGNORAR_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__",
                "dist", "build", ".mypy_cache", ".pytest_cache"}
TAMANHO_MAX = 2_000_000  # 2MB


def arquivos(repo: Path, exts: set):
    for p in sorted(repo.rglob("*")):
        if any(part in IGNORAR_DIRS for part in p.parts):
            continue
        if p.is_file() and p.suffix in exts:
            try:
                if p.stat().st_size < TAMANHO_MAX:
                    yield p
            except OSError:
                continue


def ler(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def grep(path: Path, pattern: str, flags=re.IGNORECASE):
    """Linhas que casam com o regex: [(numero_da_linha, snippet<=200c)]."""
    rx = re.compile(pattern, flags)
    out = []
    for i, linha in enumerate(ler(path).splitlines(), 1):
        if rx.search(linha):
            out.append((i, linha.strip()[:200]))
    return out


def rel(repo: Path, p: Path) -> str:
    try:
        return str(p.relative_to(repo))
    except ValueError:
        return str(p)
