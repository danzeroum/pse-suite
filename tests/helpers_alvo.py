"""Alvo de teste compartilhado entre as fases do Trabalho A.

O transporte conta tudo o que sai. E o unico jeito de provar, e nao
apenas afirmar, que nenhuma sonda foi emitida antes da hora.
"""
from datetime import date, timedelta

from pse.trabalho_a.autorizacao import fingerprint_alvo
from pse.trabalho_a.cliente import Resposta

BASE = "https://staging.exemplo.invalido"
TOKEN_A, TOKEN_B = "PSE_TOKEN_A", "PSE_TOKEN_B"
UUID_B = "9f1c2e3a-0000-4000-8000-000000000000"
ROTA_B = f"/api/clientes/{UUID_B}"

CHECKS_A = {"S-01", "S-02", "S-03", "P-05", "P-11", "E-01", "E-02", "E-03"}


class Transporte:
    """Conta tudo o que sai. Nenhuma sonda escapa desta lista."""

    def __init__(self, por_rota=None, saude=200):
        self.por_rota = por_rota or {}
        self.saude = saude
        self.chamadas = []

    def enviar(self, metodo, url, headers, corpo, timeout):
        rota = url.replace(BASE, "")
        self.chamadas.append((metodo, rota))
        if rota == "/health":
            return Resposta(self.saude, "{}", {})
        for chave, resp in self.por_rota.items():
            if rota.startswith(chave):
                return resp() if callable(resp) else resp
        return Resposta(404, "{}", {})

    @property
    def sondas(self):
        """Tudo que nao e healthcheck."""
        return [c for c in self.chamadas if c[1] != "/health"]


def alvo(scope=("pse_passive", "pse_active"), expires=None, ambiente="staging",
         fingerprint=None, sinteticas=True, recursos=(ROTA_B,), endpoints=None,
         com_autorizacao=True):
    conf = {
        "base_url": BASE,
        "environment": ambiente,
        "healthcheck": "/health",
        "identities": {"titular_a": {"token_env": TOKEN_A},
                       "titular_b": {"token_env": TOKEN_B}},
        "resources_titular_b": list(recursos),
        "endpoints": endpoints if endpoints is not None else {
            "inexistente": "/api/clientes/00000000-0000-4000-8000-000000000000",
            "erro": "/api/erro", "listagem": "/api/clientes",
            "escrita": "/api/clientes", "decisao": "/api/decisoes/ultima",
            "contestacao": "/api/contestacoes"},
    }
    if com_autorizacao:
        conf["authorization"] = {
            "attested_by": "dpo@exemplo.com",
            "scope": list(scope),
            "target_fingerprint": fingerprint or fingerprint_alvo(BASE),
            "expires": expires or (date.today() + timedelta(days=30)).isoformat(),
            "synthetic_identities": sinteticas,
        }
    return {"target": conf, "decision_making": "automated",
            "catalog_path": "catalog.yaml"}


