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
    """Cliente stdlib. LOOPBACK NUNCA PASSA POR PROXY.

    O problema apareceu no primeiro alvo local de verdade: `urllib` honra
    `HTTPS_PROXY`/`HTTP_PROXY` do ambiente, entao uma requisicao para
    `http://127.0.0.1:5178` saia da maquina, ia ao proxy e voltava 404. O
    healthcheck reprovava um alvo que estava de pe.

    E o defeito era pior que um 404. O degrau `local_target` dispensa a
    prova de posse com UM argumento escrito: em loopback nao ha rede, nao ha
    intermediario e nao ha o que capturar. Se a requisicao atravessa um
    proxy, esse argumento deixa de valer — havia rede, havia intermediario,
    e a atestacao estaria autorizando com base numa premissa falsa.

    Por isso o bypass nao e conveniencia de ambiente: e o que faz o contrato
    de alvo local dizer a verdade.

    O bypass e decidido pelo HOST parseado, nunca por prefixo de string. A
    primeira versao usava `startswith("https://127.0.0.1")` e casava
    `https://127.0.0.1.exemplo.com` — qualquer host publico podia escolher o
    proprio nome para escapar do proxy do ambiente.
    """

    def _abridor(self, url):
        from pse.trabalho_a.autorizacao import host_e_loopback
        if host_e_loopback(url):
            # `build_opener` com um ProxyHandler vazio nao apenas ignora os
            # proxies do ambiente: ele tira o ProxyHandler PADRAO da cadeia,
            # que e quem leria `HTTPS_PROXY`.
            return urllib.request.build_opener(
                urllib.request.ProxyHandler({})).open
        return urllib.request.urlopen

    def enviar(self, metodo, url, headers, corpo, timeout) -> Resposta:
        dados = corpo.encode("utf-8") if isinstance(corpo, str) else corpo
        req = urllib.request.Request(url, data=dados, method=metodo,
                                     headers=headers or {})
        abrir = self._abridor(url)
        try:
            with abrir(req, timeout=timeout) as r:
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

    def requisitar(self, metodo, rota, token=None, corpo=None, identidade=None,
                   extra_headers=None, sem_corpo_no_trace=False):
        """`sem_corpo_no_trace` omite a amostra da resposta no trace.

        Existe para P-10: o pacote de portabilidade E os dados do titular, e
        arquivar 8 KB dele em `harness/runs/` seria vazar exatamente o que o
        check prova que o titular tem direito de receber — em outro lugar.
        Mascarar nao basta; aqui a resposta certa e nao gravar.
        """
        headers = {"Accept": "application/json",
                   "User-Agent": "pse-suite/trabalho-a"}
        if extra_headers:
            headers.update(extra_headers)
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
                # Cabecalhos declarados pelo check (ex.: X-Purpose). Authorization
                # nunca entra aqui: ele e removido antes, nao mascarado.
                "headers": sanitizar_profundo(
                    {k: v for k, v in headers.items() if k != "Authorization"}),
            },
            "resposta": {
                "status": resposta.status,
                "corpo_amostra": (
                    f"<omitido: {len(resposta.corpo)} bytes contendo dados do "
                    f"titular>" if sem_corpo_no_trace
                    else sanitizar(resposta.corpo[:CORPO_MAX])),
            },
        }
        self.traces.append(trace)
        return resposta, trace
