"""As nove ratificações, seladas pelo COMPORTAMENTO e não pela prosa.

`docs/RATIFICACOES.md` afirma que nove decisões de contrato estão fechadas.
Uma tabela que afirma isso e não é verificada é pior que tabela nenhuma: ela
parece autoridade. Cada linha daquele documento tem aqui o teste que a torna
verdadeira — se o comportamento mudar, a linha vira falsa e este arquivo
reprova.

Nenhum destes testes é novo em substância: os comportamentos já tinham
prova nos módulos de origem. O que muda é o ENDEREÇO — a partir daqui, quem
quiser saber o que foi ratificado lê um documento e roda um arquivo.
"""
import tempfile
from pathlib import Path

import pytest

from pse.engine.runner import executar
from pse.model import CheckIndeterminado, Severidade
from pse.trabalho_a.autorizacao import e_loopback, host_e_loopback

RAIZ = Path(__file__).resolve().parent.parent
LEDGER = RAIZ / "docs" / "RATIFICACOES.md"
CATALOGO_CIFRADO = (
    "tables:\n  t:\n    fields:\n      cpf:\n        class: sensitive\n"
    "        encryption:\n          algorithm: aes-256-gcm\n"
    "          key_management: aws-kms\n")


def escrever(arquivos, cfg=None):
    d = Path(tempfile.mkdtemp())
    for nome, corpo in arquivos.items():
        alvo = d / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return executar(d, {"privacy", "security"}, cfg or {})


def acha(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


# ------------------------------------------------------------ 1 e 2
def test_r02_loopback_casa_host_exato_nunca_substring():
    """Ratificação 2. `http://` só é aceito com host de loopback EXATO."""
    for bom in ("http://127.0.0.1:5178/", "http://localhost:8000/",
                "http://[::1]:9000/"):
        assert e_loopback(bom), bom
    for mau in ("http://127.0.0.1.atacante.com/", "http://localhost.evil.io/",
                "https://api.exemplo.com/"):
        assert not e_loopback(mau), mau


def test_r02_o_host_de_loopback_independe_do_esquema():
    assert host_e_loopback("https://127.0.0.1:8443/")
    assert not host_e_loopback("https://127.0.0.1.exemplo.com/")


def _config(base_url, **auth):
    att = {"attested_by": "dono@exemplo.test", "scope": ["pse_passive"],
           "expires": "2030-01-01"}
    att.update(auth)
    return {"target": {"base_url": base_url, "environment": "staging",
                       "authorization": att}}


def test_r01_local_target_e_exigido_em_loopback():
    """Ratificação 1. Sem o degrau, loopback é indeterminado — nunca uma
    porta aberta sem registro."""
    from pse.trabalho_a.autorizacao import validar_atestacao
    with pytest.raises(CheckIndeterminado) as e:
        validar_atestacao(_config("http://127.0.0.1:7878"), "pse_passive")
    assert "local_target" in str(e.value)


def test_r01_local_target_em_alvo_publicado_e_entrada_invalida():
    from pse.model import EntradaInvalida
    from pse.trabalho_a.autorizacao import validar_config
    with pytest.raises(EntradaInvalida):
        validar_config(_config("https://app.exemplo.com", local_target=True),
                       "pse_passive")


def test_r01_loopback_COM_o_degrau_passa():
    """A mordida: se o degrau não abrisse caminho nenhum, ele seria só um
    bloqueio, e a camada dinâmica não teria como rodar contra alvo local."""
    from pse.trabalho_a.autorizacao import validar_atestacao
    validar_atestacao(_config("http://127.0.0.1:7878", local_target=True),
                      "pse_passive")


# ------------------------------------------------------------ 3 e 4
def test_r03_p24_e_do_pilar_privacy():
    from pse import catalogo
    assert catalogo.CATALOGO["P-24"]["pack"] == "privacy"


def test_r04_s14_e_s15_permanecem_alto():
    """Ratificação 4. `CRÍTICO` fica reservado ao que já é exposição
    consumada; dump entre ambientes e GRANT amplo são graves e não são
    isso."""
    from pathlib import Path as _P
    for arq in ("s14_dump_de_producao.py", "s15_grant_excessivo.py"):
        fonte = (RAIZ / "pse" / "checks" / "security" / arq).read_text(
            encoding="utf-8")
        assert "Severidade.CRITICO" not in fonte, arq
        assert "Severidade.ALTO" in fonte, arq


# ------------------------------------------------------------ 5 e 6
def test_r05_env_bang_bloqueia_e_env_var_decide():
    ind = escrever({"src/a.rs": 'fn f() { let api_key = env!("K"); }\n'})
    assert "S-06" in {c["id"] for c in ind["checks_indeterminados"]}
    assert not acha(ind, "S-06")

    ok = escrever({"src/a.rs":
                   'fn f() { let api_key = std::env::var("K").unwrap(); }\n'})
    assert "S-06" not in {c["id"] for c in ok["checks_indeterminados"]}
    assert not acha(ok, "S-06")


def test_r06_critico_textual_so_com_formato_conhecido():
    conhecido = escrever({"src/a.rs":
                          'fn f() { let api_key = "AKIAQ4F7X2VNBM3JZR5T"; }\n'})
    assert any(f.severidade == Severidade.CRITICO
               for f in acha(conhecido, "S-06"))

    desconhecido = escrever({"src/a.rs": 'fn f() { let api_secret = "'
                             + "9f3b" * 12 + '"; }\n'})
    achados = acha(desconhecido, "S-06")
    assert achados and all(f.severidade == Severidade.ALTO for f in achados)


# ------------------------------------------------------------ 7
def test_r07_embrulho_de_cifra_opaco_bloqueia():
    res = escrever({
        "catalog.yaml": CATALOGO_CIFRADO,
        "src/a.rs": 'fn to_ciphertext(v: &str) -> Vec<u8> { v.as_bytes().to_vec() }\n'
                    'fn g(p: &PgPool, t: &Titular) {\n'
                    '    let blob = to_ciphertext(&t.cpf);\n'
                    '    sqlx::query("INSERT INTO t (cpf) VALUES ($1)")'
                    '.bind(&blob).execute(p);\n}\n'},
        cfg={"catalog_path": "catalog.yaml"})
    assert "P-18" in {c["id"] for c in res["checks_indeterminados"]}
    assert not acha(res, "P-18")


# ------------------------------------------------------------ 8
def test_r08_achado_e_indeterminacao_coexistem():
    res = escrever({
        "src/quebrado.ts": "export const x = <<<>>> ;;;\n",
        "src/Tela.tsx": "export function T({ cpf }: { cpf: string }) {\n"
                        "  localStorage.setItem('cpf', cpf);\n"
                        "  return <div/>;\n}\n"})
    assert acha(res, "P-14"), "o achado do arquivo legível se perdeu"
    assert "P-14" in {c["id"] for c in res["checks_indeterminados"]}


def test_r08_a_excecao_carrega_os_achados():
    assert CheckIndeterminado("x").achados == []
    assert CheckIndeterminado("y", achados=[1]).achados == [1]


# ------------------------------------------------------------ 9
def test_r09_a_observacao_declara_superficie_e_quem_serviu():
    from pse.navegador.rede import NetworkLog, RecursoObservado
    marcas = ("/@vite/client",)
    log = NetworkLog(url="http://127.0.0.1:5179/", engine="chromium",
                     recursos=(RecursoObservado(
                         url="http://127.0.0.1:5179/@vite/client", status=200),))
    d = log.sanitizado(marcas)
    assert d["superficie_observada"]
    assert d["servidor_de_desenvolvimento"] is True


# ------------------------------------------------------------ 10
def test_r10_declarado_e_observado_sao_campos_separados():
    """Ratificação 10. A suíte NÃO descobre sozinha contra que artefato mede."""
    from pse.navegador.rede import NetworkLog, RecursoObservado
    limpo = NetworkLog(url="https://app.exemplo.test/", engine="chromium")
    d = limpo.sanitizado(("/@vite/client",), "producao")
    assert d["artefato_declarado"] == "producao"
    assert d["servidor_de_desenvolvimento"] is False
    assert "contradicao_de_artefato" not in d


def test_r10_producao_declarada_sobre_dev_observado_e_contradicao():
    from pse.navegador.rede import NetworkLog, RecursoObservado
    log = NetworkLog(url="http://127.0.0.1:5178/", engine="chromium",
                     recursos=(RecursoObservado(
                         url="http://127.0.0.1:5178/@vite/client", status=200),))
    assert "contradicao_de_artefato" in log.sanitizado(("/@vite/client",),
                                                       "producao")


def test_r10_valor_fora_da_lista_e_exit_30():
    from pse.model import EntradaInvalida
    from pse.trabalho_a.autorizacao import validar_config
    with pytest.raises(EntradaInvalida):
        validar_config({"target": {"base_url": "https://a.test",
                                   "environment": "staging",
                                   "artefato": "prod"}}, "pse_passive")


def test_r10_nada_declarado_nao_vira_producao_por_inferencia():
    from pse.navegador.rede import NetworkLog
    d = NetworkLog(url="https://app.exemplo.test/",
                   engine="chromium").sanitizado(("/@vite/client",))
    assert d["artefato_declarado"] == "nao_declarado"


# ------------------------------------------ o documento e o código não divergem
def test_o_ledger_lista_exatamente_as_dez():
    texto = LEDGER.read_text(encoding="utf-8")
    tabela = [l for l in texto.splitlines()
              if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
    assert len(tabela) == 10, f"o ledger tem {len(tabela)} linhas numeradas"
    numeros = [int(l.split("|")[1].strip()) for l in tabela]
    assert numeros == list(range(1, 11)), numeros


def test_cada_ratificacao_nomeia_a_versao_de_origem():
    """Ratificação sem versão de origem perde a rastreabilidade: não se sabe
    o que estava em jogo quando a decisão foi tomada."""
    import re
    texto = LEDGER.read_text(encoding="utf-8")
    tabela = [l for l in texto.splitlines()
              if l.startswith("| ") and l.split("|")[1].strip().isdigit()]
    for linha in tabela:
        assert re.search(r"v0\.\d+\.\d+", linha), linha


def test_o_ledger_nao_apaga_a_pendencia_do_manifesto():
    """Manifesto é o registro do que se sabia naquele momento. Apagar dele a
    seção de pendências — para "não repetir" o que o ledger já diz —
    falsificaria a história que ele existe para guardar.

    (O manifesto PODE conter a palavra "ratificado" em outros contextos: a
    v0.11.0 fala de `CONTRATO RATIFICADO` sobre outra coisa. O que se vigia
    é a seção, não a palavra.)
    """
    com_secao = [m.name for m in RAIZ.glob("MANIFESTO-v*.md")
                 if "PENDENCIAS DE RATIFICACAO" in
                 m.read_text(encoding="utf-8")]
    assert len(com_secao) >= 5, (
        f"só {len(com_secao)} manifesto(s) mantêm a seção de pendências — "
        f"o histórico está sendo reescrito")


def test_o_que_segue_pendente_nao_esta_vazio():
    """Zero pendência num projeto vivo é sinal de que alguém parou de
    registrar, não de que tudo foi decidido."""
    texto = LEDGER.read_text(encoding="utf-8")
    corpo = texto.split("## O que segue pendente")[-1]
    assert corpo.count("|") > 6, "seção de pendências vazia"
