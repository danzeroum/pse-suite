"""S-12, P-17, S-13 — o pacote fundador do estrato de API.

A matriz de v0.7.0 disse a verdade incômoda sobre este domínio: `api` tinha
12 checks e **nenhum nascido olhando para ele**. Vieram do Trabalho A e do
inventário, foram etiquetados depois. Densidade por herança não é cobertura
— é um número que engana quem lê o mapa.

Estes três nascem da pergunta *o que é próprio de uma borda de API?*:

  S-12  o CONTRATO é o artefato do estrato. Uma API declara campos, escopos
        e formatos num documento que outro time consome sem ler o código.
        Se esse documento carrega PII e não diz que carrega, a ontologia
        existe só na cabeça de quem escreveu. E se ele PROMETE uma ontologia
        que a implementação não cumpre, é pior: quem lê confia.
  P-17  discriminação sem modelo nenhum. Um endpoint de busca que aceita
        `?raca=` entrega segmentação discriminatória pronta, sem ML, sem
        score, sem nada que E-05 alcance.
  S-13  a borda é onde o erro vira resposta. S-03 já pega PII no payload;
        este pega a ESTRUTURA — pilha, caminho no disco, versão de framework.

O risco desta rodada, nomeado pelo arquiteto: (a) grep-de-menção
reintroduzir o D-01 num domínio inteiro e (b) falso-positivo punir contrato
correto. Por isso o primeiro teste do arquivo é o que prova que a fixture
conforme **não dispara nada**.
"""
import json
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar

FIX = Path(__file__).parent / "fixtures"
RUIM, BOM = FIX / "consumidor_api_ruim", FIX / "consumidor_api_bom"
CFG = {"catalog_path": "catalog.yaml"}

pytestmark = pytest.mark.pse_api

FUNDADORES = ("S-12", "P-17", "S-13")


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


def rodar(caminho, cfg=None):
    return executar(caminho, {"privacy", "security"}, cfg or CFG, doms=["api"])


def escrever(tmp_path, arquivos, cfg=None):
    for nome, corpo in arquivos.items():
        alvo = tmp_path / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return rodar(tmp_path, cfg)


# ==================================================== o caso correto não dispara
def test_api_conforme_nao_dispara_nenhum_fundador():
    """O teste que vale mais que os de caminho feliz. Contrato com `x-ethics`
    coerente, busca com vocabulário fechado e erro padronizado é exatamente o
    comportamento que os três checks querem produzir — puni-lo ensinaria o
    time a ignorar o pack no primeiro dia (D-08)."""
    res = rodar(BOM)
    for cid in FUNDADORES:
        assert not acha(res, cid), [
            (f.arquivo, f.linha, f.titulo) for f in acha(res, cid)]
        assert cid in res["checks_executados"], (
            f"{cid} não chegou a executar na fixture conforme — verde por não "
            f"ter olhado é o defeito que a suite inteira existe para impedir")


# ==================================================== S-12
@pytest.mark.pse_security
def test_s12_spec_com_pii_sem_ontologia():
    res = rodar(RUIM)
    s12 = acha(res, "S-12")
    assert s12, "schema expõe cpf/email/genero sem x-ethics e passou"
    cliente = [f for f in s12 if "Cliente" in f.titulo]
    assert cliente, [f.titulo for f in s12]
    assert cliente[0].arquivo == "openapi.yaml" and cliente[0].linha


@pytest.mark.pse_security
def test_s12_promessa_sem_implementacao():
    """O vetor de maior valor: o contrato declara `telefone` como PII sob
    `x-ethics`, e o DTO nunca soube desse campo. Ontologia que ninguém
    implementa é pior que ontologia ausente — quem lê o contrato confia."""
    res = rodar(RUIM)
    conta = [f for f in acha(res, "S-12") if "ContaBancaria" in f.titulo]
    assert conta, [f.titulo for f in acha(res, "S-12")]
    assert "telefone" in conta[0].descricao
    assert "dtos.py" in (conta[0].descricao + str(conta[0].arquivo))


@pytest.mark.pse_security
def test_s12_schema_sem_pii_nao_exige_ontologia(tmp_path):
    """Exigir `x-ethics` de um schema sem dado pessoal seria burocracia — e
    burocracia ensina o time a preencher por reflexo, que é o oposto de uma
    ontologia útil."""
    res = escrever(tmp_path, {"openapi.yaml":
                              "openapi: 3.0.3\ncomponents:\n  schemas:\n"
                              "    Pedido:\n      type: object\n"
                              "      properties:\n        id: {type: string}\n"
                              "        valor: {type: number}\n"})
    assert not acha(res, "S-12")


@pytest.mark.pse_security
def test_s12_sem_spec_e_pulado_com_motivo(tmp_path):
    res = escrever(tmp_path, {"app.py": "x = 1\n"})
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "S-12" in pulados and pulados["S-12"]


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s12_spec_que_nao_parseia_e_indeterminado(tmp_path):
    """Nunca verde por não ter conseguido ler. Um contrato quebrado é uma
    pergunta sem resposta, e pergunta sem resposta bloqueia (exit 20)."""
    (tmp_path / "openapi.yaml").write_text(
        "openapi: 3.0.3\ncomponents:\n  schemas:\n   - [quebrado\n",
        encoding="utf-8")
    res = rodar(tmp_path)
    motivos = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "S-12" in motivos, res["checks_executados"]


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s12_nao_le_mencao_em_comentario(tmp_path):
    """D-01 no estrato novo: `# x-ethics: pii: [cpf]` num comentário do YAML
    não é ontologia nenhuma. Se ligasse, bastaria um comentário para
    silenciar o check inteiro."""
    res = escrever(tmp_path, {"openapi.yaml":
                              "openapi: 3.0.3\ncomponents:\n  schemas:\n"
                              "    Cliente:\n      type: object\n"
                              "      # x-ethics: {pii: [cpf]}\n"
                              "      properties:\n        cpf: {type: string}\n"})
    assert acha(res, "S-12"), "comentário citando x-ethics desligou o check"


# ==================================================== P-17
@pytest.mark.pse_privacy
def test_p17_rota_aceita_filtro_proibido():
    res = rodar(RUIM)
    p17 = acha(res, "P-17")
    assert p17, "rota de busca aceita ?raca= e ?cep= e passou"
    campos = " ".join(f.titulo + f.descricao for f in p17)
    assert "raca" in campos and "cep" in campos


@pytest.mark.pse_privacy
def test_p17_pega_parametro_de_funcao_alem_do_request():
    """Um filtro chega por `request.args.get('raca')` e por parâmetro nomeado
    da própria view — as duas formas são a mesma borda."""
    res = rodar(RUIM)
    titulos = " ".join(f.titulo for f in acha(res, "P-17"))
    assert "genero" in titulos, titulos


@pytest.mark.pse_privacy
def test_p17_le_o_contrato_tambem():
    """O filtro proibido declarado em `parameters` da spec é o mesmo fato
    visto do lado do contrato — e é onde ele é público."""
    res = rodar(RUIM)
    do_contrato = [f for f in acha(res, "P-17") if f.arquivo == "openapi.yaml"]
    assert do_contrato, [f.arquivo for f in acha(res, "P-17")]


@pytest.mark.pse_privacy
def test_p17_guarda_que_executa_desliga(tmp_path):
    """D-08: allowlist aplicada por uma chamada que EXECUTA não pode receber
    achado."""
    res = escrever(tmp_path, {"rotas.py":
                              "from flask import request\n\n\n"
                              "@app.get('/x')\n"
                              "def buscar():\n"
                              "    cep = request.args.get('cep')\n"
                              "    return q(**validar_filtros({'cep': cep}))\n"})
    assert not acha(res, "P-17"), [f.titulo for f in acha(res, "P-17")]


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_p17_mencao_em_comentario_nao_liga_nem_desliga(tmp_path):
    """As duas metades do D-01 num teste só: o comentário que cita `raca`
    não cria achado, e o comentário que cita a guarda não o desliga."""
    res = escrever(tmp_path, {"rotas.py":
                              "from flask import request\n\n\n"
                              "@app.get('/a')\n"
                              "def a():\n"
                              "    # filtra por raca no futuro\n"
                              "    return q(request.args.get('cidade'))\n\n\n"
                              "@app.get('/b')\n"
                              "def b():\n"
                              "    # validar_filtros aplicado no gateway\n"
                              "    return q(request.args.get('raca'))\n"})
    ids = {(f.linha) for f in acha(res, "P-17")}
    assert ids, "menção da guarda em comentário desligou o check (D-01)"
    titulos = " ".join(f.titulo for f in acha(res, "P-17"))
    assert titulos.count("raca") == 1, (
        f"comentário citando `raca` virou achado próprio: {titulos}")


@pytest.mark.pse_privacy
def test_p17_rota_sem_filtro_proibido_nao_dispara(tmp_path):
    res = escrever(tmp_path, {"rotas.py":
                              "from flask import request\n\n\n"
                              "@app.get('/pedidos')\n"
                              "def buscar():\n"
                              "    return q(request.args.get('status'))\n"})
    assert not acha(res, "P-17")


# ==================================================== S-13
@pytest.mark.pse_security
def test_s13_handler_devolve_traceback():
    res = rodar(RUIM)
    s13 = acha(res, "S-13")
    assert s13, "handler devolve traceback e versão ao cliente e passou"
    assert all(f.arquivo == "erros.py" for f in s13), [f.arquivo for f in s13]
    texto = " ".join(f.descricao for f in s13)
    assert "traceback" in texto.lower()


@pytest.mark.pse_security
def test_s13_pega_versao_e_caminho_alem_da_pilha():
    res = rodar(RUIM)
    texto = " ".join(f.titulo + f.descricao for f in acha(res, "S-13")).lower()
    assert "versao" in texto or "versão" in texto
    assert "caminho" in texto


@pytest.mark.pse_security
def test_s13_debug_ligado_e_achado():
    """`app.run(debug=True)` é o console do Werkzeug: traceback interativo
    para qualquer requisição que estoure. É o mesmo defeito com outra roupa."""
    res = rodar(RUIM)
    debug = [f for f in acha(res, "S-13") if "debug" in f.titulo.lower()]
    assert debug, [f.titulo for f in acha(res, "S-13")]


@pytest.mark.pse_security
def test_s13_erro_padronizado_nao_dispara(tmp_path):
    res = escrever(tmp_path, {"erros.py":
                              "import logging\nimport uuid\n\n"
                              "from flask import jsonify\n\n"
                              "log = logging.getLogger(__name__)\n\n\n"
                              "@app.errorhandler(500)\n"
                              "def falha(e):\n"
                              "    c = str(uuid.uuid4())\n"
                              "    log.exception('falha')\n"
                              "    return jsonify({'erro': 'interno', 'id': c}), 500\n"})
    assert not acha(res, "S-13"), [f.titulo for f in acha(res, "S-13")]


@pytest.mark.pse_security
def test_s13_traceback_no_log_nao_e_achado(tmp_path):
    """A distinção que o check tem de fazer: `log.exception` manda a pilha
    para o lado de dentro. Punir observabilidade seria empurrar o time a
    apagar o log em vez de sanear a resposta."""
    res = escrever(tmp_path, {"erros.py":
                              "import logging\nimport traceback\n\n"
                              "log = logging.getLogger(__name__)\n\n\n"
                              "def salvar(p):\n"
                              "    try:\n        return r.salvar(p)\n"
                              "    except Exception:\n"
                              "        log.error(traceback.format_exc())\n"
                              "        return {'erro': 'interno'}, 500\n"})
    assert not acha(res, "S-13"), [f.titulo for f in acha(res, "S-13")]


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s13_arquivo_que_nao_parseia_e_indeterminado(tmp_path):
    (tmp_path / "erros.py").write_text("def f(:\n    pass\n", encoding="utf-8")
    res = rodar(tmp_path)
    motivos = {c["id"] for c in res["checks_indeterminados"]}
    assert "S-13" in motivos and "P-17" in motivos


# ==================================================== o estrato como um todo
def test_os_tres_estao_no_dominio_api():
    from pse import catalogo
    for cid in FUNDADORES:
        assert catalogo.dominios(cid) == ["api"], catalogo.dominios(cid)
        assert catalogo.meta(cid)["status"] == "implementado"


def test_prefixo_segue_o_pilar():
    """A trava que o arquiteto impôs em v0.7.0 vale para o pacote novo: nada
    de `AP-*`. O prefixo carrega o pilar, e o domínio vive em `domain`."""
    from pse import catalogo
    assert catalogo.pilar_esperado("S-12") == "security"
    assert catalogo.pilar_esperado("P-17") == "privacy"
    assert catalogo.pilar_esperado("S-13") == "security"
    assert catalogo.incoerencias_de_prefixo() == []


def test_cada_fundador_tem_mutacao_canonica():
    from pse.mutacao import provar
    for cid in FUNDADORES:
        r = provar(cid)
        assert r["ok"], r["motivo"]


@pytest.mark.mordida
def test_fixture_ruim_derruba_o_gate(tmp_path):
    rc = main(["--path", str(RUIM), "--domain", "api",
               "--config", str(RUIM / "pse-config.yaml")])
    assert rc in (10, 11), rc


@pytest.mark.mordida
def test_fixture_conforme_e_verde_no_estrato_inteiro(tmp_path):
    """`--domain api` inteiro, não só os três: um fundador que só passa
    quando isolado não serve para nada no CI de ninguém."""
    out = tmp_path / "l.json"
    rc = main(["--path", str(BOM), "--domain", "api",
               "--config", str(BOM / "pse-config.yaml"), "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0, [(f["check_id"], f["titulo"]) for f in laudo["findings"]] + \
        laudo["checks_indeterminados"]
