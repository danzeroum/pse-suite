"""Cliente HTTP do Trabalho A, com trace sanitizado na origem.

Duas decisoes deliberadas:

**stdlib, sem dependencia de rede nova.** `urllib.request` basta e mantem a
promessa do Trabalho B: nada aqui e importado ou executado num inventario
estatico, e a suite nao ganha um cliente HTTP transitivo que ela nao audita.

**Transporte injetavel.** O teste substitui o transporte e conta requisicoes.
E assim que se prova a unica coisa que realmente importa nesta fase: que
NADA foi enviado antes da atestacao passar.
"""
import json
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from pse.model import CheckIndeterminado
from pse.sanitize import sanitizar, sanitizar_profundo

TIMEOUT_PADRAO = 10
CORPO_MAX = 8_000        # o trace guarda amostra, nao dump do alvo


@dataclass
class Resposta:
    status: int
    corpo: str = ""
    headers: dict = field(default_factory=dict)

    def json(self):
        try:
            return json.loads(self.corpo)
        except (ValueError, TypeError):
            return None


class TransporteUrllib:
    def enviar(self, metodo, url, headers, corpo, timeout) -> Resposta:
        dados = corpo.encode("utf-8") if isinstance(corpo, str) else corpo
        req = urllib.request.Request(url, data=dados, method=metodo,
                                     headers=headers or {})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return Resposta(r.status, r.read(CORPO_MAX).decode("utf-8", "ignore"),
                                dict(r.headers))
        except urllib.error.HTTPError as e:
            # 4xx/5xx sao RESPOSTA, nao falha: sao exatamente o que os checks
            # de sonda precisam ler.
            return Resposta(e.code, e.read(CORPO_MAX).decode("utf-8", "ignore"),
                            dict(e.headers or {}))
        except Exception as e:
            raise CheckIndeterminado(
                f"alvo inacessivel em {metodo} (timeout ou rede): "
                f"{type(e).__name__}") from e


class Cliente:
    """Emite requisicao e grava o trace ja mascarado.

    O token nunca entra no trace, nem mascarado: o cabecalho e substituido
    por um rotulo. Mascarar um segredo e melhor que publica-lo; nao grava-lo
    e melhor que mascara-lo.
    """

    def __init__(self, base_url, transporte=None, timeout=TIMEOUT_PADRAO):
        self.base_url = str(base_url).rstrip("/")
        self.transporte = transporte or TransporteUrllib()
        self.timeout = timeout
        self.traces = []

    def _url(self, rota):
        return f"{self.base_url}{rota if rota.startswith('/') else '/' + rota}"

    def requisitar(self, metodo, rota, token=None, corpo=None, identidade=None):
        headers = {"Accept": "application/json",
                   "User-Agent": "pse-suite/trabalho-a"}
        if corpo is not None:
            headers["Content-Type"] = "application/json"
        if token:
            headers["Authorization"] = f"Bearer {token}"

        payload = json.dumps(corpo) if isinstance(corpo, (dict, list)) else corpo
        resposta = self.transporte.enviar(metodo, self._url(rota), headers,
                                          payload, self.timeout)

        trace = {
            "requisicao": {
                "metodo": metodo,
                "rota": sanitizar(rota),
                "identidade": identidade or "anonima",
                # O valor do token nao e gravado nem mascarado.
                "autenticada": bool(token),
                "corpo": sanitizar_profundo(corpo) if corpo is not None else None,
            },
            "resposta": {
                "status": resposta.status,
                "corpo_amostra": sanitizar(resposta.corpo[:CORPO_MAX]),
            },
        }
        self.traces.append(trace)
        return resposta, trace
