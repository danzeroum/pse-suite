"""A matriz: pilar × domínio.

O pilar responde *que valor está em jogo* (privacidade, segurança, ética); o
domínio responde *onde isso se manifesta no sistema* (frontend, api, backend,
data, ai). São ortogonais de propósito: um time de frontend quer
`--domain frontend` sem deixar de ser auditado nos três pilares, e um DPO quer
`--pilar privacy` atravessando todos os estratos. A matriz serve aos dois sem
duplicar check nenhum — nenhum dos 33 mudou de comportamento para isto existir.
"""
import json
from pathlib import Path

import pytest

from pse import catalogo
from pse.cli import main
from pse.engine.registry import CHECKS
from pse.engine.runner import _carregar_checks, executar

FIX = Path(__file__).parent / "fixtures"
RUIM = FIX / "consumidor_ruim"
CFG = RUIM / "pse-config.yaml"


def test_todo_check_declara_dominio():
    """Completude do catálogo na segunda dimensão. Um check sem `domain`
    seria invisível a qualquer filtro por estrato — e invisível não é
    o mesmo que ausente, mas o consumidor não teria como notar."""
    sem = [cid for cid in catalogo.CATALOGO if not catalogo.dominios(cid)]
    assert not sem, f"checks sem domain declarado: {sem}"


def test_dominios_declarados_sao_do_vocabulario():
    invalidos = {(cid, d) for cid in catalogo.CATALOGO
                 for d in catalogo.dominios(cid) if d not in catalogo.DOMINIOS}
    assert not invalidos, f"domínio fora do vocabulário: {sorted(invalidos)}"


def test_registro_carrega_o_dominio():
    _carregar_checks()
    for cid, meta in CHECKS.items():
        assert meta["domain"] == catalogo.dominios(cid)


def test_a_matriz_cruza_de_verdade():
    """privacy × data é um subconjunto próprio dos dois eixos: se o
    cruzamento devolvesse a união, o filtro seria decorativo."""
    privacy = set(catalogo.implementados({"privacy"}))
    data = set(catalogo.implementados(None, ["data"]))
    cruz = set(catalogo.implementados({"privacy"}, ["data"]))
    assert cruz == privacy & data
    assert cruz < privacy and cruz < data


@pytest.mark.parametrize("flags,esperado", [
    # FE-01/FE-02 sao do pilar privacy com prefixo de DOMINIO: a partir da
    # matriz, o prefixo do ID nao responde mais pelo pilar — o catalogo responde.
    (["--pilar", "privacy"],
     lambda ids: {"P-01", "FE-01", "FE-02"} <= set(ids) and "S-06" not in ids),
    (["--domain", "data"], lambda ids: "P-02" in ids and "S-06" not in ids),
    (["--packs", "data"], lambda ids: "P-02" in ids and "S-06" not in ids),
    (["--pilar", "privacy", "--domain", "data"],
     lambda ids: set(ids) <= {"P-02", "P-03", "P-04", "P-07", "P-08", "P-09"}),
])
def test_cli_filtra_por_pilar_dominio_e_cruzamento(tmp_path, flags, esperado):
    out = tmp_path / "l.json"
    main(["--path", str(RUIM), "--config", str(CFG), "--output", str(out)] + flags)
    ids = json.loads(out.read_text(encoding="utf-8"))["checks_executados"]
    assert esperado(ids), ids


def test_packs_aceita_o_vocabulario_que_o_consumidor_conhece(tmp_path):
    """`--packs frontend` pede um domínio. A suite entende: o consumidor não
    deveria precisar saber em que dimensão a palavra que ele conhece foi
    arquivada."""
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    main(["--path", str(RUIM), "--config", str(CFG), "--packs", "data",
          "--output", str(a)])
    main(["--path", str(RUIM), "--config", str(CFG), "--domain", "data",
          "--output", str(b)])
    ja, jb = (json.loads(p.read_text(encoding="utf-8")) for p in (a, b))
    assert ja["checks_executados"] == jb["checks_executados"]
    assert ja["dominios"] == jb["dominios"] == ["data"]


def test_termo_desconhecido_e_entrada_invalida(tmp_path):
    assert main(["--path", str(RUIM), "--packs", "nao-existe"]) == 30
    assert main(["--path", str(RUIM), "--domain", "mobile"]) == 30
    assert main(["--path", str(RUIM), "--pilar", "privacidade"]) == 30


@pytest.mark.mordida
def test_selecao_vazia_nao_compra_um_verde(tmp_path):
    """Pedir um recorte que não alcança check nenhum não pode sair conforme:
    seria verde por não ter olhado, com o agravante de o consumidor achar
    que pediu uma auditoria."""
    # ethics x frontend continua vazio (FE-* sao privacy e security).
    rc = main(["--path", str(RUIM), "--config", str(CFG),
               "--pilar", "ethics", "--domain", "frontend"])
    assert rc == 30


@pytest.mark.mordida
def test_guarda_so_roda_quando_ha_o_que_guardar():
    """E-00 decide o escopo da ética, então acompanha o PACK, não o próprio
    domínio: num recorte `api` a ética tem E-01/E-03/E-09, e deixar de gatear
    isso seria pior que o ruído. Onde a ética não tem check nenhum, porém,
    rodar a guarda é ruído puro — quem pede `frontend` não quer saber se o
    alvo tem IA."""
    cfg = {"catalog_path": "catalog.yaml", "decision_making": "automated"}

    # `frontend`: a etica nao tem check aqui -> guarda nao roda, nem executada
    # nem pulada. Silencio correto, porque nao havia nada a gatear.
    res = executar(RUIM, {"privacy", "security", "ethics"}, cfg,
                   doms=["frontend"])
    assert "E-00" not in res["checks_executados"]
    assert "E-00" not in {c["id"] for c in res["checks_pulados"]}

    # `api`: a etica TEM checks -> a guarda roda, mesmo sendo de dominio `ai`.
    res_api = executar(RUIM, {"ethics"}, cfg, doms=["api"])
    assert "E-00" in res_api["checks_executados"]
    assert {"E-01", "E-03", "E-09"} & set(
        res_api["checks_executados"] +
        [c["id"] for c in res_api["checks_nao_habilitados"]])


def test_laudo_carrega_as_duas_dimensoes(tmp_path):
    out = tmp_path / "l.json"
    main(["--path", str(RUIM), "--config", str(CFG), "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert laudo["dominios"] == list(catalogo.DOMINIOS)
    por_dom = laudo["cobertura"]["por_dominio"]
    assert set(por_dom) == set(catalogo.DOMINIOS)
    for f in laudo["findings"]:
        assert f["domain"], f"finding {f['check_id']} sem domínio no laudo"
        assert f["domain"] == catalogo.dominios(f["check_id"])


def test_frontend_existe_como_estrato_declarado():
    """Antes de ter check, o domínio já tem de existir no vocabulário — é o
    que permite ao laudo dizer `frontend: 0` em vez de omitir o estrato e
    deixar o time achar que foi auditado."""
    assert "frontend" in catalogo.DOMINIOS
