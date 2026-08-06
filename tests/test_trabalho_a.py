"""Fase 2 — Trabalho A. O teste que mais importa e o que conta requisicoes.

O risco desta fase nao e errar um veredito: e sondar um alvo sem
autorizacao. Por isso o transporte e injetavel e quase todo teste aqui
termina conferindo `transporte.chamadas` — a intencao declarada em docstring
nao vale nada; a contagem vale.
"""
import json
import re
from datetime import date, timedelta
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar
from pse.model import EXIT_ENTRADA_INVALIDA, EXIT_INDETERMINADO
from pse.trabalho_a.autorizacao import fingerprint_alvo
from pse.trabalho_a.cliente import Resposta

FIX = Path(__file__).parent / "fixtures" / "consumidor_bom"
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


@pytest.fixture(autouse=True)
def _tokens(monkeypatch):
    monkeypatch.setenv(TOKEN_A, "token-de-teste-a")
    monkeypatch.setenv(TOKEN_B, "token-de-teste-b")


def rodar(config, modo, transporte, packs=("privacy", "security", "ethics")):
    return executar(FIX, set(packs), config, modo=modo, transporte=transporte)


def ids(res, campo):
    return {c["id"] for c in res[campo]}


# ================================================== nada antes da atestacao
@pytest.mark.mordida
def test_sem_atestacao_nenhuma_requisicao_e_emitida():
    """Trabalho A habilitado, atestacao ausente: todos os checks A ficam
    indeterminados e o transporte nao ve um unico byte."""
    t = Transporte()
    res = rodar(alvo(com_autorizacao=False), "pse_active", t)
    assert CHECKS_A <= ids(res, "checks_indeterminados")
    assert all(c["motivo"] for c in res["checks_indeterminados"])
    assert t.chamadas == [], f"requisicao emitida sem atestacao: {t.chamadas}"


@pytest.mark.mordida
@pytest.mark.parametrize("config,esperado", [
    (alvo(expires=(date.today() - timedelta(days=1)).isoformat()), "vencida"),
    (alvo(scope=("pse_passive",)), "nao cobre o modo pse_active"),
    (alvo(fingerprint="0" * 64), "target_fingerprint nao corresponde"),
    (alvo(sinteticas=False), "synthetic_identities"),
])
def test_atestacao_invalida_bloqueia_sem_sondar(config, esperado):
    t = Transporte()
    res = rodar(config, "pse_active", t)
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert CHECKS_A <= set(motivos)
    assert any(esperado in m for m in motivos.values()), motivos
    assert t.chamadas == [], f"sondou com atestacao invalida: {t.chamadas}"


@pytest.mark.mordida
def test_token_ausente_no_ambiente_bloqueia(monkeypatch):
    monkeypatch.delenv(TOKEN_A, raising=False)
    t = Transporte()
    res = rodar(alvo(), "pse_active", t)
    motivos = " ".join(c["motivo"] for c in res["checks_indeterminados"])
    assert "PSE_TOKEN_A" in motivos and "ausente no ambiente" in motivos
    assert t.sondas == [], "sondou sem credencial"


# ================================================== recusa da v1: producao
@pytest.mark.mordida
def test_ativo_em_producao_sai_30_sem_emitir_nada(tmp_path, monkeypatch):
    """Nem o healthcheck: a recusa acontece antes de o runner existir."""
    enviadas = []
    monkeypatch.setattr(
        "pse.trabalho_a.cliente.TransporteUrllib.enviar",
        lambda self, *a, **k: enviadas.append(a) or Resposta(200, "{}", {}))
    cfg = tmp_path / "c.yaml"
    cfg.write_text(json.dumps({"pse_suite": alvo(ambiente="production")}))
    rc = main(["--path", str(FIX), "--config", str(cfg), "--modo", "pse_active"])
    assert rc == EXIT_ENTRADA_INVALIDA
    assert enviadas == [], "producao recusada mas alguma requisicao saiu"


def test_passivo_em_producao_e_permitido(tmp_path):
    """A recusa e da SONDA ATIVA. Leitura com a propria identidade continua."""
    from pse.trabalho_a.autorizacao import validar_config
    validar_config(alvo(ambiente="production"), "pse_passive")   # nao levanta


# ================================================== alvo caido
@pytest.mark.mordida
def test_healthcheck_503_para_tudo_apos_o_healthcheck():
    t = Transporte(saude=503)
    res = rodar(alvo(), "pse_active", t)
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert CHECKS_A <= set(motivos)
    assert "503" in " ".join(motivos.values())
    assert t.sondas == [], f"sondou alvo caido: {t.sondas}"
    # O healthcheck e feito UMA vez, nao uma por check.
    assert len([c for c in t.chamadas if c[1] == "/health"]) == 1


# ================================================== S-01
@pytest.mark.pse_security
def test_s01_recurso_de_b_com_token_de_a_retornando_200():
    t = Transporte({ROTA_B: Resposta(200, json.dumps(
        {"id": UUID_B, "cpf": "529.982.247-25", "email": "b@exemplo.com"}))})
    res = rodar(alvo(), "pse_active", t, packs=("security",))
    s01 = [f for f in res["findings"] if f.check_id == "S-01"]
    assert len(s01) == 1
    assert s01[0].severidade.value == "CRITICO"

    # O trace prova o achado sem republicar o que ele denuncia.
    bruto = json.dumps(s01[0].trace, ensure_ascii=False)
    assert UUID_B not in bruto, "UUID do titular B em claro no trace"
    assert "529.982.247-25" not in bruto and "b@exemplo.com" not in bruto
    assert "/api/clientes/" in bruto and '"status": 200' in bruto
    assert "token-de-teste-a" not in bruto


@pytest.mark.pse_security
def test_s01_404_nao_e_achado():
    t = Transporte({ROTA_B: Resposta(404, "{}")})
    res = rodar(alvo(), "pse_active", t, packs=("security",))
    assert not [f for f in res["findings"] if f.check_id == "S-01"]
    assert "S-01" in res["checks_executados"]


@pytest.mark.pse_security
def test_s01_403_e_p11_nao_s01():
    """Negou o acesso mas confirmou a existencia: cada check responde por
    uma coisa so."""
    t = Transporte({
        ROTA_B: Resposta(403, "{}"),
        "/api/clientes/00000000": Resposta(404, "{}")})
    res = rodar(alvo(), "pse_active", t, packs=("security", "privacy"))
    assert not [f for f in res["findings"] if f.check_id == "S-01"]
    p11 = [f for f in res["findings"] if f.check_id == "P-11"]
    assert p11 and p11[0].severidade.value == "CRITICO"


@pytest.mark.pse_privacy
def test_p11_indistinguivel_e_conforme():
    t = Transporte({"/api/clientes/": Resposta(404, "{}")})
    res = rodar(alvo(), "pse_active", t, packs=("privacy",))
    assert not [f for f in res["findings"] if f.check_id == "P-11"]


# ================================================== recursos nao declarados
@pytest.mark.mordida
def test_sem_recurso_de_b_declarado_nao_ha_descoberta():
    t = Transporte()
    res = rodar(alvo(recursos=()), "pse_active", t, packs=("security",))
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "S-01" in motivos
    assert "recurso de B nao declarado" in motivos["S-01"]
    # Os demais checks do pack sondam os endpoints DELES, o que e legitimo.
    # O que nao pode existir e requisicao a um recurso individual — seria
    # tentativa de descobrir qual recurso pertence a B.
    individuais = [c for c in t.sondas if re.match(r"^/api/\w+/[^/]+$", c[1])]
    assert individuais == [], f"tentou descobrir recurso: {individuais}"


@pytest.mark.mordida
def test_endpoint_nao_declarado_nao_vira_busca():
    t = Transporte()
    res = rodar(alvo(endpoints={}), "pse_active", t)
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    for cid in ("S-02", "S-03", "P-05", "E-01", "E-03"):
        assert "nao declarado" in motivos.get(cid, ""), (cid, motivos.get(cid))
    # S-01 nao depende de `endpoints` — ele usa o recurso declarado de B, e
    # sondar aquilo continua correto. O que nao pode e requisicao a rota que
    # o consumidor nao declarou.
    rotas = {c[1] for c in t.sondas}
    assert rotas <= {ROTA_B}, f"sondou rota nao declarada: {rotas - {ROTA_B}}"


# ================================================== demais checks A
@pytest.mark.pse_security
def test_s03_pii_no_payload_de_erro():
    t = Transporte({"/api/erro": Resposta(
        500, '{"erro":"falha para cpf=529.982.247-25 de maria@empresa.com.br"}')})
    res = rodar(alvo(), "pse_passive", t, packs=("security",))
    s03 = [f for f in res["findings"] if f.check_id == "S-03"]
    assert s03 and s03[0].severidade.value == "ALTO"
    assert "529.982.247-25" not in json.dumps(s03[0].trace)


@pytest.mark.pse_security
def test_s02_sem_rate_limit_e_com_rate_limit():
    t = Transporte({"/api/clientes": Resposta(200, '{"itens":[]}')})
    res = rodar(alvo(), "pse_active", t, packs=("security",))
    assert [f for f in res["findings"] if f.check_id == "S-02"]

    chamadas = [0]

    def responde():
        chamadas[0] += 1
        return Resposta(429 if chamadas[0] > 3 else 200, "{}")

    t2 = Transporte({"/api/clientes": responde})
    res2 = rodar(alvo(), "pse_active", t2, packs=("security",))
    assert not [f for f in res2["findings"] if f.check_id == "S-02"]


@pytest.mark.pse_privacy
def test_p05_campo_extra_aceito_e_rejeitado():
    t = Transporte({"/api/clientes": Resposta(201, '{"id":"x"}')})
    res = rodar(alvo(), "pse_active", t, packs=("privacy",))
    assert [f for f in res["findings"] if f.check_id == "P-05"]

    t2 = Transporte({"/api/clientes": Resposta(422, '{"erro":"campo desconhecido"}')})
    res2 = rodar(alvo(), "pse_active", t2, packs=("privacy",))
    assert not [f for f in res2["findings"] if f.check_id == "P-05"]


@pytest.mark.pse_ethics
def test_e01_e_e02_decisao_sem_explicacao_e_sem_log():
    t = Transporte({"/api/decisoes": Resposta(200, '{"aprovado":false}')})
    res = rodar(alvo(), "pse_passive", t, packs=("ethics",))
    assert {"E-01", "E-02"} <= {f.check_id for f in res["findings"]}

    completo = json.dumps({
        "aprovado": False, "motivo": "score abaixo do piso",
        "fatores": ["renda"], "modelo_v": "3.1", "features": {"renda": 1200},
        "score": 412, "limiar": 500, "revisor": "analista-07"})
    t2 = Transporte({"/api/decisoes": Resposta(200, completo)})
    res2 = rodar(alvo(), "pse_passive", t2, packs=("ethics",))
    assert not [f for f in res2["findings"] if f.check_id in ("E-01", "E-02")]


@pytest.mark.pse_ethics
def test_e03_contestacao_sem_protocolo():
    t = Transporte({"/api/contestacoes": Resposta(201, '{"status":"recebido"}')})
    res = rodar(alvo(), "pse_active", t, packs=("ethics",))
    assert [f for f in res["findings"] if f.check_id == "E-03"]

    t2 = Transporte({"/api/contestacoes": Resposta(
        201, '{"protocolo":"CT-2026-001","prazo_dias":15}')})
    res2 = rodar(alvo(), "pse_active", t2, packs=("ethics",))
    assert not [f for f in res2["findings"] if f.check_id == "E-03"]


# ================================================== modo e habilitacao
def test_trabalho_a_nao_habilitado_nao_bloqueia(tmp_path):
    """Sem `target`: checks A ficam previstos-e-nao-habilitados, e o exit
    segue o Trabalho B."""
    out = tmp_path / "l.json"
    rc = main(["--path", str(FIX), "--config", str(FIX / "pse-config.yaml"),
               "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    nao_hab = {c["id"] for c in laudo["checks_nao_habilitados"]}
    assert CHECKS_A <= nao_hab
    assert all(c["motivo"] for c in laudo["checks_nao_habilitados"])
    assert not laudo["checks_indeterminados"]
    assert rc == 0, "Trabalho A ausente nao pode bloquear o Trabalho B"


def test_modo_passivo_nao_dispara_check_ativo():
    t = Transporte({"/api/erro": Resposta(200, "{}")})
    res = rodar(alvo(scope=("pse_passive",)), "pse_passive", t)
    nao_hab = ids(res, "checks_nao_habilitados")
    assert {"S-01", "S-02", "P-05", "P-11", "E-03"} <= nao_hab
    assert {"S-03", "E-01", "E-02"} <= set(res["checks_executados"])
    assert not any(c[1].startswith("/api/clientes/9f") for c in t.sondas)


def test_modo_inventory_nao_toca_a_rede():
    t = Transporte()
    res = rodar(alvo(), "pse_inventory", t)
    assert CHECKS_A <= ids(res, "checks_nao_habilitados")
    assert t.chamadas == []


@pytest.mark.mordida
def test_indeterminacao_do_trabalho_a_bloqueia_o_processo(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(json.dumps({"pse_suite": alvo(com_autorizacao=False)}))
    rc = main(["--path", str(FIX), "--config", str(cfg), "--modo", "pse_passive",
               "--output", str(tmp_path / "l.json")])
    laudo = json.loads((tmp_path / "l.json").read_text(encoding="utf-8"))
    assert rc == EXIT_INDETERMINADO
    assert laudo["veredito"] == "indeterminado"
    assert laudo["artifact"]["modo"] == "pse_passive"


def test_laudo_carimba_a_atestacao_sem_segredo(tmp_path):
    cfg = tmp_path / "c.yaml"
    cfg.write_text(json.dumps({"pse_suite": alvo()}))
    main(["--path", str(FIX), "--config", str(cfg), "--modo", "pse_passive",
          "--output", str(tmp_path / "l.json")])
    bruto = (tmp_path / "l.json").read_text(encoding="utf-8")
    att = json.loads(bruto)["artifact"]["autorizacao"]
    assert att["attested_by"] == "dpo@exemplo.com"
    assert att["scope"] and att["expires"] and att["target_fingerprint"]
    assert "token-de-teste-a" not in bruto and "PSE_TOKEN_A" not in bruto
