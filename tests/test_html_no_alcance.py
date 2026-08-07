"""HTML era `IRRELEVANTE`, e isso escondia egresso a terceiro.

O btv contacta `fonts.googleapis.com` — a camada DINAMICA viu, a ESTATICA
nao. A causa nao era um check fraco: era um rotulo. `.html` estava em
`alcance.IRRELEVANTES` ("nem codigo nem declaracao") e S-04 nunca abria um.

Mas `index.html` e o unico arquivo do bundle que o navegador carrega SEMPRE,
e e exatamente onde mora `<link href="https://fonts.googleapis.com/...">`.
Um arquivo que DECLARA para onde o navegador vai nao e irrelevante — chamar
de irrelevante era a lacuna se escondendo atras de uma palavra.

E o mesmo padrao de todas as rodadas anteriores: nao um erro de logica, e um
silencio com aparencia de decisao.
"""
import tempfile
from pathlib import Path

import pytest

from pse import alcance
from pse.engine import scan
from pse.engine.runner import executar


def escrever(arquivos):
    d = Path(tempfile.mkdtemp())
    for nome, corpo in arquivos.items():
        alvo = d / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return executar(d, {"security"}, {})


def s04(res):
    return [f for f in res["findings"] if f.check_id == "S-04"]


# ------------------------------------------------- o rotulo estava errado
def test_html_saiu_de_irrelevantes_e_entrou_no_alcance():
    assert ".html" not in alcance.IRRELEVANTES
    assert ".htm" not in alcance.IRRELEVANTES
    assert alcance.COM_PARSER[".html"][0] == "HTML"
    assert alcance.COM_PARSER[".htm"][0] == "HTML"


def test_o_laudo_conta_html_como_lido(tmp_path):
    (tmp_path / "index.html").write_text("<html></html>\n", encoding="utf-8")
    lidos = {x["linguagem"]: x for x in alcance.medir(tmp_path)["lidos"]}
    assert "HTML" in lidos
    assert lidos["HTML"]["ferramenta"]


# ------------------------------------------------- o fato dispara
def test_link_a_terceiro_no_html_dispara_s04():
    """O achado que so a camada dinamica via."""
    res = escrever({"index.html":
                    '<html><head>\n'
                    '<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
                    '</head></html>\n'})
    achados = s04(res)
    assert achados, "host de terceiro num <link> do HTML nao disparou"
    assert any("fonts.googleapis.com" in f.titulo for f in achados)
    assert achados[0].arquivo.endswith(".html")


def test_script_src_a_terceiro_no_html_dispara():
    res = escrever({"index.html":
                    '<html><body>\n'
                    '<script src="https://cdn.terceiro.test/lib.js"></script>\n'
                    '</body></html>\n'})
    assert any("cdn.terceiro.test" in f.titulo for f in s04(res))


# ------------------------------------------------- D-01 vale igual aqui
def test_host_em_comentario_html_nao_dispara():
    """`<!-- ... -->` e onde o vigiado escreve o que quiser. Sem tratamento
    proprio, o apagador generico usaria `#` — que em HTML nao comenta nada —
    e o comentario valeria como fato."""
    res = escrever({"index.html":
                    '<html><head>\n'
                    '<!-- <link href="https://tracker-comentado.test/x.js"> -->\n'
                    '</head></html>\n'})
    assert not any("tracker-comentado" in f.titulo for f in s04(res))


def test_comentario_html_preserva_numero_de_linha():
    """Apagar por substituicao, nao por remocao: o `arquivo:linha` do achado
    tem de continuar apontando para o lugar certo."""
    texto = ('<html>\n'
             '<!-- comentario\n'
             '     de varias linhas -->\n'
             '<link href="https://real.test/x">\n')
    efetivo = scan.codigo_efetivo(texto, ".html")
    assert efetivo.count("\n") == texto.count("\n")
    assert "comentario" not in efetivo
    assert "real.test" in efetivo
    assert efetivo.splitlines()[3].strip().startswith("<link")


def test_o_valor_do_atributo_NAO_e_apagado():
    """Em HTML o valor do atributo E o fato: `href="https://..."` nao e a
    mencao de um terceiro, e o egresso acontecendo. Apagar literais aqui —
    como se faz para logica de supressao — cegaria o check inteiro."""
    efetivo = scan.codigo_efetivo(
        '<link href="https://fonts.googleapis.com/css2">\n', ".html")
    assert "fonts.googleapis.com" in efetivo


# ------------------------------------------------- o correto nao dispara
def test_host_proprio_e_relativo_nao_disparam():
    res = escrever({
        "index.html": '<html><head>\n'
                      '<link rel="icon" href="/favicon.svg" />\n'
                      '<script type="module" src="./src/main.tsx"></script>\n'
                      '</head></html>\n'})
    assert not s04(res)


def test_terceiro_declarado_no_manifesto_nao_dispara():
    """D-08: quem registrou a integracao fez o certo, e nao pode ser punido."""
    res = escrever({
        ".privacy/third-party-manifest.yml":
            "integrations:\n  - name: Google Fonts\n"
            "    hosts: [fonts.googleapis.com]\n"
            "    dpa_signed: true\n"
            "    dpa_path: contratos/google-fonts.pdf\n",
        "index.html": '<html><head>\n'
                      '<link href="https://fonts.googleapis.com/css2" />\n'
                      '</head></html>\n'})
    assert not any("fonts.googleapis.com" in f.titulo for f in s04(res))


# ------------------------------------- a corroboracao entre as duas camadas
def test_o_host_que_a_dinamica_viu_agora_a_estatica_tambem_ve():
    """A prova de que a lacuna fechou: o mesmo host, nas duas camadas.

    Antes, `fonts.googleapis.com` aparecia em `observacao_de_rede` e em
    NENHUM achado estatico — e um leitor podia concluir que o egresso era
    coisa do navegador, nao do artefato. Ele esta declarado no `index.html`
    entregue.
    """
    res = escrever({"index.html":
                    '<html><head>\n'
                    '<link rel="preconnect" href="https://fonts.googleapis.com" />\n'
                    '<link rel="preconnect" href="https://fonts.gstatic.com" '
                    'crossorigin />\n'
                    '</head></html>\n'})
    hosts = {h for f in s04(res) for h in ("fonts.googleapis.com",
                                           "fonts.gstatic.com")
             if h in f.titulo}
    assert hosts == {"fonts.googleapis.com", "fonts.gstatic.com"}
