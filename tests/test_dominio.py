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
    # P-13/P-14 sao do pilar privacy com prefixo de DOMINIO: a partir da
    # matriz, o prefixo do ID nao responde mais pelo pilar — o catalogo responde.
    (["--pilar", "privacy"],
     lambda ids: {"P-01", "P-13", "P-14"} <= set(ids) and "S-06" not in ids),
    (["--domain", "data"], lambda ids: "P-02" in ids and "S-06" not in ids),
    (["--packs", "data"], lambda ids: "P-02" in ids and "S-06" not in ids),
    # P-18 e P-19 sao multi-dominio: nasceram olhando o backend e inspecionam
    # artefato de dados (o catalogo, o log de eventos). Entram no cruzamento
    # por isso — e a matriz registra que NAO nasceram do estrato `data`.
    (["--pilar", "privacy", "--domain", "data"],
     lambda ids: set(ids) <= {"P-02", "P-03", "P-04", "P-07", "P-08", "P-09",
                              "P-18", "P-19"}),
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


# ==================================================== o prefixo responde pelo pilar
def test_prefixo_do_id_codifica_o_pilar():
    """Regra estrutural, não estética: das duas dimensões, só o pilar é
    univalorado. Um check pertence a UM pilar e pode pertencer a VÁRIOS
    domínios (S-07 é api+backend). O prefixo é rígido e único, então tem de
    carregar o que também é único; o multivalorado vive em `domain`, que é
    lista. Codificar domínio no prefixo — como `FE-*` fazia — é errar qual
    das duas vai no lugar rígido, e o erro só aparece no primeiro check que
    pertencer a dois estratos.
    """
    assert catalogo.incoerencias_de_prefixo() == [], (
        "ID com prefixo que não corresponde ao pilar declarado: "
        f"{catalogo.incoerencias_de_prefixo()}")


def test_nenhum_prefixo_fora_de_pse():
    fora = sorted({catalogo.prefixo(cid) for cid in catalogo.CATALOGO}
                  - set(catalogo.PREFIXO_DO_PILAR.values()))
    assert not fora, (
        f"prefixo(s) fora do vocabulário de pilares: {fora}. Domínio nunca "
        f"vai no prefixo — vai em `domain`.")


@pytest.mark.mordida
@pytest.mark.parametrize("id_hipotetico,pack", [
    ("FE-99", "privacy"),   # domínio no prefixo, a tentação que já aconteceu
    ("AP-01", "security"),  # a próxima tentação: pacote de API
    ("MB-01", "privacy"),   # e a seguinte: mobile
    ("P-99", "security"),   # prefixo certo, pilar errado
])
def test_prefixo_de_dominio_e_barrado(monkeypatch, id_hipotetico, pack):
    """A trava tem de IMPEDIR a regressão, não só corrigi-la uma vez. Sem
    isto, `AP-*` volta no pacote de API e ninguém percebe até o consumidor
    referenciar o ID errado num relatório."""
    monkeypatch.setitem(catalogo.CATALOGO, id_hipotetico,
                        {"pack": pack, "domain": ["api"], "titulo": "t",
                         "status": "implementado"})
    incoerentes = {c for c, _, _ in catalogo.incoerencias_de_prefixo()}
    assert id_hipotetico in incoerentes


@pytest.mark.mordida
def test_registro_recusa_prefixo_de_dominio(monkeypatch):
    """A regra mora num lugar só (o validador do catálogo), e o registro a
    consulta — nenhum check a repete."""
    from pse.engine.registry import CheckNaoCatalogado, check
    monkeypatch.setitem(catalogo.CATALOGO, "FE-99",
                        {"pack": "privacy", "domain": ["frontend"],
                         "titulo": "t", "status": "implementado"})
    with pytest.raises(CheckNaoCatalogado) as e:
        check("FE-99", "privacy", "t")(lambda ctx: [])
    assert "prefixo" in str(e.value).lower()


def test_dominio_e_multivalorado_e_o_pilar_nao():
    """A assimetria que justifica a regra, verificada no catálogo real."""
    multi = [cid for cid in catalogo.CATALOGO if len(catalogo.dominios(cid)) > 1]
    assert multi, "nenhum check multi-domínio: a premissa da regra sumiu"
    for cid in catalogo.CATALOGO:
        assert isinstance(catalogo.meta(cid)["pack"], str), (
            f"{cid}: pilar virou lista — a regra do prefixo deixa de valer")


# ==================================================== o mapa não pode envelhecer
def test_matriz_versionada_bate_com_o_catalogo():
    """`docs/matriz-dominio.md` é gerado. Um mapa mantido à mão diverge do
    território no primeiro check novo — e mapa errado é pior que mapa nenhum,
    porque parece confiável."""
    from pse import matriz
    versionado = (Path(__file__).resolve().parent.parent /
                  "docs" / "matriz-dominio.md").read_text(encoding="utf-8")
    assert versionado == matriz.gerar(), (
        "matriz-dominio.md desatualizada: rode "
        "`python -m pse.matriz > docs/matriz-dominio.md`")


def test_toda_celula_vazia_tem_leitura_declarada():
    """Buraco sem resposta é buraco escondido. Dizer 'não se aplica' ou
    'falta check' é julgamento, e julgamento tem de estar assinado."""
    from pse import matriz
    vazias = [(p, d) for p in matriz.PILARES for d in catalogo.DOMINIOS
              if not catalogo.implementados({p}, [d])]
    sem_leitura = [c for c in vazias if c not in matriz.LEITURA_DOS_BURACOS]
    assert not sem_leitura, (
        f"célula(s) vazia(s) sem leitura declarada em pse/matriz.py: "
        f"{sem_leitura}")


def test_nenhum_dominio_do_vocabulario_fica_sem_check():
    """Domínio declarado e sem nenhum check é pior que domínio inexistente:
    o consumidor filtra por ele e recebe exit 30 sem entender por quê."""
    vazios = [d for d in catalogo.DOMINIOS if not catalogo.implementados(None, [d])]
    assert not vazios, (
        f"domínio(s) no vocabulário sem nenhum check: {vazios}. Ou nascem "
        f"checks fundadores, ou o domínio sai do vocabulário.")
