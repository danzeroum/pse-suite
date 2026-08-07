"""O alcance textual ancorado a Rust — S-06, P-18, P-19, S-16.

A decisao que originou este alcance esta medida em `docs/cobertura-btv.md`:
nao houve parser de Rust, e nao deve haver. Houve alcance a QUATRO vetores
por padrao textual ancorado, e a fronteira entre "alcanca quatro vetores" e
"le a linguagem" e exatamente o que estes testes vigiam.

Sem arvore, a fragilidade e maior — entao a politica declarada e PRECISAO
SOBRE RECALL. Um falso-positivo num alvo real ensina o time a ignorar o
pack inteiro, e o custo disso e maior que o do achado perdido. Metade dos
testes daqui existe para provar que o caso CORRETO em Rust nao dispara.
"""
from pathlib import Path

import pytest

from pse.engine import rustscan
from pse.engine.runner import executar
from pse.model import CheckIndeterminado

FIX = Path(__file__).parent / "fixtures"
RUIM, BOM = FIX / "consumidor_rust_ruim", FIX / "consumidor_rust_bom"
CFG = {"catalog_path": "catalog.yaml", "data_residency": "BR"}
OS_QUATRO = ("S-06", "P-18", "P-19", "S-16")


def rodar(caminho, cfg=None):
    return executar(caminho, {"privacy", "security"}, CFG if cfg is None else cfg)


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


def escrever(tmp_path, arquivos, cfg=None):
    for nome, corpo in arquivos.items():
        alvo = tmp_path / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return rodar(tmp_path, cfg)


CATALOGO_CIFRADO = """
tables:
  titulares:
    fields:
      cpf:
        class: sensitive
        encryption:
          algorithm: aes-256-gcm
          key_management: aws-kms
"""


# ============================================ o caso correto nao dispara
def test_consumidor_rust_bom_nao_dispara_nenhum_dos_quatro():
    """Vale mais que os quatro testes de caminho feliz somados.

    Chave vinda de `std::env::var` e de cofre, campo cifrado com AES-GCM e
    chave de KMS, evento com crypto-shredding, regiao em `sa-east-1`: e
    exatamente o comportamento que os quatro checks querem produzir. Puni-lo
    seria o D-08 ao contrario, e num alcance textual — o mais fragil da
    suite — e o erro mais provavel.
    """
    res = rodar(BOM)
    for cid in OS_QUATRO:
        assert not acha(res, cid), [
            (f.titulo, f.arquivo, f.linha) for f in acha(res, cid)]


def test_consumidor_rust_ruim_dispara_os_quatro():
    res = rodar(RUIM)
    for cid in OS_QUATRO:
        assert acha(res, cid), f"{cid} nao mordeu a fixture ruim"


# ======================================================== D-01: o comentario
def test_credencial_em_comentario_nao_dispara():
    """A ancora e o FATO, nunca a mencao. `// let api_key = "AKIA..."` num
    comentario e o vigiado escrevendo o que quiser."""
    res = escrever(Path(pytest.importorskip("tempfile").mkdtemp()), {
        "src/a.rs": '// let api_key = "AKIAQ4F7X2VNBM3JZR5T";\n'
                    '/// doc: let secret = "sk-live-aaaaaaaaaaaaaaaaaaaa";\n'
                    '/* bloco /* aninhado */ let token = "ghp_'
                    + "a" * 36 + '"; */\n'
                    'fn main() {}\n'})
    assert not acha(res, "S-06")


def test_comentario_de_bloco_aninhado_nao_deixa_vazar_codigo():
    """Rust permite `/* a /* b */ c */`. Um apagador que pare no primeiro
    `*/` deixaria ` c */` valendo como codigo — e um segredo comentado
    voltaria a ser fato."""
    texto = '/* /* dentro */ let api_key = "' + "z" * 40 + '"; */\nfn f() {}\n'
    assert "api_key" not in rustscan.efetivo(texto)
    assert not list(rustscan.ligacoes(texto))


def test_tempo_de_vida_nao_e_literal_de_caractere():
    """`&'a str` comeca com aspa simples. Um apagador generico engoliria
    tudo ate a proxima aspa e apagaria codigo real — errando para MENOS
    achado, em silencio."""
    texto = "fn f<'a>(s: &'a str) -> &'a str {\n" \
            '    let api_key = "' + "q" * 40 + '";\n    s\n}\n'
    efetivo = rustscan.efetivo(texto)
    assert "&'a str" in efetivo
    nomes = [x.nome for x in rustscan.ligacoes(texto)]
    assert "api_key" in nomes


def test_string_crua_nao_desalinha_o_resto_do_arquivo():
    texto = 'const SQL: &str = r#"SELECT "a" FROM t;"#;\n' \
            'let access_token = "' + "w" * 40 + '";\n'
    ligs = {x.nome: x for x in rustscan.ligacoes(texto)}
    assert ligs["SQL"].literal == 'SELECT "a" FROM t;'
    assert ligs["access_token"].linha == 2


# ================================================= D-08: o correto nao dispara
def test_chave_vinda_do_ambiente_nao_e_hardcoded():
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() {\n'
                    '    let api_key = std::env::var("API_KEY").unwrap();\n'
                    '    let client_secret = env::var("S").unwrap();\n}\n'})
    assert not acha(res, "S-06")


def test_placeholder_nao_e_segredo():
    """Punir o exemplo que o time deixou de proposito e o D-08 ao contrario."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() {\n'
                    '    let api_key = "changeme-antes-do-deploy-por-favor";\n'
                    '    let secret = "your-key-goes-right-here-ok";\n}\n'})
    assert not acha(res, "S-06")


def test_literal_curto_nao_vira_credencial():
    """Minimo mais alto que o de Python de proposito: sem arvore, cada
    caractere a menos e um falso-positivo a mais."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() { let token = "abc123"; }\n'})
    assert not acha(res, "S-06")


def test_nome_parecido_nao_vira_credencial():
    """`keyboard` nao pode satisfazer `key` — a mesma disciplina de
    `nome_casa`, onde a fragilidade e maior por nao haver arvore."""
    assert not rustscan.contem_token("let keyboard = 1", ["key"])
    assert rustscan.contem_token("let api_key = 1", ["api_key"])


# ================================================= severidade conservadora
def test_formato_conhecido_e_critico_e_o_resto_e_alto():
    """CRITICO so quando o literal casa com um FORMATO conhecido (AKIA, sk-,
    ghp_, PEM): ai o casamento textual nao introduz ambiguidade. Nome de
    credencial com literal longo de formato desconhecido e ALTO —
    provavelmente e chave, e *provavelmente* nao merece o grau maximo num
    alcance sem arvore."""
    from pse.model import Severidade
    res = rodar(RUIM)
    por_titulo = {f.titulo: f for f in acha(res, "S-06")}
    critico = [f for f in por_titulo.values() if f.severidade == Severidade.CRITICO]
    alto = [f for f in por_titulo.values() if f.severidade == Severidade.ALTO]
    assert critico and all("api_key" in f.titulo for f in critico)
    assert alto and all("webhook_secret" in f.titulo for f in alto)


def test_nenhum_critico_sai_de_literal_sem_formato_conhecido():
    """A trava da politica: em Rust, texto sem formato reconhecido nunca
    chega a CRITICO."""
    import tempfile
    from pse.model import Severidade
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() { let api_secret = "'
                    + "9f3b" * 12 + '"; }\n'})
    achados = acha(res, "S-06")
    assert achados
    assert all(f.severidade == Severidade.ALTO for f in achados)


# ====================================================== a ambiguidade bloqueia
def test_macro_de_compilacao_vira_indeterminado_nunca_achado():
    """`env!("API_KEY")` grava o valor no BINARIO em tempo de compilacao —
    nao le o ambiente em execucao. Pode ou nao ser o vetor, e o alcance
    textual nao tem como decidir. Achado seria inventar; verde seria
    conveniencia."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() { let api_key = env!("API_KEY"); }\n'})
    assert not acha(res, "S-06")
    ind = {c["id"]: c["motivo"] for c in res["checks_indeterminados"]}
    assert "S-06" in ind
    assert "env" in ind["S-06"] and "COMPILACAO" in ind["S-06"]


def test_include_str_tambem_e_ambiguo():
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() { let secret = include_str!("../k.txt"); }\n'})
    ind = {c["id"] for c in res["checks_indeterminados"]}
    assert "S-06" in ind and not acha(res, "S-06")


def test_env_var_de_execucao_nao_e_ambiguo():
    """A mordida do teste acima: `std::env::var` le em EXECUCAO e e
    decidivel — se tudo virasse indeterminado, o gate seria inutil."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() { let api_key = std::env::var("K").unwrap(); }\n'})
    assert "S-06" not in {c["id"] for c in res["checks_indeterminados"]}
    assert not acha(res, "S-06")


# =============================================================== P-18 em Rust
def test_p18_pega_o_vao_entre_catalogo_e_motor():
    """O caso que so o `.rs` revela: o catalogo promete `encryption` com
    `key_management` — o braco declarativo fica quieto — e o motor grava o
    campo em claro. Declaracao e fato divergindo e pior que ausencia de
    declaracao: quem le o catalogo confia numa protecao que nao executa."""
    res = rodar(RUIM)
    f = acha(res, "P-18")
    assert len(f) == 1
    assert f[0].arquivo.endswith(".rs")
    assert "declarado cifrado" in f[0].titulo


def test_p18_nao_duplica_o_achado_declarativo():
    """Dois achados para o mesmo campo seriam ruido, e ruido ensina o time a
    ignorar o pack. O braco Rust so fala de campo que o catalogo ja deu por
    cifrado."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "catalog.yaml": "tables:\n  t:\n    fields:\n      cpf:\n"
                        "        class: sensitive\n",
        "src/a.rs": 'fn f(p: &Pool, cpf: &str) {\n'
                    '    sqlx::query("INSERT").bind(cpf).execute(p);\n}\n'})
    achados = acha(res, "P-18")
    assert len(achados) == 1
    assert not achados[0].arquivo.endswith(".rs")


def test_p18_cifra_em_rust_suprime_o_achado_do_catalogo():
    """D-08: consumidor cujo motor Rust cifra de verdade nao pode ser punido
    por o catalogo nao declarar. Punir quem protegeu e o pior sinal que uma
    suite pode mandar."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "catalog.yaml": "tables:\n  t:\n    fields:\n      cpf:\n"
                        "        class: sensitive\n",
        "src/a.rs": 'fn f(cpf: &str) {\n'
                    '    let c = aes_gcm::encrypt(&chave(), cpf);\n}\n'})
    assert not acha(res, "P-18")


# =============================================================== P-19 em Rust
def test_p19_pega_producao_de_evento_com_pii_em_rust():
    res = rodar(RUIM)
    f = acha(res, "P-19")
    assert len(f) == 1 and f[0].arquivo.endswith(".rs")
    assert "cpf" in f[0].titulo


def test_p19_resolve_um_salto_de_ligacao():
    """Idiomatico em Rust: o payload e montado numa ligacao e so o nome
    entra na chamada. Sem o salto, o braco textual acharia zero PII no caso
    mais comum e diria que esta limpo."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'use rdkafka::producer::FutureProducer;\n'
                    'fn f(producer: &FutureProducer, cpf: &str) {\n'
                    '    let payload = format!("{{\\"cpf\\":\\"{}\\"}}", cpf);\n'
                    '    producer.send(FutureRecord::to("t").payload(&payload), 0);\n'
                    '}\n'})
    assert acha(res, "P-19")


def test_p19_crypto_shredding_em_rust_suprime():
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'use rdkafka::producer::FutureProducer;\n'
                    'fn f(producer: &FutureProducer, cpf: &str) {\n'
                    '    producer.send(FutureRecord::to("t").key(cpf), 0);\n}\n'
                    'fn destroy_key(t: &str) {}\n'})
    assert not acha(res, "P-19")


def test_p19_shredding_dentro_de_string_nao_suprime():
    """D-01 na supressao: `"crypto_shred"` numa mensagem de log nao destroi
    chave nenhuma."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'use rdkafka::producer::FutureProducer;\n'
                    'fn f(producer: &FutureProducer, cpf: &str) {\n'
                    '    let msg = "crypto_shred previsto para o Q3";\n'
                    '    producer.send(FutureRecord::to("t").key(cpf), 0);\n}\n'})
    assert acha(res, "P-19")


# =============================================================== S-16 em Rust
def test_s16_pega_regiao_em_chamada_de_conexao_rust():
    res = rodar(RUIM)
    f = acha(res, "S-16")
    assert f and all(x.arquivo.endswith(".rs") for x in f)
    assert all("us-east-1" in x.titulo for x in f)


def test_s16_regiao_dentro_da_politica_nao_dispara():
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() { let r = Region::new("sa-east-1"); }\n'})
    assert not acha(res, "S-16")


def test_s16_regiao_solta_fora_de_chamada_nao_dispara():
    """A ancora e a CHAMADA. Um `const REGION: &str = "us-east-1"` solto nao
    prova que algo persiste la — precisao sobre recall."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'const REGION: &str = "us-east-1";\nfn f() {}\n'})
    assert not acha(res, "S-16")


def test_s16_sem_politica_declarada_continua_pulando():
    """Supor `BR` porque a LGPD e brasileira seria a suite decidindo pelo
    consumidor. O alcance a Rust nao muda isso."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'fn f() { let r = Region::new("us-east-1"); }\n'},
        cfg={"catalog_path": "catalog.yaml"})
    assert not acha(res, "S-16")
    assert "S-16" in {c["id"] for c in res["checks_pulados"]}


# ================================== o alcance nao contamina os outros checks
def test_nenhum_outro_check_passa_a_ler_rust():
    """A fronteira que este alcance nao pode cruzar. Se um quinto check
    comecasse a olhar `.rs` sem entrar na lista declarada, o laudo passaria
    a afirmar cobertura que o bloco `alcance` nao registra — e a cobertura
    de fachada voltaria pela porta dos fundos."""
    from pse import alcance
    declarados = set(alcance.ALCANCE_PARCIAL[".rs"][2])
    assert declarados == set(OS_QUATRO)

    fonte = Path(__file__).resolve().parent.parent / "pse" / "checks"
    usam_rust = set()
    for p in fonte.rglob("*.py"):
        if p.name.startswith("_"):
            continue
        texto = p.read_text(encoding="utf-8")
        if "_rust" in texto or "rustscan" in texto:
            usam_rust.add(p.stem.split("_")[0].upper().replace("P", "P-", 1)
                          if False else p.stem[:3].upper())
    esperados = {c.replace("-", "").upper()[:3] for c in OS_QUATRO}
    assert usam_rust == esperados, (
        f"checks que importam o alcance a Rust: {sorted(usam_rust)}; "
        f"declarados em ALCANCE_PARCIAL: {sorted(esperados)}")


def test_rust_nao_entra_em_com_parser():
    """A suite NAO le Rust, e o dia em que `.rs` aparecer em COM_PARSER o
    laudo passa a dizer *Rust: lido* — um leitor razoavel concluiria que os
    57 checks olharam o motor."""
    from pse import alcance
    assert ".rs" not in alcance.COM_PARSER
    assert ".rs" in alcance.ALCANCE_PARCIAL


def test_o_alcance_parcial_nao_conta_como_lido_na_proporcao():
    """Somar as linhas de alcance parcial ao lido faria a proporcao saltar e
    a suite mentiria por arredondamento."""
    from pse import cobertura
    volume = {"Rust": {"arquivos": 1, "linhas": 900, "lida": "parcial"},
              "Python": {"arquivos": 1, "linhas": 100, "lida": True}}
    p = cobertura.proporcao(volume)
    assert p["percentual_lido"] == 10.0
    assert p["percentual_alcance_parcial"] == 90.0
    assert p["linhas_lidas"] == 100


# ======================================================= a sonda de substrato
def test_a_sonda_so_empurra_para_nao_aplicavel():
    """Presenca de marca NAO e achado: significa que o vetor existe e que o
    check segue cego. Se a sonda pudesse produzir *auditado*, ela viraria a
    alegacao de cobertura que este mapa foi criado para impedir."""
    import tempfile
    from pse import cobertura
    from pse.engine.context import Contexto
    d = Path(tempfile.mkdtemp())
    (d / "a.rs").write_text("fn f() { tracing::info!(\"x\"); }\n", encoding="utf-8")
    sondas = cobertura.sondar_substrato(d, Contexto("/tmp").data)
    assert "P-01" not in sondas, "logger presente: P-01 nao pode virar N/A"
    assert "E-11" in sondas, "nenhum cliente de LLM: E-11 e nao-aplicavel aqui"


def test_a_sonda_ignora_comentario_e_literal():
    """`// TODO: chamar o modelo` nao prova que ha inferencia no motor."""
    import tempfile
    from pse import cobertura
    from pse.engine.context import Contexto
    d = Path(tempfile.mkdtemp())
    (d / "a.rs").write_text(
        '// TODO: openai prompt completion\n'
        'fn f() { let m = "openai chat_completion"; }\n', encoding="utf-8")
    sondas = cobertura.sondar_substrato(d, Contexto("/tmp").data)
    assert "E-11" in sondas, "mencao em comentario/literal virou substrato"


def test_sem_rust_nenhum_a_sonda_nao_opina():
    """Alvo sem `.rs` nao tem Rust nao-aplicavel: tem Rust inexistente, e o
    bloco `alcance` ja diz isso. Opinar aqui seria inventar estado."""
    import tempfile
    from pse import cobertura
    from pse.engine.context import Contexto
    assert cobertura.sondar_substrato(Path(tempfile.mkdtemp()),
                                      Contexto("/tmp").data) == {}


# ===================================================================
# O QUE A TRIAGEM DO btv REAL ENSINOU
#
# O primeiro alvo real nao produziu achado `.rs` nenhum — mas a triagem dos
# CANDIDATOS revelou quatro formas que o grep ancorado considerava e nao
# deveria. Nenhuma virou achado no btv por sorte: porque nenhum nome de PII
# caiu no span. Sorte nao e controle, e num repositorio cujo canal
# carregasse uma struct com `cpf` as quatro teriam disparado.
#
# Cada uma virou um caso permanente em `consumidor_rust_bom`.
# ===================================================================

def test_definicao_de_funcao_nao_e_chamada():
    """`fn append(&mut self, cpf: &str)` e DEFINICAO. A lista de parametros
    nao e um span de argumento, e um check que a varresse acusaria a
    PROPRIA ASSINATURA — um achado que nao tem como ser corrigido, porque
    nao ha defeito nenhum ali."""
    texto = ("pub fn append(&mut self, cpf: &str) {}\n"
             "pub fn connect(regiao: &str) {}\n"
             "fn f() { store.append(cpf); }\n")
    nomes = [c.nome for c in rustscan.chamadas(texto)]
    assert nomes == ["store.append"], nomes


def test_canal_tokio_nao_e_barramento_append_only():
    """`tx.send(...)` num modulo que menciona `ledger` era elegivel. O btv
    tem ledger no dominio: a marca aparecia em 18 arquivos e tornava
    elegivel todo `send` deles."""
    res = rodar(BOM)
    assert not acha(res, "P-19")


def test_canal_com_nome_sufixado_tambem_e_excluido():
    """`agent_evt_tx` — o nome idiomatico. O casamento por token exato nao
    alcancava o sufixo, e oito destes sobreviveram ao primeiro refino."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'use crate::ledger::L;\n'
                    'fn f(cpf: &str) {\n'
                    '    let _ = agent_evt_tx.send(cpf);\n'
                    '    let _ = input_tx.send(cpf);\n}\n'})
    assert not acha(res, "P-19")


def test_requisicao_http_nao_e_producao_de_evento():
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'use crate::ledger::L;\n'
                    'async fn f(cpf: &str) {\n'
                    '    let builder = client.post(url).body(cpf);\n'
                    '    let _ = builder.send().await;\n}\n'})
    assert not acha(res, "P-19")


def test_variante_de_enum_nao_e_chamada_de_metodo():
    """Em Rust idiomatico metodo e snake_case e variante e CamelCase."""
    import tempfile
    res = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'use crate::ledger::L;\n'
                    'fn f(cpf: &str) { let c = UiCommand::Send(cpf); }\n'})
    assert not acha(res, "P-19")


def test_o_refino_nao_cegou_o_verdadeiro_produtor():
    """A mordida dos quatro acima: se o refino tivesse ido longe demais, o
    produtor de verdade pararia de morder e a triagem teria trocado
    falso-positivo por falso-negativo — o defeito mais caro desta suite."""
    res = rodar(RUIM)
    assert acha(res, "P-19")
    import tempfile
    res2 = escrever(Path(tempfile.mkdtemp()), {
        "src/a.rs": 'use crate::ledger::LedgerRepository;\n'
                    'fn f(cpf: &str) { ledger.append(cpf); }\n'})
    assert acha(res2, "P-19"), "receptor que E barramento tem de continuar mordendo"


def test_a_triagem_esta_documentada():
    """Relatorio de triagem sem evidencia e opiniao. Cada achado (e cada
    nao-achado) do btv precisa aparecer com o trecho real."""
    doc = (Path(__file__).resolve().parent.parent / "docs" /
           "triagem-btv-rust.md").read_text(encoding="utf-8")
    for cid in OS_QUATRO:
        assert f"`{cid}`" in doc, cid
    for termo in ("VIOLACAO PROVAVEL", "FALSO-POSITIVO PROVAVEL", "INCERTO"):
        assert termo in doc, termo


def test_o_relatorio_de_triagem_nao_replica_segredo():
    """Sanitizacao vale tambem em triagem interna: o dado nao se replica em
    claro so porque o relatorio e nosso."""
    import re as _re
    doc = (Path(__file__).resolve().parent.parent / "docs" /
           "triagem-btv-rust.md").read_text(encoding="utf-8")
    from pse.engine.context import Contexto
    for padrao in Contexto("/tmp").data["rust"]["formatos_de_credencial"]:
        assert not _re.search(padrao, doc), (
            f"o relatorio de triagem carrega algo com forma de credencial "
            f"({padrao}) em claro")
