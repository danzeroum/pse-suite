"""Contexto de execucao: repo alvo + regua curada + config declarativa."""
from pathlib import Path
import yaml

from pse.model import EntradaInvalida

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _ler_yaml(p: Path, rotulo: str):
    """Declaracao ilegivel e entrada invalida (exit 30), nunca 'ausente'.

    Confundir 'YAML quebrado' com 'arquivo nao existe' faria um catalogo
    corrompido virar N/A declarado — verde por acidente de sintaxe.
    """
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as e:
        raise EntradaInvalida(f"{rotulo} ilegivel ({p}): {e}") from e


class Contexto:
    def __init__(self, repo_path, config: dict | None = None):
        self.repo = Path(repo_path)
        self.config = config or {}
        # A regua: carregada do PACOTE, nunca do consumidor.
        self.data = {
            f.stem: yaml.safe_load(f.read_text(encoding="utf-8"))
            for f in sorted(DATA_DIR.glob("*.yaml"))
        }

    def catalog(self):
        """Catalogo vivo de dados do consumidor (declarativo)."""
        rel = self.config.get("catalog_path", "tests/qa/catalog.yaml")
        p = self.repo / rel
        if not p.exists():
            return None
        return _ler_yaml(p, "catalogo de dados")

    def manifest_terceiros(self):
        rel = self.config.get("third_party_manifest",
                              ".privacy/third-party-manifest.yml")
        p = self.repo / rel
        if not p.exists():
            return None
        return _ler_yaml(p, "manifesto de terceiros")
