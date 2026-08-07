"""O estrato web e a maior fatia do alvo — e um arquivo ilegivel apagava o
veredito de todos os outros.

O mapa de cobertura tinha dois defeitos que se reforcavam, e nenhum dos dois
era uma mentira explicita:

  1. Ele comparava ROTULOS DE LINGUAGEM. `TypeScript` e `TypeScript/TSX` sao
     rotulos separados no bloco `alcance` (ferramentas diferentes), entao
     compara-los um a um contra `Rust` dividia o front em dois e fazia o
     motor parecer a maior fatia por numero de arquivos. Somando o estrato,
     o front ganha: 174 contra 137.

  2. Os checks de frontend chamavam o parser DENTRO do laco, e o primeiro
     arquivo que nenhuma gramatica alcancasse derrubava o check INTEIRO. No
     btv eram tres arquivos — e os outros 171, que parseavam sem problema
     nenhum, ficavam sem veredito. O gate funcionava (exit 20) e a
     informacao se perdia: uma violacao real nos 171 nunca seria reportada.

O segundo e o mais caro dos dois, porque produz FALSO-NEGATIVO por causa de
fail-closed — nem verde honesto, nem informacao.
"""
import json
import tempfile
from pathlib import Path

import pytest

from pse import cobertura
from pse.engine import jsast, scan
from pse.engine.runner import executar
from pse.model import CheckIndeterminado

RAIZ = Path(__file__).resolve().parent.parent
MEDICAO = RAIZ / "aceites" / "btv-medicao.json"
DOC = RAIZ / "docs" / "cobertura-btv.md"
FRONTEND = ("P-13", "P-14", "S-09")


def _dados():
    return json.loads(MEDICAO.read_text(encoding="utf-8"))


def escrever(arquivos, cfg=None):
    d = Path(tempfile.mkdtemp())
    for nome, corpo in arquivos.items():
        alvo = d / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return executar(d, {"privacy", "security"}, cfg or {})


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


# ============================================ .tsx e parseado de verdade
# O risco silencioso que a tarefa nomeou: se o parser cobrisse `.ts` e nao
# `.tsx`, metade do front do btv passaria como nao-auditada sem ninguem ver.

@pytest.mark.parametrize("ext", [".ts", ".tsx", ".jsx", ".js", ".mjs", ".cjs"])
def test_a_extensao_esta_no_conjunto_do_parser(ext):
    assert ext in jsast.EXTS


def test_tsx_com_pii_na_url_dispara_p14():
    """A prova de que `.tsx` e parseado, e nao so listado. Um teste que so
    olhasse `EXTS` passaria mesmo se a gramatica de TSX nunca carregasse."""
    res = escrever({"src/Tela.tsx":
                    "export function Tela({ cpf }: { cpf: string }) {\n"
                    "  const url = `/api/busca?cpf=${cpf}`;\n"
                    "  fetch(url);\n"
                    "  return <div>{cpf}</div>;\n"
                    "}\n"})
    assert acha(res, "P-14"), "PII na URL dentro de um .tsx nao disparou"


def test_tsx_com_token_no_storage_dispara_s09():
    res = escrever({"src/Login.tsx":
                    "export function Login() {\n"
                    "  const salvar = (t: string) =>\n"
                    "    localStorage.setItem('access_token', t);\n"
                    "  return <button onClick={() => salvar('x')}>Entrar</button>;\n"
                    "}\n"})
    assert acha(res, "S-09"), "token em localStorage dentro de um .tsx nao disparou"


def test_tsx_com_checkbox_pre_marcado_dispara_p13():
    res = escrever({"src/Aceite.tsx":
                    "export function Aceite() {\n"
                    "  return (\n"
                    "    <label>Aceito receber marketing\n"
                    "      <input type=\"checkbox\" defaultChecked />\n"
                    "    </label>\n"
                    "  );\n"
                    "}\n"})
    assert acha(res, "P-13"), "checkbox pre-marcado num .tsx nao disparou"


def test_a_gramatica_de_tsx_e_de_ts_sao_ambas_tentadas():
    """`.ts` e `.tsx` sao gramaticas DIFERENTES e nenhuma e superconjunto da
    outra. JSX num `.tsx` e generico num `.ts` sao os dois lados."""
    d = Path(tempfile.mkdtemp())
    tsx = d / "a.tsx"
    tsx.write_text("export const C = () => <div>oi</div>;\n", encoding="utf-8")
    ts = d / "b.ts"
    ts.write_text("export function f<T>(x: T): T { return x; }\n",
                  encoding="utf-8")
    for p in (tsx, ts):
        assert jsast.arvore(p, scan.ler(p)) is not None, p.name


# ================== arquivo ilegivel nao apaga o veredito dos outros
def test_um_arquivo_ilegivel_nao_derruba_os_demais():
    """O defeito que o btv expos, e o mais caro do mapa.

    Um `.ts` que nenhuma gramatica alcanca fazia P-13, P-14 e S-09 pararem
    ANTES de olhar os outros arquivos. Fail-closed que apaga achado e o pior
    dos dois mundos: nem verde honesto, nem informacao.
    """
    res = escrever({
        # Sintaxe que nenhuma gramatica aceita — o arquivo que bloqueia.
        "src/quebrado.ts": "export const x = <<<>>> ;;;\n",
        # E um arquivo perfeitamente legivel com uma violacao de verdade.
        "src/Tela.tsx": "export function T({ cpf }: { cpf: string }) {\n"
                        "  localStorage.setItem('cpf', cpf);\n"
                        "  return <div/>;\n"
                        "}\n"})
    assert acha(res, "P-14"), (
        "o achado do arquivo legivel foi apagado pelo arquivo ilegivel — "
        "falso-negativo produzido por fail-closed")


def test_o_veredito_continua_indeterminado_mesmo_emitindo_achado():
    """Bloquear e emitir nao sao opostos. O check NAO viu tudo, entao segue
    indeterminado; o que ele viu vai junto."""
    res = escrever({
        "src/quebrado.ts": "export const x = <<<>>> ;;;\n",
        "src/Tela.tsx": "export function T({ cpf }: { cpf: string }) {\n"
                        "  localStorage.setItem('cpf', cpf);\n"
                        "  return <div/>;\n"
                        "}\n"})
    ind = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    for cid in FRONTEND:
        assert cid in ind, f"{cid} deveria seguir indeterminado"
    assert "quebrado.ts" in ind["P-14"]
    assert "analisado" in ind["P-14"]
    # E o achado do arquivo LEGIVEL saiu junto: bloquear e emitir nao sao
    # opostos, e e essa a correcao inteira.
    assert acha(res, "P-14")


def test_a_mensagem_diz_quantos_leu_e_quantos_nao():
    """Indeterminacao sem numero nao deixa ninguem dimensionar a lacuna."""
    res = escrever({"src/a.ts": "export const x = <<<>>> ;;;\n",
                    "src/b.ts": "export const y = 1;\n",
                    "src/c.ts": "export const z = 2;\n"})
    motivo = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}["P-14"]
    assert "2 arquivo(s) analisado(s) e 1 NAO" in motivo


def test_sem_arquivo_ilegivel_o_check_executa_normalmente():
    """A mordida: se tudo virasse indeterminado, o gate perderia o sentido."""
    res = escrever({"src/a.tsx": "export const C = () => <div>oi</div>;\n"})
    ind = {c["id"] for c in res["checks_indeterminados"]}
    assert not (ind & set(FRONTEND))
    assert set(FRONTEND) <= set(res["checks_executados"])


def test_achado_parcial_nao_vaza_para_check_que_nao_bloqueou():
    """`CheckIndeterminado.achados` carrega SO o que aquele check decidiu."""
    e = CheckIndeterminado("x")
    assert e.achados == []
    e2 = CheckIndeterminado("y", achados=[1, 2])
    assert e2.achados == [1, 2]


# ====================================== o censo de parse entra no mapa
def test_o_censo_conta_todo_arquivo_do_estrato_web():
    """Nenhum arquivo pode sumir: analisado + nao-analisado fecha o total."""
    censo = cobertura.censo_de_parse(Path(tempfile.mkdtemp()))
    assert censo["arquivos"] == 0
    d = Path(tempfile.mkdtemp())
    (d / "a.ts").write_text("export const x = 1;\n", encoding="utf-8")
    (d / "b.tsx").write_text("export const C = () => <div/>;\n", encoding="utf-8")
    (d / "c.ts").write_text("export const x = <<<>>> ;;;\n", encoding="utf-8")
    censo = cobertura.censo_de_parse(d)
    assert censo["arquivos"] == 3
    assert censo["analisados"] + censo["nao_analisados"] == censo["arquivos"]
    assert censo["nao_analisados"] == 1
    assert [x["arquivo"] for x in censo["ilegiveis"]] == ["c.ts"]


def test_a_medicao_do_btv_carrega_o_censo():
    censo = _dados()["medicao"]["parse"]
    assert censo["arquivos"] == censo["analisados"] + censo["nao_analisados"]
    assert censo["analisados"] > 0
    assert censo["percentual_analisado"] > 90


def test_todo_arquivo_web_do_btv_esta_classificado_no_documento():
    """Nenhum dos arquivos do estrato web pode ser silenciosamente ignorado:
    ou entrou na conta dos analisados, ou esta NOMEADO como ilegivel."""
    censo = _dados()["medicao"]["parse"]
    texto = DOC.read_text(encoding="utf-8")
    assert f"**{censo['arquivos']}** arquivos JS/TS" in texto
    assert f"**{censo['analisados']}**" in texto
    for x in censo["ilegiveis"]:
        assert f"`{x['arquivo']}`" in texto, (
            f"{x['arquivo']} nao foi analisado e nao aparece no documento — "
            f"e exatamente o silencio que o mapa existe para impedir")


def test_o_documento_compara_ESTRATO_e_nao_rotulo_de_linguagem():
    """`TypeScript` e `TypeScript/TSX` sao rotulos separados. Compara-los um
    a um contra `Rust` dividia o front em dois e fazia o motor parecer a
    maior fatia por arquivo — o que nao e verdade."""
    vol = _dados()["medicao"]["volume"]
    web = sum(v["arquivos"] for k, v in vol.items()
              if k in cobertura.LINGUAGENS_DA_FAMILIA[cobertura.WEB])
    rust = vol.get("Rust", {}).get("arquivos", 0)
    assert web > rust, (
        f"o estrato web ({web}) deveria ser a maior fatia por arquivos "
        f"contra Rust ({rust})")
    texto = DOC.read_text(encoding="utf-8")
    assert "web (JS/TS/JSX/TSX)" in texto
    assert f"| web (JS/TS/JSX/TSX) | {web} |" in texto


def test_o_documento_traz_as_DUAS_reguas_de_tamanho():
    """Trazer so linhas deixava a impressao de que o alvo era pouco
    auditavel; trazer so arquivos esconderia o Rust nao lido. As duas."""
    texto = DOC.read_text(encoding="utf-8")
    assert "Por ARQUIVOS o maior estrato e `web (JS/TS/JSX/TSX)`" in texto
    assert "Por LINHAS" in texto and "Rust (motor)" in texto
