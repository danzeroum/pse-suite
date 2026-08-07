"""S-14, S-15, P-18, P-19, S-16 — o pacote fundador do estrato de backend.

Mesmo diagnóstico que a matriz fez sobre `api`: 11 checks, todos herdados.
São os estáticos do inventário, reclassificados — nenhum nasceu da pergunta
*o que é próprio de um backend?*

E a resposta não é "código de servidor". É a **infraestrutura que só existe
deste lado**: o dump que viaja entre ambientes, a role do banco, a coluna
cifrada, o tópico imutável e a região onde o byte pousa. Nenhum desses cinco
vetores tem equivalente no frontend, na borda ou no modelo.

  S-14  dump de produção restaurado em ambiente inferior sem descaracterizar.
        É o vazamento que não passa por nenhuma API: o dado sai pela porta
        de trás, com credencial de operação e sem log de acesso.
  S-15  role de banco com privilégio amplo. `GRANT SELECT ON ALL TABLES` é
        uma decisão de minimização tomada uma vez e herdada para sempre.
  P-18  campo sensível persistido sem cifra de aplicação. P-06 pega a chave
        no código; este pega a ausência da cifra.
  P-19  eliminação num log append-only. Apagar a linha não é uma operação
        disponível: ou há crypto-shredding, ou o Art. 18 VI não é cumprível.
  S-16  residência no ponto de ESCRITA. S-08 olha o egresso declarado no
        manifesto; este olha onde o byte efetivamente pousa.

O primeiro teste do arquivo é, de novo, o que prova que a fixture conforme
não dispara nada. Falso-positivo em infra é caro: o time não consegue
"consertar" um pipeline que já está certo, e aprende a ignorar o pack.
"""
import json
from pathlib import Path

import pytest

from pse.cli import main
from pse.engine.runner import executar

FIX = Path(__file__).parent / "fixtures"
RUIM, BOM = FIX / "consumidor_backend_ruim", FIX / "consumidor_backend_bom"
CFG = {"catalog_path": "catalog.yaml", "data_residency": "BR"}

pytestmark = pytest.mark.pse_backend

FUNDADORES = ("S-14", "S-15", "P-18", "P-19", "S-16")


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


def rodar(caminho, cfg=None):
    return executar(caminho, {"privacy", "security"},
                    CFG if cfg is None else cfg, doms=["backend"])


def escrever(tmp_path, arquivos, cfg=None):
    for nome, corpo in arquivos.items():
        alvo = tmp_path / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return rodar(tmp_path, cfg)


# ==================================================== o caso correto não dispara
def test_backend_conforme_nao_dispara_nenhum_fundador():
    """Vale mais que os cinco testes de caminho feliz somados. Um pipeline
    que anonimiza antes de restaurar, concede por coluna, cifra com chave
    de KMS, destrói chave por titular e escreve em sa-east-1 é exatamente o
    comportamento que os checks querem produzir."""
    res = rodar(BOM)
    for cid in FUNDADORES:
        assert not acha(res, cid), [
            (f.arquivo, f.linha, f.titulo) for f in acha(res, cid)]
        assert cid in res["checks_executados"], (
            f"{cid} não chegou a executar — verde por não ter olhado")


# ==================================================== S-14
@pytest.mark.pse_security
def test_s14_dump_de_producao_em_staging():
    res = rodar(RUIM)
    s14 = acha(res, "S-14")
    assert s14, "restaurou dump de produção em staging cru e passou"
    assert "refresh-staging.sh" in s14[0].arquivo
    assert s14[0].linha


@pytest.mark.pse_security
def test_s14_pseudonimizacao_no_mesmo_script_desliga(tmp_path):
    """D-08: o passo que descaracteriza, executando antes do restore, é o
    caminho correto — e é o que o check quer que exista."""
    res = escrever(tmp_path, {"r.sh":
                              "pg_dump $PROD_URL > d.sql\n"
                              "python anonimizar.py d.sql d_anon.sql\n"
                              "psql $STAGING_URL < d_anon.sql\n"})
    assert not acha(res, "S-14"), [f.titulo for f in acha(res, "S-14")]


@pytest.mark.pse_security
def test_s14_backup_de_prod_para_prod_nao_dispara(tmp_path):
    """Sem ambiente inferior no destino não há travessia de fronteira —
    é só um backup, e punir backup seria ruído puro."""
    res = escrever(tmp_path, {"r.sh": "pg_dump $PROD_URL > /backups/prod.sql\n"})
    assert not acha(res, "S-14")


@pytest.mark.pse_security
def test_s14_seed_de_dev_nao_dispara(tmp_path):
    res = escrever(tmp_path, {"r.sh": "psql $DEV_URL < fixtures/seed_dev.sql\n"})
    assert not acha(res, "S-14")


@pytest.mark.pse_security
def test_s14_pega_no_pipeline_de_ci(tmp_path):
    """O restore quase nunca está num .sh: está no YAML do CI, que é onde
    ele roda com credencial de produção."""
    res = escrever(tmp_path, {".github/workflows/refresh.yml":
                              "jobs:\n  refresh:\n    steps:\n"
                              "      - run: psql $STAGING_URL < dumps/prod.sql\n"})
    assert acha(res, "S-14"), "restore no pipeline de CI passou"


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s14_comentario_nao_liga_nem_desliga(tmp_path):
    """D-01 nas duas direções: comentário citando o restore não cria achado,
    e comentário citando a anonimização não desliga o achado real."""
    res = escrever(tmp_path, {"r.sh":
                              "# psql $STAGING_URL < prod.sql (antigo)\n"
                              "# anonymize aplicado no gateway\n"
                              "psql $STAGING_URL < dump_prod.sql\n"})
    s14 = acha(res, "S-14")
    assert len(s14) == 1, [(f.linha, f.snippet) for f in s14]
    assert s14[0].linha == 3


# ==================================================== S-15
@pytest.mark.pse_security
def test_s15_grant_em_todas_as_tabelas():
    res = rodar(RUIM)
    s15 = acha(res, "S-15")
    assert s15, "GRANT SELECT ON ALL TABLES passou"
    texto = " ".join(f.titulo + f.descricao for f in s15).lower()
    assert "all tables" in texto or "todas" in texto


@pytest.mark.pse_security
def test_s15_all_privileges_tambem():
    res = rodar(RUIM)
    texto = " ".join(f.titulo.lower() for f in acha(res, "S-15"))
    assert "all privileges" in texto or "app_etl" in texto


@pytest.mark.pse_security
def test_s15_grant_por_coluna_nao_dispara(tmp_path):
    """D-08: a concessão por coluna é a minimização feita no lugar certo."""
    res = escrever(tmp_path, {"m.sql":
                              "GRANT SELECT (id, cidade) ON clientes "
                              "TO app_readonly;\n"})
    assert not acha(res, "S-15"), [f.titulo for f in acha(res, "S-15")]


@pytest.mark.pse_security
def test_s15_grant_em_tabela_com_pii_sem_coluna(tmp_path):
    """Nomear a tabela não basta quando a tabela inteira é PII: `SELECT ON
    clientes` entrega CPF a quem só precisava da cidade."""
    res = escrever(tmp_path, {
        "m.sql": "GRANT SELECT ON clientes TO app_readonly;\n",
        "catalog.yaml": "tables:\n  clientes:\n    fields:\n      cpf:\n"
                        "        class: personal\n        owner: o\n"
                        "        purpose: p\n        legal_basis: contrato\n"
                        "        retention_years: 5\n"})
    assert acha(res, "S-15")


@pytest.mark.pse_security
def test_s15_grant_em_tabela_sem_pii_nao_dispara(tmp_path):
    res = escrever(tmp_path, {
        "m.sql": "GRANT SELECT ON metricas TO app_readonly;\n",
        "catalog.yaml": "tables:\n  clientes:\n    fields:\n      cpf:\n"
                        "        class: personal\n        owner: o\n"
                        "        purpose: p\n        legal_basis: contrato\n"
                        "        retention_years: 5\n"})
    assert not acha(res, "S-15")


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s15_grant_em_comentario_nao_conta(tmp_path):
    res = escrever(tmp_path, {"m.sql":
                              "-- GRANT ALL PRIVILEGES ON clientes TO app;\n"
                              "SELECT 1;\n"})
    assert not acha(res, "S-15"), "GRANT comentado virou achado (D-01)"


# ==================================================== P-18
@pytest.mark.pse_privacy
def test_p18_sensivel_sem_cifra():
    res = rodar(RUIM)
    p18 = acha(res, "P-18")
    assert p18, "campo sensível persistido sem cifra de aplicação e passou"
    campos = " ".join(f.titulo for f in p18)
    assert "genero" in campos and "biometria" in campos
    assert "cpf" not in campos, "campo pessoal comum não é escopo de P-18"


@pytest.mark.pse_privacy
def test_p18_cifra_com_chave_gerenciada_nao_dispara():
    res = rodar(BOM)
    assert not acha(res, "P-18"), [f.titulo for f in acha(res, "P-18")]


@pytest.mark.pse_privacy
def test_p18_cifra_sem_gerencia_de_chave_ainda_dispara(tmp_path):
    """Cifrar com chave que a própria aplicação guarda não protege de um
    dump: o dump leva a chave junto. A gerência é metade do controle."""
    res = escrever(tmp_path, {
        "catalog.yaml": "tables:\n  t:\n    fields:\n      genero:\n"
                        "        class: sensitive\n        owner: o\n"
                        "        purpose: p\n        legal_basis: consentimento\n"
                        "        retention_years: 2\n"
                        "        encryption:\n          algorithm: AES-256-GCM\n"})
    p18 = acha(res, "P-18")
    assert p18, "cifra sem gerência de chave declarada passou"
    assert "chave" in p18[0].descricao.lower()


@pytest.mark.pse_privacy
def test_p18_cifra_aplicada_no_codigo_desliga(tmp_path):
    """A outra metade do D-08: quem cifra no código e não declarou no
    catálogo já protege o dado — o achado seria sobre a declaração, e disso
    cuida P-04."""
    res = escrever(tmp_path, {
        "catalog.yaml": "tables:\n  t:\n    fields:\n      genero:\n"
                        "        class: sensitive\n        owner: o\n"
                        "        purpose: p\n        legal_basis: consentimento\n"
                        "        retention_years: 2\n",
        "modelo.py": "from kms import kms_encrypt\n\n\n"
                     "def salvar(genero):\n"
                     "    return db.save(kms_encrypt(genero))\n"})
    assert not acha(res, "P-18"), [f.titulo for f in acha(res, "P-18")]


@pytest.mark.pse_privacy
def test_p18_sem_catalogo_e_pulado(tmp_path):
    res = escrever(tmp_path, {"a.py": "x = 1\n"})
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "P-18" in pulados and "P-04" in pulados["P-18"]


# ==================================================== P-19
@pytest.mark.pse_privacy
def test_p19_evento_com_pii_sem_crypto_shredding():
    res = rodar(RUIM)
    p19 = acha(res, "P-19")
    assert p19, "PII em tópico append-only sem estratégia de destruição passou"
    assert "eventos.py" in p19[0].arquivo and p19[0].linha


@pytest.mark.pse_privacy
def test_p19_crypto_shredding_desliga():
    res = rodar(BOM)
    assert not acha(res, "P-19"), [f.titulo for f in acha(res, "P-19")]


@pytest.mark.pse_privacy
def test_p19_evento_sem_pii_nao_dispara(tmp_path):
    res = escrever(tmp_path, {"e.py":
                              "from kafka import KafkaProducer\n\n"
                              "producer = KafkaProducer()\n\n\n"
                              "def f(pedido):\n"
                              "    producer.send('pedidos', "
                              "{'id': pedido.id, 'valor': pedido.valor})\n"})
    assert not acha(res, "P-19")


@pytest.mark.pse_privacy
def test_p19_sem_barramento_e_pulado(tmp_path):
    res = escrever(tmp_path, {"a.py": "def f(cpf):\n    return db.save(cpf)\n"})
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "P-19" in pulados and pulados["P-19"]


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_p19_comentario_de_shredding_nao_desliga(tmp_path):
    res = escrever(tmp_path, {"e.py":
                              "from kafka import KafkaProducer\n\n"
                              "producer = KafkaProducer()\n\n\n"
                              "def f(c):\n"
                              "    # crypto_shred previsto para o Q3\n"
                              "    producer.send('clientes', {'cpf': c.cpf})\n"})
    assert acha(res, "P-19"), "comentário citando crypto_shred desligou o check"


# ==================================================== S-16
@pytest.mark.pse_security
def test_s16_persistencia_fora_da_residencia_declarada():
    res = rodar(RUIM)
    s16 = acha(res, "S-16")
    assert s16, "política declara BR e a escrita vai para us-east-1"
    texto = " ".join(f.titulo + f.descricao for f in s16)
    assert "us-east-1" in texto and "BR" in texto


@pytest.mark.pse_security
def test_s16_regiao_nacional_nao_dispara():
    res = rodar(BOM)
    assert not acha(res, "S-16"), [f.titulo for f in acha(res, "S-16")]


@pytest.mark.pse_security
def test_s16_sem_politica_declarada_e_pulado(tmp_path):
    """Sem residência declarada não há promessa a confrontar. Inventar uma
    (supor BR porque a LGPD é brasileira) seria a suite decidindo pelo
    consumidor uma coisa que é dele."""
    res = escrever(tmp_path,
                   {"p.py": "import boto3\n"
                            "s3 = boto3.client('s3', region_name='us-east-1')\n"},
                   cfg={"catalog_path": "catalog.yaml"})
    pulados = {c["id"]: c["motivo"] for c in res["checks_pulados"]}
    assert "S-16" in pulados and "residencia" in pulados["S-16"].lower()


@pytest.mark.pse_security
@pytest.mark.mordida
def test_s16_regiao_em_comentario_nao_conta(tmp_path):
    res = escrever(tmp_path, {"p.py":
                              "import boto3\n"
                              "# migrar para us-east-1 no Q4\n"
                              "s3 = boto3.client('s3', region_name='sa-east-1')\n"})
    assert not acha(res, "S-16"), "região citada em comentário virou achado"


# ==================================================== o estrato como um todo
def test_os_cinco_estao_no_dominio_backend():
    from pse import catalogo
    for cid in FUNDADORES:
        assert "backend" in catalogo.dominios(cid), catalogo.dominios(cid)
        assert catalogo.meta(cid)["status"] == "implementado"


def test_prefixo_segue_o_pilar():
    from pse import catalogo
    assert catalogo.pilar_esperado("S-14") == "security"
    assert catalogo.pilar_esperado("P-18") == "privacy"
    assert catalogo.incoerencias_de_prefixo() == []


def test_cada_fundador_tem_mutacao_canonica():
    from pse.mutacao import provar
    for cid in FUNDADORES:
        r = provar(cid)
        assert r["ok"], r["motivo"]


@pytest.mark.mordida
def test_arquivo_que_nao_parseia_e_indeterminado(tmp_path):
    (tmp_path / "catalog.yaml").write_text("tables: {}\n", encoding="utf-8")
    (tmp_path / "e.py").write_text("def f(:\n    pass\n", encoding="utf-8")
    res = rodar(tmp_path)
    indet = {c["id"] for c in res["checks_indeterminados"]}
    assert {"P-19", "S-16"} <= indet, res["checks_executados"]


@pytest.mark.mordida
def test_fixture_ruim_derruba_o_gate():
    rc = main(["--path", str(RUIM), "--domain", "backend",
               "--config", str(RUIM / "pse-config.yaml")])
    assert rc in (10, 11), rc


@pytest.mark.mordida
def test_fixture_conforme_e_verde_no_estrato_inteiro(tmp_path):
    out = tmp_path / "l.json"
    rc = main(["--path", str(BOM), "--domain", "backend",
               "--config", str(BOM / "pse-config.yaml"), "--output", str(out)])
    laudo = json.loads(out.read_text(encoding="utf-8"))
    assert rc == 0, [(f["check_id"], f["titulo"]) for f in laudo["findings"]] + \
        laudo["checks_indeterminados"]
