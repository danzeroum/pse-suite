"""Contexto de execucao: repo alvo + regua curada + config declarativa."""
from pathlib import Path
import yaml

from pse.engine import yamlloc
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
    def __init__(self, repo_path, config: dict | None = None,
                 modo: str = "pse_inventory", transporte=None):
        self.repo = Path(repo_path)
        self.config = config or {}
        # Modo de execucao (pse_inventory | pse_passive | pse_active). Decide
        # quais checks de Trabalho A sao disparados; nunca afrouxa gate.
        self.modo = modo
        # Transporte injetavel: e o que permite provar, em teste, que nenhuma
        # requisicao foi emitida antes da atestacao passar.
        self.transporte = transporte
        self._cliente = None
        self._saude = None
        # Relatorios que um check quer anexar ao laudo (ex.: cobertura do
        # catalogo). Nao sao findings: descrevem o estado, nao um defeito.
        self.relatorios: dict = {}
        # A regua: carregada do PACOTE, nunca do consumidor.
        self.data = {
            f.stem: yaml.safe_load(f.read_text(encoding="utf-8"))
            for f in sorted(DATA_DIR.glob("*.yaml"))
        }

    def cliente_http(self, alvo):
        """Cliente unico por execucao — traces de todos os checks num lugar so."""
        if self._cliente is None:
            from pse.trabalho_a.base import novo_cliente
            self._cliente = novo_cliente(alvo, transporte=self.transporte)
        return self._cliente

    def exigir_alvo_saudavel(self, cliente, alvo):
        """Healthcheck UMA vez por execucao; o veredito vale para todos.

        Alvo caido nao merece uma sonda sequer: o primeiro check que descobre
        a queda a memoriza, e os seguintes ficam indeterminados sem tocar a
        rede. E o que faz "healthcheck 503 -> zero sondas" ser verdade, e nao
        apenas intencao.
        """
        from pse.model import CheckIndeterminado
        rota = alvo.get("healthcheck")
        if not rota:
            return
        if self._saude is None:
            try:
                resposta, _ = cliente.requisitar("GET", rota, identidade="anonima")
                self._saude = resposta.status
            except CheckIndeterminado as e:
                self._saude = f"inacessivel: {e}"
        if self._saude != 200:
            raise CheckIndeterminado(
                f"alvo indisponivel: healthcheck {rota} respondeu {self._saude} "
                f"— nenhuma sonda e enviada contra alvo que nao esta de pe")

    def relatorio(self, nome: str, dados: dict):
        self.relatorios[nome] = dados

    def catalog_path(self) -> str:
        return self.config.get("catalog_path", "tests/qa/catalog.yaml")

    def catalog(self):
        """Catalogo vivo de dados do consumidor (declarativo)."""
        p = self.repo / self.catalog_path()
        if not p.exists():
            return None
        return _ler_yaml(p, "catalogo de dados")

    def linha_no_catalogo(self, *caminho) -> int | None:
        """Linha de uma chave do catalogo, para o `arquivo:linha` do finding."""
        return yamlloc.localizar_em(self.repo / self.catalog_path(), caminho)

    def manifesto_path(self) -> str:
        return self.config.get("third_party_manifest",
                               ".privacy/third-party-manifest.yml")

    def linha_da_integracao(self, nome) -> int | None:
        """Entrada de lista no manifesto: localizada pelo par `name: <valor>`."""
        return yamlloc.localizar_valor_em(
            self.repo / self.manifesto_path(), "name", nome)

    def manifest_terceiros(self):
        rel = self.config.get("third_party_manifest",
                              ".privacy/third-party-manifest.yml")
        p = self.repo / rel
        if not p.exists():
            return None
        return _ler_yaml(p, "manifesto de terceiros")
