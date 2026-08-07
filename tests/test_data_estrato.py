"""P-20 — o fundador do estrato `data`, e a decisão sobre P-21.

`data` foi o estrato FUNDADOR da suite: o auditor original nasceu dele, e
por isso quase tudo já existe — catálogo em P-04, linhagem em E-08,
k-anonimato em P-09, pseudonimização em P-06, minimização em P-05,
finalidade em S-07, residência em S-16. Densidade aqui não é herança
preguiçosa: é o estrato onde a suite começou.

Sobrou **um** buraco real, e ele é o mais perigoso justamente por parecer
resolvido: hash determinístico sem chave tratado como anonimização.

  P-20  `hashlib.sha256(cpf)` gravado numa coluna chamada anônima. P-06
        pega a chave no código — mas aqui não HÁ chave. P-18 pega a
        ausência de cifra — mas aqui alguém cifrou, no sentido errado da
        palavra. Nenhum dos 48 checks anteriores pergunta se o "anônimo"
        é anônimo.

O risco desta rodada é preciso: punir HMAC correto, que é exatamente o que
P-06 valida como certo. Os testes que provam que HMAC e sal aleatório NÃO
disparam vêm primeiro, e valem mais que os de caminho feliz.
"""
import json
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar
from pse.model import Severidade

FIX = Path(__file__).parent / "fixtures"
RUIM, BOM = FIX / "consumidor_data_ruim", FIX / "consumidor_data_bom"
CFG = {"catalog_path": "catalog.yaml"}

pytestmark = [pytest.mark.pse_data, pytest.mark.pse_privacy]


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


def rodar(caminho, cfg=None):
    return executar(caminho, {"privacy", "security"}, cfg or CFG, doms=["data"])


def escrever(tmp_path, arquivos, cfg=None):
    for nome, corpo in arquivos.items():
        alvo = tmp_path / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return rodar(tmp_path, cfg)


# ==================================================== o caso correto não dispara
def test_hmac_com_chave_de_cofre_nao_dispara():
    """O teste que mais importa. HMAC com chave de Vault é o comportamento
    que P-06 valida como CERTO — se P-20 o punisse, a suite estaria
    contradizendo a si mesma, e um time que fez a coisa certa receberia
    achado por isso."""
    res = rodar(BOM)
    assert not acha(res, "P-20"), [
        (f.arquivo, f.linha, f.titulo) for f in acha(res, "P-20")]
    assert "P-20" in res["checks_executados"]


def test_sal_aleatorio_por_registro_nao_dispara(tmp_path):
    """Sem determinismo não há ligação: duas ocorrências do mesmo titular
    produzem digests diferentes, e é isso que o hash nu destrói."""
    res = escrever(tmp_path, {
        "e.py": "import hashlib\nimport secrets\n\n\n"
                "def f(cliente, db):\n"
                "    sal = secrets.token_bytes(16)\n"
                "    m = hashlib.sha256(sal + cliente.cpf.encode()).hexdigest()\n"
                "    db.insert('t', {'m': m, 'sal': sal.hex()})\n"})
    assert not acha(res, "P-20"), [f.titulo for f in acha(res, "P-20")]


def test_checksum_de_conteudo_nao_dispara(tmp_path):
    """Hash de arquivo é integridade, não identificador de titular. Punir
    checksum ensinaria o time a ignorar o check."""
    res = escrever(tmp_path, {
        "e.py": "import hashlib\n\n\n"
                "def f(conteudo, db):\n"
                "    db.insert('arquivos', "
                "{'sha': hashlib.sha256(conteudo).hexdigest()})\n"})
    assert not acha(res, "P-20")


def test_hash_de_senha_nao_e_escopo(tmp_path):
    """`password` está em pii-patterns, mas hashear senha é o que se DEVE
    fazer — o defeito ali seria a ausência de KDF, que é outro assunto.
    P-20 é sobre identificador tratado como anônimo, não sobre segredo."""
    res = escrever(tmp_path, {
        "e.py": "import hashlib\n\n\n"
                "def f(usuario, db):\n"
                "    db.insert('u', "
                "{'h': hashlib.sha256(usuario.password.encode()).hexdigest()})\n"})
    assert not acha(res, "P-20")


def test_hash_nao_persistido_nao_dispara(tmp_path):
    """Digest que só vira chave de cache em memória não é dado guardado."""
    res = escrever(tmp_path, {
        "e.py": "import hashlib\n\n\n"
                "def f(cliente):\n"
                "    return hashlib.sha256(cliente.cpf.encode()).hexdigest()\n"})
    assert not acha(res, "P-20")


# ==================================================== o achado
def test_p20_hash_nu_de_cpf_persistido():
    res = rodar(RUIM)
    p20 = acha(res, "P-20")
    assert p20, "sha256 nu de CPF gravado como anônimo passou"
    cpf = [f for f in p20 if "cpf" in f.titulo.lower()]
    assert cpf, [f.titulo for f in p20]
    assert cpf[0].arquivo == "exportacao.py" and cpf[0].linha
    assert "Art. 12" in cpf[0].base_legal


def test_p20_pessoal_comum_e_alto():
    res = rodar(RUIM)
    cpf = [f for f in acha(res, "P-20") if "cpf" in f.titulo.lower()]
    assert cpf[0].severidade is Severidade.ALTO, cpf[0].severidade


def test_p20_sensivel_e_critico():
    """Mesmo princípio ratificado em P-15: Art. 11 é trava estrutural, não
    gradiente. Biometria com hash nu é irreversível de mentira sobre o dado
    mais irreversível que existe — a pessoa não troca de digital."""
    res = rodar(RUIM)
    bio = [f for f in acha(res, "P-20") if "biometria" in f.titulo.lower()]
    assert bio, [f.titulo for f in acha(res, "P-20")]
    assert bio[0].severidade is Severidade.CRITICO
    assert "Art. 11" in bio[0].base_legal


def test_p20_md5_e_sha1_tambem():
    res = rodar(RUIM)
    titulos = " ".join(f.titulo.lower() for f in acha(res, "P-20"))
    assert "email" in titulos, titulos


def test_p20_classe_anonymized_no_catalogo_reforca_o_achado():
    """A declaração `class: anonymized` é a afirmação que o check confronta:
    Art. 12 só dispensa o dado que NÃO PODE ser revertido por meios
    razoáveis, e um dicionário de sha256 sobre o espaço do CPF se constrói
    em segundos."""
    res = rodar(RUIM)
    cpf = [f for f in acha(res, "P-20") if "cpf" in f.titulo.lower()]
    assert "anonymized" in cpf[0].descricao or "anonim" in cpf[0].descricao.lower()


def test_p20_hash_direto_no_sink_sem_variavel(tmp_path):
    res = escrever(tmp_path, {
        "e.py": "import hashlib\n\n\n"
                "def f(cliente, db):\n"
                "    db.insert('t', "
                "{'id': hashlib.sha256(cliente.cpf.encode()).hexdigest()})\n"})
    assert acha(res, "P-20")


def test_p20_exportacao_conta_como_persistencia(tmp_path):
    res = escrever(tmp_path, {
        "e.py": "import hashlib\n\n\n"
                "def f(cliente, api):\n"
                "    h = hashlib.sha256(cliente.cpf.encode()).hexdigest()\n"
                "    api.export({'id': h})\n"})
    assert acha(res, "P-20")


@pytest.mark.mordida
def test_p20_comentario_de_anonimizacao_nao_desliga(tmp_path):
    """D-01: `# anonimizado` acima de um sha256 nu não anonimiza nada. Se
    desligasse, bastaria um comentário para silenciar o check."""
    res = escrever(tmp_path, {
        "e.py": "import hashlib\n\n\n"
                "def f(cliente, db):\n"
                "    # anonimizado com hmac no gateway\n"
                "    h = hashlib.sha256(cliente.cpf.encode()).hexdigest()\n"
                "    db.insert('t', {'id': h})\n"})
    assert acha(res, "P-20"), "comentário citando hmac desligou o check"


@pytest.mark.mordida
def test_p20_sensivel_derruba_o_gate(tmp_path):
    (tmp_path / "catalog.yaml").write_text(
        "tables:\n  t:\n    fields:\n      biometria:\n"
        "        class: sensitive\n        owner: o\n        purpose: p\n"
        "        legal_basis: consentimento\n        retention_years: 1\n"
        "        encryption:\n          algorithm: AES-256-GCM\n"
        "          key_management: aws-kms\n", encoding="utf-8")
    (tmp_path / "pse-config.yaml").write_text(
        "catalog_path: catalog.yaml\n", encoding="utf-8")
    (tmp_path / "e.py").write_text(
        "import hashlib\n\n\n"
        "def f(c, db):\n"
        "    db.insert('t', "
        "{'k': hashlib.sha256(c.biometria.encode()).hexdigest()})\n",
        encoding="utf-8")
    assert main(["--path", str(tmp_path), "--pilar", "privacy",
                 "--domain", "data",
                 "--config", str(tmp_path / "pse-config.yaml")]) == 10


@pytest.mark.mordida
def test_p20_arquivo_que_nao_parseia_e_indeterminado(tmp_path):
    (tmp_path / "catalog.yaml").write_text("tables: {}\n", encoding="utf-8")
    (tmp_path / "e.py").write_text("def f(:\n    pass\n", encoding="utf-8")
    res = rodar(tmp_path)
    assert "P-20" in {c["id"] for c in res["checks_indeterminados"]}


# ==================================================== P-21: a decisão
#
# `pse.testes` reprova todo teste que cite um ID fora do catálogo — ou o check
# foi renomeado e o teste ficou para trás, ou alguém está testando fantasma.
# Aqui a citação é o ponto: o teste existe justamente para provar que P-21 NÃO
# está no catálogo. A exceção fica declarada, com motivo, e aparece no índice.
CHECKS_FORA_DO_CATALOGO = {
    "P-21": "investigado e deliberadamente não implementado; este arquivo é "
            "onde a decisão está assinada, e citar o ID é o teste",
}


def test_p21_nao_existe_e_a_decisao_esta_assinada():
    """P-21 — zona bruta de data lake sem restrição — foi INVESTIGADO e
    NÃO implementado. A decisão fica versionada aqui e na matriz, porque
    buraco honesto é melhor que check que não verifica nada real.

    Três razões, nesta ordem:

    1. A identificação da zona bruta viria do NOME do bucket
       (`raw`/`bronze`/`landing`). Isso é menção, não fato — exatamente o
       que o D-01 proíbe, e num check cuja consequência seria bloquear CI.
    2. Uma policy sem `Condition` no Terraform NÃO é violação por si: a
       restrição pode viver numa SCP, num permission boundary, num grant de
       Lake Formation ou no provedor de identidade — todos fora do
       repositório. O check acusaria setup correto, que é o D-08 ao
       contrário.
    3. A suite não tem parser de HCL, e adicionar um para avaliar uma forma
       de política que não se consegue decidir seria construir a aparência
       de cobertura.

    O que faria P-21 nascer de verdade: um artefato de policy-as-code
    versionado que declare finalidade e expiração por zona — aí há
    declaração a confrontar com fato, que é como todos os outros funcionam.
    """
    from pse import catalogo, matriz
    assert "P-21" not in catalogo.CATALOGO, (
        "P-21 entrou no catálogo sem que esta decisão fosse revista")
    assert ("data", "zona_bruta") in matriz.FORA_DE_ESCOPO_ESTATICO, (
        "a decisão de não implementar P-21 tem de estar assinada em "
        "pse/matriz.py — buraco sem leitura é buraco escondido")
    leitura = matriz.FORA_DE_ESCOPO_ESTATICO[("data", "zona_bruta")]
    assert len(leitura) > 200, "leitura curta demais para uma decisão de escopo"


def test_fora_de_escopo_aparece_no_mapa_versionado():
    doc = (Path(__file__).resolve().parent.parent /
           "docs" / "matriz-dominio.md").read_text(encoding="utf-8")
    assert "P-21" in doc or "zona bruta" in doc.lower(), (
        "a decisão de fora-de-escopo não chegou ao mapa que o consumidor lê")


# ==================================================== o estrato como um todo
def test_p20_no_dominio_data_com_prefixo_de_pilar():
    from pse import catalogo
    assert catalogo.dominios("P-20") == ["data"]
    assert catalogo.pilar_esperado("P-20") == "privacy"
    assert catalogo.incoerencias_de_prefixo() == []


def test_p20_tem_mutacao_canonica():
    from pse.mutacao import provar
    r = provar("P-20")
    assert r["ok"], r["motivo"]


def test_todo_dominio_tem_check_nascido_do_estrato():
    """O fecho da matriz: depois desta rodada, nenhum dos cinco domínios
    depende só de herança. É a afirmação estrutural da versão."""
    from pse import matriz
    for dom in ("frontend", "api", "backend", "data", "ai"):
        leitura = matriz.LEITURA_DA_DENSIDADE[dom]
        assert "nasce" in leitura.lower(), (
            f"a leitura de `{dom}` não afirma nenhum check nascido do "
            f"estrato: {leitura[:80]}")


@pytest.mark.mordida
def test_fixture_ruim_derruba_o_gate():
    rc = main(["--path", str(RUIM), "--domain", "data",
               "--config", str(RUIM / "pse-config.yaml")])
    assert rc in (10, 11), rc


@pytest.mark.mordida
def test_fixture_conforme_e_verde_no_estrato_inteiro(tmp_path):
    out = tmp_path / "l.json"
    rc = main(["--path", str(BOM), "--domain", "data",
               "--config", str(BOM / "pse-config.yaml"), "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0, [(f["check_id"], f["titulo"]) for f in laudo["findings"]] + \
        laudo["checks_indeterminados"]
