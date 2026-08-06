"""Fase 3 — os dois riscos novos, e os testes que os medem.

E-09 pode disparar um kill switch de verdade. E-06 pode rodar inferencia
sobre dado sensivel de titular real. Nenhum dos dois e um risco de veredito
errado: sao riscos de a AUDITORIA causar o dano que ela audita. Por isso os
testes que contam acionamentos e leituras valem mais que os de caminho feliz,
e vem primeiro neste arquivo.
"""
import json
from pathlib import Path

import pytest

from pse import limites
from pse.engine.runner import executar
from pse.model import EntradaInvalida
from pse.trabalho_a.cliente import Resposta

from helpers_alvo import Transporte, alvo

BOM = Path(__file__).parent / "fixtures" / "consumidor_bom"

ENDPOINTS_FASE3 = {
    "kill_switch_dry_run": "/api/kill-switch",
    "exportacao": "/api/exportacao",
    "log_auditoria": "/api/logs",
    "consentimento_protegido": "/api/perfil",
    "agregacao": "/api/relatorios/bairro",
    "listagem": "/api/clientes",
}


def alvo3(**kw):
    eps = dict(ENDPOINTS_FASE3)
    eps.update(kw.pop("endpoints", {}) or {})
    return alvo(endpoints=eps, **kw)


def rodar(config, modo, transporte, packs=("privacy", "security", "ethics")):
    return executar(BOM, set(packs), config, modo=modo, transporte=transporte)


# ==================================================== E-09: nunca dispara real
def _acionamentos_reais(transporte, corpos):
    """Requisicao ao kill switch SEM marca de simulacao — o que nao pode existir."""
    reais = []
    for (metodo, rota), corpo in zip(transporte.sondas, corpos):
        if "kill-switch" not in rota:
            continue
        marcado = isinstance(corpo, dict) and (corpo.get("dry_run") is True
                                               or corpo.get("simulacao") is True)
        if not marcado:
            reais.append((metodo, rota, corpo))
    return reais


class TransporteKill(Transporte):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.corpos = []

    def enviar(self, metodo, url, headers, corpo, timeout):
        if "/health" not in url:
            self.corpos.append(json.loads(corpo) if corpo else None)
        return super().enviar(metodo, url, headers, corpo, timeout)


@pytest.mark.mordida
def test_e09_confirma_simulacao_sem_acionar_nada():
    t = TransporteKill({"/api/kill-switch": Resposta(
        200, '{"dry_run":true,"efeito":["fila-decisao","score-online"]}')})
    res = rodar(alvo3(), "pse_active", t, packs=("ethics",))
    assert not [f for f in res["findings"] if f.check_id == "E-09"]
    assert _acionamentos_reais(t, t.corpos) == [], "kill switch acionado de verdade"


@pytest.mark.mordida
def test_e09_sem_dry_run_e_indeterminado_e_nao_tenta_de_novo():
    """Alvo recusa a simulacao: a suite NAO descobre 'na marra' se o switch
    funciona. Uma retentativa sem dry-run apareceria na contagem."""
    t = TransporteKill({"/api/kill-switch": Resposta(404, "{}")})
    res = rodar(alvo3(), "pse_active", t, packs=("ethics",))
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "E-09" in motivos and "nao tenta acionamento real" in motivos["E-09"]
    assert _acionamentos_reais(t, t.corpos) == []
    assert len([c for c in t.sondas if "kill-switch" in c[1]]) == 1


@pytest.mark.mordida
def test_e09_aceito_sem_confirmar_simulacao_e_indeterminado():
    """200 mudo nao prova que simulou. A duvida aqui bloqueia."""
    t = TransporteKill({"/api/kill-switch": Resposta(200, '{"status":"ok"}')})
    res = rodar(alvo3(), "pse_active", t, packs=("ethics",))
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "E-09" in motivos and "nao confirmou que SIMULOU" in motivos["E-09"]
    assert _acionamentos_reais(t, t.corpos) == []


@pytest.mark.pse_ethics
def test_e09_simula_mas_nao_declara_efeito():
    t = TransporteKill({"/api/kill-switch": Resposta(200, '{"dry_run":true}')})
    res = rodar(alvo3(), "pse_active", t, packs=("ethics",))
    e09 = [f for f in res["findings"] if f.check_id == "E-09"]
    assert e09 and e09[0].severidade.value == "ALTO"
    assert _acionamentos_reais(t, t.corpos) == []


# ==================================================== E-06: nunca infere
@pytest.mark.mordida
def test_e06_sem_dataset_e_indeterminado_e_nao_le_nada(tmp_path, monkeypatch):
    """Dataset e insumo declarado. Sem declaracao: indeterminado (20), e
    nenhum arquivo do alvo e aberto em busca de 'algum' dataset."""
    abertos = []
    original = Path.open

    def espiao(self, *a, **kw):
        abertos.append(str(self))
        return original(self, *a, **kw)

    (tmp_path / "ml.py").write_text(
        "from sklearn.linear_model import LogisticRegression\n")
    (tmp_path / "eval.parquet").write_bytes(b"nao-declarado")
    monkeypatch.setattr(Path, "open", espiao)
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated"})
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "E-06" in motivos
    assert "dataset de avaliacao ausente" in motivos["E-06"]
    assert not any("eval.parquet" in a for a in abertos), (
        "a suite foi procurar dataset que ninguem declarou")


@pytest.mark.mordida
def test_e06_indeterminado_bloqueia_o_processo(tmp_path):
    from pse.cli import main
    (tmp_path / "ml.py").write_text("from sklearn.svm import SVC\n")
    cfg = tmp_path / "c.yaml"
    cfg.write_text("pse_suite:\n  decision_making: automated\n")
    out = tmp_path / "l.json"
    rc = main(["--path", str(tmp_path), "--packs", "ethics",
               "--config", str(cfg), "--output", str(out)])
    assert rc == 20
    assert json.loads(out.read_text())["veredito"] == "indeterminado"


@pytest.mark.pse_ethics
def test_e06_relatorio_stale_e_achado(tmp_path):
    import shutil
    for f in ("eval.csv", "fairness-report.yaml", "pse-config.yaml"):
        shutil.copy(BOM / f, tmp_path / f)
    (tmp_path / "eval.csv").write_text("grupo,alvo\nA,1\n")   # dataset mudou
    cfg = {"decision_making": "automated",
           "packs": {"ethics": {"fairness_dataset": "eval.csv",
                                "fairness_report": "fairness-report.yaml"}}}
    res = executar(tmp_path, {"ethics"}, cfg)
    e06 = [f for f in res["findings"] if f.check_id == "E-06"]
    assert e06 and "stale" in e06[0].titulo


@pytest.mark.pse_ethics
def test_e06_numero_sem_condicoes_reprova(tmp_path):
    import shutil
    shutil.copy(BOM / "eval.csv", tmp_path / "eval.csv")
    (tmp_path / "rel.yaml").write_text(
        "modelo_versao: '1'\ndataset_fingerprint: " + "0" * 64 +
        "\nmedido_em: hoje\ngrupos:\n  - {nome: A, n: 2, dpd: 0.0}\n")
    cfg = {"decision_making": "automated",
           "packs": {"ethics": {"fairness_dataset": "eval.csv",
                                "fairness_report": "rel.yaml"}}}
    res = executar(tmp_path, {"ethics"}, cfg)
    e06 = [f for f in res["findings"] if f.check_id == "E-06"]
    assert e06 and "invalido" in e06[0].titulo
    assert "condicoes" in " ".join(f.descricao for f in e06)


@pytest.mark.pse_ethics
def test_e06_dpd_acima_do_teto():
    cfg = {"decision_making": "automated",
           "thresholds": {"dpd_max_delta": 0.005},
           "packs": {"ethics": {"fairness_dataset": "eval.csv",
                                "fairness_report": "fairness-report.yaml"}}}
    res = executar(BOM, {"ethics"}, cfg)
    e06 = [f for f in res["findings"] if f.check_id == "E-06"]
    assert e06 and "acima do teto" in e06[0].titulo


# ==================================================== thresholds da regua
@pytest.mark.mordida
@pytest.mark.parametrize("thresholds,trecho", [
    ({"k_anonymity_min": 2}, "abaixo do piso"),
    ({"dpd_max_delta": 0.5}, "acima do teto"),
    ({"inventado": 1}, "threshold desconhecido"),
])
def test_consumidor_nao_afrouxa_a_regua(thresholds, trecho):
    with pytest.raises(EntradaInvalida) as e:
        limites.validar({"thresholds": thresholds})
    assert trecho in str(e.value)


def test_consumidor_pode_apertar_a_regua():
    limites.validar({"thresholds": {"k_anonymity_min": 20, "dpd_max_delta": 0.01}})
    assert limites.valor({"thresholds": {"k_anonymity_min": 20}}, "k_anonymity_min") == 20


# ==================================================== P-10
@pytest.mark.pse_privacy
def test_p10_export_sem_hash_e_achado_e_pacote_nao_vaza():
    pacote = json.dumps({"itens": [
        {"cpf": "529.982.247-25", "email": "maria@empresa.com.br"}]})
    t = Transporte({"/api/exportacao": Resposta(200, pacote)})
    res = rodar(alvo3(), "pse_active", t, packs=("privacy",))
    p10 = [f for f in res["findings"] if f.check_id == "P-10"]
    assert p10 and "integridade" in p10[0].descricao

    bruto = json.dumps(p10[0].trace, ensure_ascii=False)
    assert "529.982.247-25" not in bruto and "maria@empresa.com.br" not in bruto
    assert "<omitido:" in bruto, "o pacote exportado precisa ser omitido do trace"
    assert p10[0].trace["resposta"]["chaves_presentes"] == ["itens"]


@pytest.mark.pse_privacy
def test_p10_export_integro_nao_e_achado():
    t = Transporte({"/api/exportacao": Resposta(200, json.dumps({
        "dados": [], "formato": "json", "gerado_em": "2026-08-06",
        "sha256": "a" * 64}))})
    res = rodar(alvo3(), "pse_active", t, packs=("privacy",))
    assert not [f for f in res["findings"] if f.check_id == "P-10"]


# ==================================================== S-07
@pytest.mark.pse_security
def test_s07_sem_x_purpose_atendido_e_achado():
    t = Transporte({
        "/api/clientes": Resposta(200, "[]"),
        "/api/logs": Resposta(200, json.dumps([{
            "ator": "u1", "acao": "read", "timestamp": "2026-08-06",
            "recurso": "c1", "finalidade": "cobranca"}]))})
    res = rodar(alvo3(), "pse_active", t, packs=("security",))
    s07 = [f for f in res["findings"] if f.check_id == "S-07"]
    assert len(s07) == 1 and "X-Purpose" in s07[0].titulo


@pytest.mark.pse_security
def test_s07_log_incompleto_e_achado_sem_gravar_token():
    t = Transporte({
        "/api/clientes": Resposta(428, "{}"),
        "/api/logs": Resposta(200, json.dumps([{
            "ator": "u1", "acao": "read", "timestamp": "2026-08-06",
            "recurso": "c1", "token": "Bearer token-de-teste-a"}]))})
    res = rodar(alvo3(), "pse_active", t, packs=("security",))
    s07 = [f for f in res["findings"] if f.check_id == "S-07"]
    assert len(s07) == 1 and "incompleto" in s07[0].titulo
    assert "para que" in s07[0].descricao
    bruto = json.dumps(s07[0].trace, ensure_ascii=False)
    assert "token-de-teste-a" not in bruto
    # O X-Purpose que a suite envia fica registrado; o Authorization, nunca.
    assert s07[0].trace["requisicao"]["headers"].get("X-Purpose") == "auditoria_pse"
    assert "Authorization" not in s07[0].trace["requisicao"]["headers"]


@pytest.mark.pse_security
def test_s07_conforme():
    t = Transporte({
        "/api/clientes": Resposta(428, "{}"),
        "/api/logs": Resposta(200, json.dumps([{
            "ator": "u1", "acao": "read", "timestamp": "2026-08-06",
            "recurso": "c1", "finalidade": "cobranca"}]))})
    res = rodar(alvo3(), "pse_active", t, packs=("security",))
    assert not [f for f in res["findings"] if f.check_id == "S-07"]


# ==================================================== P-07 / P-09 / S-05
@pytest.mark.pse_privacy
def test_p07_rota_protegida_responde_sem_consentimento():
    t = Transporte({"/api/perfil": Resposta(200, '{"perfil":{}}')})
    cfg = {**alvo3(), "consent_model_path": "consent-model.yaml"}
    res = rodar(cfg, "pse_active", t, packs=("privacy",))
    p07 = [f for f in res["findings"] if f.check_id == "P-07"]
    assert p07 and p07[0].severidade.value == "CRITICO"


@pytest.mark.pse_privacy
def test_p07_403_e_conforme():
    t = Transporte({"/api/perfil": Resposta(403, "{}")})
    cfg = {**alvo3(), "consent_model_path": "consent-model.yaml"}
    res = rodar(cfg, "pse_active", t, packs=("privacy",))
    assert not [f for f in res["findings"] if f.check_id == "P-07"]


@pytest.mark.pse_privacy
def test_p09_celula_rara_exposta():
    t = Transporte({"/api/relatorios": Resposta(
        200, '{"linhas":[{"bairro":"X","count":2},{"bairro":"Y","count":40}]}')})
    cfg = {**alvo3(), "consent_model_path": "consent-model.yaml"}
    res = rodar(cfg, "pse_active", t, packs=("privacy",))
    p09 = [f for f in res["findings"] if f.check_id == "P-09"]
    assert p09 and "count=2" in p09[0].descricao


@pytest.mark.pse_privacy
def test_p09_estatico_group_by_sem_having(tmp_path):
    (tmp_path / "rel.sql").write_text(
        "SELECT bairro, COUNT(*) FROM titulares GROUP BY bairro;\n")
    res = executar(tmp_path, {"privacy"}, {})
    p09 = [f for f in res["findings"] if f.check_id == "P-09"]
    assert p09 and p09[0].arquivo == "rel.sql" and p09[0].linha


@pytest.mark.pse_security
def test_s05_egresso_nao_declarado_e_pii_no_egresso(tmp_path):
    (tmp_path / "tp.yml").write_text(
        "integrations:\n"
        "  - name: sem-declaracao\n    hosts: [a.example.net]\n    dpa_signed: true\n"
        "  - name: com-cpf\n    hosts: [b.example.net]\n    dpa_signed: true\n"
        "    egress_fields: [cpf, id_pseudonimo]\n")
    res = executar(tmp_path, {"security"}, {"third_party_manifest": "tp.yml"})
    s05 = [f for f in res["findings"] if f.check_id == "S-05"]
    titulos = " ".join(f.titulo for f in s05)
    assert "sem payload de egresso declarado" in titulos
    assert "envia dado identificavel" in titulos
    assert all(f.linha for f in s05)


@pytest.mark.pse_security
def test_s05_declara_cobertura_parcial(tmp_path):
    (tmp_path / "tp.yml").write_text(
        "integrations:\n  - name: ok\n    hosts: [a.example.net]\n"
        "    egress_fields: [id_pseudonimo]\n")
    res = executar(tmp_path, {"security"}, {"third_party_manifest": "tp.yml"})
    assert "S-05" in res["relatorios"]["cobertura_parcial"]
    assert "proxy" in res["relatorios"]["cobertura_parcial"]["S-05"]


# ==================================================== E-10
@pytest.mark.pse_ethics
def test_e10_inferencia_sem_incerteza(tmp_path):
    (tmp_path / "s.py").write_text(
        "def decidir(modelo, x):\n    return modelo.predict(x)\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated",
                                          "packs": {"ethics": {
                                              "fairness_dataset": None}}})
    e10 = [f for f in res["findings"] if f.check_id == "E-10"]
    assert e10 and e10[0].severidade.value == "MEDIO"


@pytest.mark.pse_ethics
def test_e10_com_probabilidade_nao_e_achado(tmp_path):
    (tmp_path / "s.py").write_text(
        "def decidir(modelo, x):\n"
        "    p = modelo.predict_proba(x)\n"
        "    return {'score': modelo.predict(x), 'confianca': p.max()}\n")
    res = executar(tmp_path, {"ethics"}, {"decision_making": "automated"})
    assert not [f for f in res["findings"] if f.check_id == "E-10"]


# ==================================================== sem atestacao
@pytest.mark.mordida
def test_checks_fase3_sem_atestacao_ficam_indeterminados():
    t = Transporte()
    res = rodar(alvo3(com_autorizacao=False), "pse_active", t)
    indet = {c["id"] for c in res["checks_indeterminados"]}
    assert {"E-09", "P-10", "S-07", "P-07", "P-09"} <= indet
    assert t.chamadas == [], "requisicao emitida sem atestacao"
