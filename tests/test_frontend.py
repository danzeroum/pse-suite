"""P-13, P-14, S-09 — o domínio frontend, ancorado em AST de verdade.

O material de fundação do frontend propõe `grep -rn "consent\\|token\\|..."`.
Grep é ótimo para achar ONDE olhar e péssimo como check: é literalmente o
D-01, a menção passando por fato. Um `// consent default on` num comentário
casaria; um `<input checked />` sem handler, escrito em três linhas, não.

Por isso os três nascem sobre uma AST real (tree-sitter, gramáticas
javascript e tsx). E por isso o risco desta virada não é errar um veredito:
é (a) reintroduzir o grep-de-menção num domínio inteiro e (b) falso-positivo
CRÍTICO em P-13/P-14 ensinar o time de frontend a ignorar o pack inteiro no
primeiro dia. Os testes que provam que o caso CORRETO não dispara vêm
primeiro, e são os que mais importam.
"""
import json
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar

FIX = Path(__file__).parent / "fixtures"
RUIM = FIX / "consumidor_frontend_ruim"
BOM = FIX / "consumidor_frontend_bom"
CFG = {"decision_making": "none"}

pytestmark = pytest.mark.pse_frontend


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


def rodar(caminho, cfg=None):
    return executar(caminho, {"privacy", "security", "ethics"}, cfg or CFG,
                    doms=["frontend"])


def escrever(tmp_path, nome, conteudo):
    (tmp_path / nome).write_text(conteudo, encoding="utf-8")
    return rodar(tmp_path)


# ==================================================== o caso correto não dispara
def test_fixture_conforme_nao_dispara_nenhum_dos_tres():
    """O teste que mais importa: falso-positivo em CRÍTICO num pack novo
    ensina o time a ignorá-lo antes de ele provar qualquer valor."""
    res = rodar(BOM)
    for cid in ("P-13", "P-14", "S-09"):
        assert not acha(res, cid), [
            (f.arquivo, f.linha, f.snippet) for f in acha(res, cid)]
        assert cid in res["checks_executados"]


# ==================================================== P-13 (consentimento)
def test_p13_checkbox_pre_marcado_sem_handler(tmp_path):
    res = escrever(tmp_path, "C.jsx",
                   'export const C = () => <label>Aceito o marketing'
                   '<input type="checkbox" name="consent_ads" checked /></label>;')
    fe = acha(res, "P-13")
    assert fe and fe[0].severidade.value == "CRITICO"
    assert fe[0].arquivo == "C.jsx" and fe[0].linha
    assert "Art. 7" in fe[0].base_legal or "Art. 8" in fe[0].base_legal


def test_p13_escolha_registrada_nao_dispara(tmp_path):
    """Nasce ligado porque REFLETE escolha do titular, com handler. Este é o
    padrão correto — puni-lo seria punir quem acertou."""
    res = escrever(tmp_path, "C.jsx",
                   'export const C = ({c, set}) => <label>Aceito o marketing'
                   '<input type="checkbox" name="consent_ads" '
                   'checked={c.marketing} onChange={set} /></label>;')
    assert not acha(res, "P-13")


def test_p13_comentario_nao_liga_nem_desliga(tmp_path):
    """`// consent default on` é exatamente o que um grep casaria."""
    res = escrever(tmp_path, "C.jsx",
                   "// consent default on\n"
                   "// <input type='checkbox' checked /> consentimento\n"
                   "export const C = () => <div>oi</div>;")
    assert not acha(res, "P-13"), "comentário virou achado — grep entrou pela porta"


def test_p13_checkbox_nao_relacionado_a_consentimento_nao_dispara(tmp_path):
    res = escrever(tmp_path, "C.jsx",
                   'export const C = () => <input type="checkbox" '
                   'name="lembrar_filtro" checked />;')
    assert not acha(res, "P-13")


def test_p13_desligado_por_default_e_conforme(tmp_path):
    res = escrever(tmp_path, "C.jsx",
                   'export const C = () => <label>Aceito cookies'
                   '<input type="checkbox" name="consentimento" /></label>;')
    assert not acha(res, "P-13")


# ==================================================== P-14
@pytest.mark.parametrize("codigo,esperado", [
    ('localStorage.setItem("cpf", user.cpf);', True),
    ('sessionStorage.setItem("email", u.email);', True),
    ('const url = base + "?email=" + user.email;', True),
    ('const url = `/r?cpf=${user.cpf}`;', True),
    ('localStorage.setItem("cpf", mask(user.cpf));', False),
    ('localStorage.setItem("tema", "escuro");', False),
    ('const url = base + "?ref=" + user.idPseudonimo;', False),
])
def test_p14_limites(tmp_path, codigo, esperado):
    res = escrever(tmp_path, "a.js", f"export function f(user, u, base) {{ {codigo} }}")
    assert bool(acha(res, "P-14")) is esperado, codigo


def test_p14_e_critico_com_endereco(tmp_path):
    res = escrever(tmp_path, "a.js",
                   'export function f(user) {\n  localStorage.setItem("cpf", user.cpf);\n}')
    fe = acha(res, "P-14")
    assert fe and fe[0].severidade.value == "CRITICO"
    assert fe[0].arquivo == "a.js" and fe[0].linha == 2


def test_p14_string_em_comentario_nao_conta(tmp_path):
    res = escrever(tmp_path, "a.js",
                   '// localStorage.setItem("cpf", user.cpf) -- nunca faca isso\n'
                   'export const f = () => null;')
    assert not acha(res, "P-14")


# ==================================================== S-09
@pytest.mark.parametrize("codigo,esperado", [
    ('localStorage.setItem("token", jwt);', True),
    ('sessionStorage.setItem("refresh_token", r);', True),
    ('document.cookie = "token=" + jwt;', True),
    ('localStorage.setItem("tema", "escuro");', False),
    ('fetch(url, { credentials: "include" });', False),
])
def test_s09_limites(tmp_path, codigo, esperado):
    res = escrever(tmp_path, "a.js", f"export function f(jwt, r, url) {{ {codigo} }}")
    assert bool(acha(res, "S-09")) is esperado, codigo


def test_s09_e_alto(tmp_path):
    res = escrever(tmp_path, "a.js", 'export const f = jwt => localStorage.setItem("token", jwt);')
    fe = acha(res, "S-09")
    assert fe and fe[0].severidade.value == "ALTO"
    assert "Art. 46" in fe[0].base_legal


# ==================================================== AST de verdade
@pytest.mark.mordida
def test_arquivo_que_nao_parseia_e_indeterminado(tmp_path):
    """Sem AST não há decisão pelo fato — e não decidir bloqueia."""
    (tmp_path / "quebrado.tsx").write_text(
        "export const C = () => <div><span></div>;\n", encoding="utf-8")
    res = rodar(tmp_path)
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert {"P-13", "P-14", "S-09"} <= set(motivos)
    assert all("quebrado.tsx" in m for m in motivos.values())
    assert not res["findings"]


@pytest.mark.mordida
def test_indeterminacao_do_frontend_bloqueia(tmp_path):
    (tmp_path / "quebrado.jsx").write_text("const x = <a", encoding="utf-8")
    assert main(["--path", str(tmp_path), "--domain", "frontend",
                 "--output", str(tmp_path / "l.json")]) == 20


def test_parser_cobre_as_quatro_extensoes(tmp_path):
    for ext in ("js", "jsx", "ts", "tsx"):
        (tmp_path / f"a.{ext}").write_text(
            'export function f(u) { localStorage.setItem("cpf", u.cpf); }\n',
            encoding="utf-8")
    res = rodar(tmp_path)
    arquivos = {f.arquivo for f in acha(res, "P-14")}
    assert arquivos == {"a.js", "a.jsx", "a.ts", "a.tsx"}, arquivos


# ==================================================== integração
def test_fixture_ruim_dispara_os_tres():
    res = rodar(RUIM)
    for cid in ("P-13", "P-14", "S-09"):
        assert acha(res, cid), cid
    assert all(f.arquivo.startswith("src/") and f.linha
               for cid in ("P-13", "P-14", "S-09") for f in acha(res, cid))


@pytest.mark.mordida
def test_gate_morde_no_frontend(tmp_path):
    rc = main(["--path", str(RUIM), "--domain", "frontend",
               "--output", str(tmp_path / "l.json")])
    assert rc == 10
    laudo = json.loads((tmp_path / "l.json").read_text(encoding="utf-8"))
    assert laudo["dominios"] == ["frontend"]
    for f in laudo["findings"]:
        assert f["domain"] == ["frontend"]


def test_catalogo_frontend_no_lugar():
    from pse import catalogo
    assert len(catalogo.CATALOGO) == 52
    assert catalogo.previstos() == []
    # 3 estáticos (P-13/P-14/S-09) + 3 dinâmicos (P-22/S-17/P-23). O estrato
    # `frontend` é o único auditado nas duas camadas: é onde o contrato e a
    # observação se encontram, e é por isso que os pares de correlação
    # (P-14×P-23, S-09×S-17) moram aqui.
    assert catalogo.por_dominio()["frontend"] == 6
    for cid, pilar in (("P-13", "privacy"), ("P-14", "privacy"),
                       ("S-09", "security")):
        m = catalogo.meta(cid)
        assert m["pack"] == pilar and m["domain"] == ["frontend"]
        assert m["canonical_mutation"] and m["base_legal"]


@pytest.mark.mordida
def test_repo_backend_nao_e_afetado():
    """A virada não pode mexer no que já funcionava: os checks de backend
    continuam cegos a .jsx e o gate deles segue idêntico."""
    res = executar(FIX / "consumidor_bom", {"privacy", "security", "ethics"},
                   {"catalog_path": "catalog.yaml", "decision_making": "automated",
                    "lineage_path": "lineage.jsonl",
                    "consent_model_path": "consent-model.yaml",
                    "packs": {"ethics": {"fairness_dataset": "eval.csv",
                                         "fairness_report": "fairness-report.yaml"}}})
    assert not res["findings"]
