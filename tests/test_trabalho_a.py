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
from pse.model import EXIT_ENTRADA_INVALIDA, EXIT_INDETERMINADO, EntradaInvalida
from pse.trabalho_a.cliente import Resposta

from helpers_alvo import (BASE, CHECKS_A, ROTA_B, TOKEN_A, UUID_B,
                          Transporte, alvo)

FIX = Path(__file__).parent / "fixtures" / "consumidor_bom"



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


# ==================================================== loopback: mudanca de regra
@pytest.mark.mordida
@pytest.mark.parametrize("url,aceita", [
    ("http://127.0.0.1:8000", True),
    ("http://localhost:8000", True),
    ("https://staging.exemplo.com", True),
    # A trava: casa o host de loopback EXATO, nunca por substring.
    ("http://127.0.0.1.atacante.com", False),
    ("http://localhost.atacante.com", False),
    ("http://meu-localhost.com", False),
    ("http://staging.exemplo.com", False),
    ("http://10.0.0.5", False),
])
def test_http_so_e_aceito_em_loopback(url, aceita):
    """MUDANCA DE REGRA declarada, para a camada dinamica poder ser provada
    contra um alvo REAL.

    A exigencia de https existe por UM motivo escrito: sonda em texto claro
    vaza o proprio token de teste na rede. Em loopback nao ha rede — o
    pacote nao passa por interface fisica, nao ha intermediario e nao ha o
    que capturar. A razao da regra nao alcanca o caso.

    Sem isto, o alvo de fixture (http://127.0.0.1) nao passaria pelo
    contrato, e a camada dinamica so teria prova contra objeto fabricado —
    exatamente o erro de tratar ambiente local como alvo respondendo.

    A excecao e ESTREITA de proposito, e e isso que este teste fixa:
    `127.0.0.1.atacante.com` NAO passa.
    """
    from pse.trabalho_a import autorizacao
    cfg = {"target": {"base_url": url, "environment": "staging"}}
    if aceita:
        autorizacao.validar_config(cfg, "pse_passive")
    else:
        with pytest.raises(EntradaInvalida) as e:
            autorizacao.validar_config(cfg, "pse_passive")
        assert "https" in str(e.value)


# ============================================ alvo local: o degrau local_target
def _att_local(**extra):
    return {"attested_by": "arquiteto@danzeroum", "scope": ["pse_passive"],
            "expires": "2030-01-01", **extra}


@pytest.mark.mordida
def test_loopback_sem_local_target_e_recusado():
    """O buraco que o degrau existe para fechar.

    Em 127.0.0.1 nao ha rede nem prova de posse a fazer — e e JUSTAMENTE por
    isso que o degrau precisa ser explicito. Sem ele, qualquer coisa que suba
    numa porta local viraria alvo sondavel sem registro, e o contrato
    perderia o sentido no unico lugar onde e mais facil burla-lo.
    """
    from pse.model import CheckIndeterminado
    from pse.trabalho_a import autorizacao
    cfg = {"target": {"base_url": "http://127.0.0.1:8080",
                      "environment": "staging",
                      "authorization": _att_local()}}
    autorizacao.validar_config(cfg, "pse_passive")     # config passa
    with pytest.raises(CheckIndeterminado) as e:       # a atestacao, nao
        autorizacao.validar_atestacao(cfg, "pse_passive")
    assert "local_target" in str(e.value)


def test_loopback_com_local_target_dispensa_o_fingerprint():
    """A porta do alvo local e efemera: um fingerprint que muda a cada
    execucao viraria burocracia que o operador cola sem ler."""
    from pse.trabalho_a import autorizacao
    cfg = {"target": {"base_url": "http://127.0.0.1:54321",
                      "environment": "staging",
                      "authorization": _att_local(local_target=True)}}
    autorizacao.validar_config(cfg, "pse_passive")
    att = autorizacao.validar_atestacao(cfg, "pse_passive")
    assert att["local_target"] is True


@pytest.mark.mordida
def test_local_target_em_alvo_publicado_e_entrada_invalida():
    """A fraude barata que o degrau NAO pode permitir: uma linha dispensando
    a prova de posse de um host que nao e seu."""
    from pse.trabalho_a import autorizacao
    cfg = {"target": {"base_url": "https://alvo-de-terceiro.example.org",
                      "environment": "staging",
                      "authorization": _att_local(local_target=True)}}
    with pytest.raises(EntradaInvalida) as e:
        autorizacao.validar_config(cfg, "pse_passive")
    assert "nao e loopback" in str(e.value).lower() or "NAO e loopback" in str(e.value)


@pytest.mark.mordida
def test_alvo_publicado_segue_exigindo_fingerprint():
    """O degrau local nao pode ter afrouxado o caminho normal."""
    from pse.model import CheckIndeterminado
    from pse.trabalho_a import autorizacao
    cfg = {"target": {"base_url": "https://staging.exemplo.com",
                      "environment": "staging",
                      "authorization": _att_local(target_fingerprint="errado")}}
    with pytest.raises(CheckIndeterminado) as e:
        autorizacao.validar_atestacao(cfg, "pse_passive")
    assert "target_fingerprint" in str(e.value)


@pytest.mark.mordida
def test_local_target_nao_dispensa_escopo_nem_prazo():
    """Alvo local continua sendo alvo: escopo e prazo valem igual. O degrau
    substitui a prova de POSSE, nao a autorizacao."""
    from pse.model import CheckIndeterminado
    from pse.trabalho_a import autorizacao
    base = {"base_url": "http://localhost:9000", "environment": "staging"}

    sem_ativo = {"target": {**base, "authorization": _att_local(local_target=True)}}
    with pytest.raises(CheckIndeterminado) as e:
        autorizacao.validar_atestacao(sem_ativo, "pse_active")
    assert "scope" in str(e.value)

    vencida = {"target": {**base, "authorization": _att_local(
        local_target=True, expires="2020-01-01")}}
    with pytest.raises(CheckIndeterminado) as e:
        autorizacao.validar_atestacao(vencida, "pse_passive")
    assert "vencida" in str(e.value)
