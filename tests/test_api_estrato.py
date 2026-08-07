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


# ==================================================== S-22
#
# Seis materiais de security foram avaliados nesta rodada e renderam UM check.
# Não é falha da leitura: BOLA já era S-01, minimização já era P-05, hash como
# anonimização já era P-20, DPA de terceiro já era S-04, dado de treino já era
# P-15. A convergência é o resultado — a régua generalizou além dos exemplos
# que a produziram, e a suíte parou de crescer porque cobriu o essencial.
#
# O vetor que sobrou é o mais fino de todos, e é por isso que ele escapou até
# agora: S-07 verifica que a etiqueta de finalidade existe e é registrada;
# ninguém verificava se a etiqueta tem CONSEQUÊNCIA.
SUP = {"catalog_path": "catalog.yaml"}


def s22(res):
    return acha(res, "S-22")


@pytest.mark.pse_security
def test_s22_finalidade_lida_sem_mapa_de_base_legal_dispara():
    res = rodar(RUIM)
    f = s22(res)
    assert f, "a fixture lê X-Purpose e não amarra base legal nenhuma"
    assert f[0].severidade.name == "ALTO", (
        "falha de limitação de finalidade é grave e não é exposição consumada "
        "— CRÍTICO fica reservado ao que já vazou (critério de S-14/S-15)")
    assert f[0].arquivo.endswith("finalidade.py")


@pytest.mark.pse_security
def test_s22_mapa_e_recusa_desligam_o_achado():
    """D-08. Punir quem escreveu a tabela E a checagem ensinaria o time a não
    escrever nenhuma das duas."""
    res = rodar(BOM)
    assert not s22(res), [(f.arquivo, f.linha, f.titulo) for f in s22(res)]
    assert "S-22" in res["checks_executados"], "verde por não ter olhado"


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s22_comentario_de_checagem_nao_desliga(tmp_path):
    """D-01. `# TODO: validar legal basis` é exatamente o que existe na fixture
    ruim, e é o caso em que um grep de menção daria verde."""
    res = escrever(tmp_path, {"api.py":
                              "from flask import request\n"
                              "# legal_basis: consentimento para marketing\n"
                              "def rota():\n"
                              "    p = request.headers.get('X-Purpose')\n"
                              "    return repo.ler(p)\n"}, cfg=SUP)
    assert s22(res), "comentário citando base legal desligou o achado"


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s22_mapa_decorativo_ainda_dispara(tmp_path):
    """O segundo achado, e o mais interessante: o alvo já fez o trabalho
    difícil de escrever a tabela, e ninguém a consulta. Uma tabela que ninguém
    consulta é papel, e papel não é enforcement."""
    res = escrever(tmp_path, {"api.py":
                              "from flask import request\n"
                              "BASES = {'marketing': 'consentimento',\n"
                              "         'cobranca': 'execucao_de_contrato'}\n"
                              "def rota():\n"
                              "    p = request.headers.get('X-Purpose')\n"
                              "    return repo.ler(p)\n"}, cfg=SUP)
    f = s22(res)
    assert f and "nao e aplicado" in f[0].titulo, [x.titulo for x in f]


@pytest.mark.pse_security
def test_s22_sem_finalidade_entrando_e_pulado(tmp_path):
    """Sem finalidade não há o que amarrar a base nenhuma. A propagação em si
    é cobrada por S-07 — cobrar o mesmo defeito duas vezes ensina a ignorar
    os dois."""
    res = escrever(tmp_path, {"api.py": "def rota():\n    return repo.ler()\n"},
                   cfg=SUP)
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "S-22" in pulados and "S-07" in pulados["S-22"]


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s22_mapa_nao_literal_indetermina(tmp_path):
    """Precisão sobre recall. Há finalidade entrando e há um identificador com
    nome de mapa de base legal — e o que ele guarda vem de uma chamada. Chutar
    aqui seria trocar fail-closed por adivinhação."""
    res = escrever(tmp_path, {"api.py":
                              "from flask import request\n"
                              "BASES_LEGAIS = carregar_config('bases.yml')\n"
                              "def rota():\n"
                              "    p = request.headers.get('X-Purpose')\n"
                              "    return repo.ler(p)\n"}, cfg=SUP)
    indet = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "S-22" in indet, res["checks_executados"]
    assert "BASES_LEGAIS" in indet["S-22"]


@pytest.mark.pse_security
def test_s22_declaracao_com_base_por_finalidade_conta_como_mapa(tmp_path):
    """A forma declarada vale tanto quanto a do código — é a que
    `consent-model.yaml` já usa. Sem consulta no código, porém, continua
    decorativa."""
    res = escrever(tmp_path, {
        "consent-model.yaml": "purposes:\n"
                              "  - id: cobranca\n"
                              "    base_legal: execucao_de_contrato\n",
        "api.py": "from flask import request\n"
                  "def rota():\n"
                  "    return repo.ler(request.headers.get('X-Purpose'))\n"},
        cfg=SUP)
    f = s22(res)
    assert f and "nao e aplicado" in f[0].titulo, [x.titulo for x in f]


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s22_finalidade_disfarcada_de_base_nao_conta_como_mapa(tmp_path):
    """`interesse_do_negocio` e `melhoria_do_produto` não são bases legais —
    são finalidades vestidas de base, e é o erro que S-22 existe para achar.
    Se a régua as reconhecesse, o check viraria o seu contrário."""
    res = escrever(tmp_path, {"api.py":
                              "from flask import request\n"
                              "BASES = {'marketing': 'interesse_do_negocio',\n"
                              "         'perfil': 'melhoria_do_produto'}\n"
                              "def rota():\n"
                              "    p = request.headers.get('X-Purpose')\n"
                              "    if p not in BASES:\n"
                              "        raise PermissionError(p)\n"
                              "    return repo.ler(p)\n"}, cfg=SUP)
    f = s22(res)
    assert f and "sem base legal amarrada" in f[0].titulo, [x.titulo for x in f]


@pytest.mark.pse_security
def test_s22_e_s07_nao_sao_o_mesmo_check():
    """A fixture ruim faz TUDO o que S-07 pede — exige 428 sem finalidade,
    propaga e registra ator/ação/recurso/finalidade no log. E reprova em S-22,
    porque nada diz sob que base aquela finalidade podia rodar. Um sistema
    passa o primeiro e falha o segundo: é o caso comum, e é por isso que são
    dois IDs e não um."""
    from pse import catalogo
    res = rodar(RUIM)
    assert s22(res), "S-22 tem de disparar contra a fixture"
    assert not acha(res, "S-07"), "S-07 não é dono deste defeito"
    assert "Art. 6o" in catalogo.base_legal("S-22")
    assert "Art. 37" in catalogo.base_legal("S-07")
    assert catalogo.dominios("S-22") == ["api"]
    assert catalogo.meta("S-22")["pack"] == "security"


@pytest.mark.pse_security
def test_s22_declara_a_metade_runtime_nao_executada():
    """Meia execução silenciosa é meia-verdade no laudo. Sem a combinação
    declarada em `target.endpoints.finalidade_incompativel`, a suíte não sai
    inventando o que testar — e diz que não testou."""
    res = rodar(RUIM)
    parcial = res.get("relatorios", {}).get("cobertura_parcial", {})
    assert "S-22" in parcial and "runtime" in parcial["S-22"]


# ============================== os dois candidatos que NÃO viraram check
#
# Da mesma avaliação de seis materiais saíram dois vetores reais que foram
# deliberadamente deixados de fora. Não é backlog: é a decisão de que o check
# possível verificaria a fachada, não o direito — e o laudo passaria a afirmar
# cobertura onde não há. É a mesma regra que matou P-21.
#
# Os testes abaixo não verificam alvo nenhum. Eles verificam que a DECISÃO
# continua assinada — e reprovam se alguém implementar o check fraco sem
# revisá-la, ou se a leitura sumir do mapa que o consumidor lê.
def test_acesso_do_titular_nao_virou_check_e_a_decisao_esta_assinada():
    """Art. 18 II. O check possível seria "existe rota de exportação?" — e
    isso já é P-10, que roda no ar e confirma que ela responde e devolve
    conteúdo íntegro.

    O que faria dele um check NOVO seria verificar que a resposta traz os
    dados daquele titular, todos eles, dentro do prazo. As três são
    inverificáveis: a primeira exige conhecer o conjunto correto (só o alvo
    sabe), a segunda exige impersonar titular real (o Trabalho A obriga
    identidade sintética), a terceira é propriedade do processo.

    Um check de "existe rota" duplicaria P-10 com nome novo, e o laudo
    exibiria dois verdes pela mesma evidência — inflação de cobertura."""
    from pse import matriz
    assert ("api", "acesso_do_titular") in matriz.FORA_DE_ESCOPO_ESTATICO, (
        "a decisão de não implementar o acesso do titular tem de estar "
        "assinada em pse/matriz.py — buraco sem leitura é buraco escondido")
    leitura = matriz.FORA_DE_ESCOPO_ESTATICO[("api", "acesso_do_titular")]
    assert "P-10" in leitura, "a leitura tem de nomear o check que já cobre"
    assert len(leitura) > 200, "leitura curta demais para uma decisão de escopo"


def test_revogacao_downstream_nao_virou_check_e_a_decisao_esta_assinada():
    """Art. 18 IX. O vetor é real e grave, e é por construção não observável
    a partir do alvo: a prova exigiria enumerar e acessar sistemas a jusante
    que não são o alvo declarado — exatamente o que o contrato do Trabalho A
    proíbe.

    A metade verificável já tem dono: P-19 (crypto-shredding no log
    append-only) e P-07 (revogação existe, retenção pós-revogação
    declarada)."""
    from pse import matriz
    assert ("data", "revogacao_downstream") in matriz.FORA_DE_ESCOPO_ESTATICO
    leitura = matriz.FORA_DE_ESCOPO_ESTATICO[("data", "revogacao_downstream")]
    assert "P-19" in leitura and "P-07" in leitura, (
        "a leitura tem de nomear a metade que JÁ é verificada, senão parece "
        "que a suíte não olha nada disso")
    assert len(leitura) > 200


def test_os_buracos_assumidos_chegam_aos_documentos_que_o_consumidor_le():
    """Decisão que ninguém acha não foi tomada. Ela tem de estar nos dois
    documentos gerados — a matriz e a seção de lacunas de TESTES.md — e o
    gerador LÊ a tabela, não a recopia: fechado um buraco, ele some dos dois
    no mesmo commit."""
    from pse import testes
    raiz = Path(__file__).resolve().parent.parent
    doc = (raiz / "docs" / "matriz-dominio.md").read_text(encoding="utf-8")
    assert "acesso_do_titular" in doc and "revogacao_downstream" in doc

    buracos = {b["vetor"] for b in testes._buracos_assumidos()}
    assert any("titular" in b for b in buracos), buracos
    assert any("evoga" in b for b in buracos), buracos
    lacuna = [i for i in testes.lacunas()
              if i["titulo"] == "Vetores reais deliberadamente nao implementados"]
    assert lacuna and lacuna[0]["aberta"]


def test_convergencia_registrada_seis_materiais_um_check():
    """Seis materiais renderem um check é RESULTADO, não falha: a régua
    generalizou além dos exemplos que a produziram. O registro fica no
    catálogo (fase 12 tem exatamente um check) e na docstring de S-22."""
    from pse import catalogo
    fase12 = [c for c, m in catalogo.CATALOGO.items() if m.get("fase") == 12]
    assert fase12 == ["S-22"], fase12


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
