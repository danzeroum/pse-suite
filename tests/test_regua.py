"""D-13 — a regua curada e vigiada.

Em 1eb616b, remover `cpf` de pii-patterns.yaml deixava os 6 testes verdes:
a cobertura de P-01 encolhia em silencio. Era exatamente o cenario que o
README usa para justificar a regua morar neste repositorio.

Este modulo torna a edicao da regua *bloqueante*: remover um termo exige
alterar este teste no mesmo PR — visivel, versionado e revisavel. O
`catalog_hash` no laudo (Gap 3) faz a outra metade: torna a edicao
*evidente na evidencia*, mesmo que alguem altere teste e regua juntos.
"""
from pathlib import Path

import pytest

from pse.engine.context import Contexto

# Piso curado. Nao e a lista inteira — e o minimo que nao pode sumir sem
# que alguem assine embaixo. Acrescentar termos a regua nao quebra o teste;
# remover, sim.
PISO = {
    "pii-patterns": {
        "identificadores": {"cpf", "rg", "cnh", "passaporte", "cns", "titulo_eleitor"},
        "contato": {"email", "telefone", "celular", "endereco"},
        "credenciais": {"password", "senha", "token", "api_secret"},
    },
    "sensitive-fields": {
        "sensiveis": {"raca", "etnia", "religiao", "biometria", "saude",
                      "orientacao_sexual", "opiniao_politica",
                      "filiacao_sindical", "dado_genetico", "genero"},
    },
    "prohibited-filters": {
        "proxies_discriminacao": {"cep", "bairro", "nome_mae", "genero",
                                  "raca", "etnia"},
    },
}


# `credenciais` tem o piso INVERTIDO alem do normal: aqui, ACRESCENTAR termo
# encolhe a cobertura. Cada valor sintetico e uma credencial que a suite deixa
# de tratar como bloqueante, e inchar essa lista e a forma mais silenciosa de
# desligar P-06 e S-06 — mais silenciosa que apagar o check, porque os
# achados continuam saindo, em MEDIO, e o laudo parece o mesmo.
VALORES_QUE_NAO_PODEM_ENTRAR = {
    # Sequencia de digitos aparece dentro de segredo real com facilidade.
    # `123456` chegou a entrar e rebaixou as DUAS mutacoes canonicas.
    "123456", "1234567890", "0123456789", "000000", "111111",
    # Radicais curtos demais: casariam com metade dos segredos do mundo.
    "a", "ab", "abc", "key", "secret", "token", "pass", "pwd",
    # Marcas que descrevem AMBIENTE, nao valor descartavel. Um segredo de
    # staging e um segredo.
    "staging", "homolog", "dev", "local", "sandbox", "qa",
}


@pytest.fixture(scope="module")
def regua(tmp_path_factory):
    return Contexto(tmp_path_factory.mktemp("vazio")).data


@pytest.mark.parametrize("arquivo,grupo,esperado", [
    (a, g, termos) for a, grupos in PISO.items() for g, termos in grupos.items()
])
def test_piso_da_regua_intacto(regua, arquivo, grupo, esperado):
    presentes = set(regua[arquivo][grupo])
    faltando = esperado - presentes
    assert not faltando, (
        f"termo(s) removido(s) de pse/data/{arquivo}.yaml [{grupo}]: "
        f"{sorted(faltando)}. Remover da regua encolhe a cobertura dos checks "
        f"em silencio — se a remocao e intencional, altere o PISO neste teste "
        f"no mesmo PR, para que a decisao fique assinada."
    )


def test_terceiros_conhecidos_cobrem_as_tres_categorias(regua):
    cats = regua["third-party-endpoints"]["categorias"]
    assert {"analytics", "llm", "cdn"} <= set(cats)
    assert all(cats[c] for c in ("analytics", "llm", "cdn"))


def test_ignorar_nao_engole_host_real(regua):
    """A allowlist de hosts ignorados so pode conter dominios de exemplo.

    Um `ignorar: [amazonaws.com]` faria S-04 parar de ver metade da nuvem
    sem nenhum erro — a mesma classe de defeito que D-13.
    """
    permitidos = {"localhost", "127.0.0.1", "example.com", "example.org",
                  "example.net", "w3.org", "json-schema.org", "schema.org",
                  "localhost.localdomain"}
    excedente = set(regua["third-party-endpoints"]["ignorar"]) - permitidos
    assert not excedente, (
        f"hosts fora da lista de exemplos entraram em `ignorar`: {sorted(excedente)}"
    )


def test_ignorar_em_dependencias_nao_silencia_destino_real(regua):
    """E-13 tem lista propria de hosts ignorados (registro, licenca, doc).

    A trava: nenhum host das categorias conhecidas — analytics, llm, cdn —
    pode entrar nela. Senao bastaria mover `api.openai.com` para ca para o
    egresso de uma dependencia sumir do laudo sem ninguem notar.
    """
    dados = regua["third-party-endpoints"]
    dep = {h.lower() for h in dados.get("ignorar_em_dependencias", [])}
    assert dep, "lista de ignorados em dependencia vazia: E-13 vira ruido puro"
    conhecidos = {h.lower() for hosts in dados["categorias"].values() for h in hosts}
    intruso = dep & conhecidos
    assert not intruso, (
        f"host de categoria conhecida silenciado em ignorar_em_dependencias: "
        f"{sorted(intruso)}")


def test_llm_da_regua_alimenta_o_reconhecimento_do_e11(regua):
    """E-11 deriva os fornecedores que reconhece da categoria `llm`.

    Remover a categoria (ou esvazia-la) cega o check em silencio — por isso
    ela e vigiada aqui, e nao so no check.
    """
    from pse.checks.ethics import _llm

    class _Ctx:
        data = regua

    fornecedores = _llm.fornecedores(_Ctx())
    assert {"openai", "anthropic"} <= fornecedores, (
        f"fornecedores derivados da regua: {sorted(fornecedores)}")
    assert _llm.e_chamada_llm("openai.chat.completions.create", _Ctx(), False)
    assert _llm.e_chamada_llm("llm.complete", _Ctx(), False)
    assert not _llm.e_chamada_llm("db.create", _Ctx(), False)


def test_regua_do_frontend_e_vigiada(regua):
    """P-13/02/03 derivam da régua `frontend-terms`. Esvaziar um grupo aqui
    cega um check inteiro em silêncio — o mesmo defeito do D-13, num domínio
    novo."""
    fe = regua["frontend-terms"]
    piso = {
        "consentimento": {"consent", "consentimento", "aceito", "optin",
                          "cookies", "marketing"},
        "handlers_de_mudanca": {"onchange", "onclick"},
        "armazenamento_cliente": {"localstorage", "sessionstorage"},
        "segredos_cliente": {"token", "jwt", "refresh_token", "senha",
                             "password", "secret"},
    }
    for grupo, esperado in piso.items():
        presentes = {t.lower() for t in fe[grupo]}
        faltando = esperado - presentes
        assert not faltando, (
            f"termo(s) removido(s) de frontend-terms.yaml [{grupo}]: "
            f"{sorted(faltando)} — remover encolhe a cobertura de FE-* em "
            f"silêncio; se a remoção é intencional, altere o piso no mesmo PR")


def test_pii_do_frontend_vem_da_regua_geral(regua):
    """P-14 não pode ter lista própria de PII: se tivesse, `cpf` removido de
    pii-patterns.yaml continuaria sendo pego no backend e não no frontend."""
    fonte = Path(__file__).resolve().parent.parent
    codigo = (fonte / "pse" / "checks" / "privacy" /
              "p14_pii_no_cliente.py").read_text(encoding="utf-8")
    assert 'ctx.data["pii-patterns"]' in codigo
    for termo in ("cpf", "titulo_eleitor", "passaporte"):
        assert f'"{termo}"' not in codigo and f"'{termo}'" not in codigo


def test_regua_adversarial_e_vigiada(regua):
    """S-10 e S-11 derivam de `adversarial-patterns`. Esvaziar um grupo aqui
    cega um vetor de injeção inteiro em silêncio — o D-13 no estrato de IA."""
    adv = regua["adversarial-patterns"]
    piso = {
        "fontes_de_entrada_do_usuario": {"request", "body", "params", "argv"},
        "protecoes": None,          # conferido abaixo, por subgrupo
        "chamadas_de_treino": {"fit", "train"},
        "carregadores_de_dataset": {"read_csv", "read_parquet"},
        "finalidades_de_treino": {"treino", "training"},
        "validacoes_de_saida": {"valid", "schema", "escape"},
    }
    for grupo, esperado in piso.items():
        if esperado is None:
            continue
        presentes = {t.lower() for t in adv[grupo]}
        faltando = esperado - presentes
        assert not faltando, (
            f"termo(s) removido(s) de adversarial-patterns.yaml [{grupo}]: "
            f"{sorted(faltando)}")

    for grupo in ("sanitizacao", "normalizacao", "limite", "delimitacao"):
        assert adv["protecoes"].get(grupo), (
            f"grupo de proteção '{grupo}' vazio: S-10 passaria a exigir uma "
            f"proteção que nenhum nome consegue satisfazer, e todo pipeline "
            f"viraria CRÍTICO")

    for grupo in ("execucao", "banco", "rede", "arquivo"):
        assert adv["sinks_perigosos"].get(grupo), (
            f"categoria de sink '{grupo}' vazia: S-11 pararia de ver aquela "
            f"classe de execução")


def test_invisiveis_da_regua_cobrem_zero_width_e_bidi(regua):
    """O vetor que sobrevive à revisão humana. Remover a categoria cega S-10
    sem que nenhum diff mostre a perda."""
    invisiveis = set(regua["adversarial-patterns"]["caracteres_invisiveis"])
    assert invisiveis, "categoria de invisíveis vazia — S-10 fica cego ao vetor 2"
    for c in ("​", "‌", "⁠", "﻿", "‮", "‭", "⁦"):
        assert c in invisiveis, f"faltando U+{ord(c):04X} na régua de invisíveis"
    teto = regua["adversarial-patterns"]["token_flooding"]["caracteres_maximos_aceitos"]
    assert isinstance(teto, int) and 0 < teto <= 200_000, (
        f"teto de token flooding implausível: {teto}")


def _fonte(pack: str, arquivo: str) -> str:
    return (Path(__file__).resolve().parent.parent / "pse" / "checks" /
            pack / arquivo).read_text(encoding="utf-8")


def _literais_de_colecao(pack: str, arquivo: str) -> set:
    """Strings que o check trata como VOCABULÁRIO, não como prosa.

    Procurar o termo no arquivo inteiro reprova a própria explicação de por
    que o check existe — a docstring de P-17 cita `?raca=` e a mensagem de
    S-12 cita a chave `openapi` para o operador entender o motivo do skip.
    A lição aprendida seria "documente menos", que é a errada.

    O que caracteriza lista própria é a string participar de uma COLEÇÃO
    literal ou de uma comparação — `("openapi", "swagger")`, `x in {...}`,
    `nome == "raca"`. É isso que se procura aqui, pela AST.
    """
    import ast
    achados = set()
    for no in ast.walk(ast.parse(_fonte(pack, arquivo))):
        alvos = []
        if isinstance(no, (ast.List, ast.Tuple, ast.Set)):
            alvos = list(no.elts)
        elif isinstance(no, ast.Compare):
            alvos = list(no.comparators)
        elif isinstance(no, ast.Dict):
            alvos = [k for k in no.keys if k is not None]
        for alvo in alvos:
            if isinstance(alvo, ast.Constant) and isinstance(alvo.value, str):
                achados.add(alvo.value.lower())
    return achados


def test_regua_do_contrato_de_api_e_vigiada(regua):
    """S-12, P-17 e S-13 derivam de `api-contract`. Esvaziar um grupo aqui
    apaga um vetor inteiro sem que nenhum teste de caminho feliz perceba —
    o D-13 no estrato de API."""
    api = regua["api-contract"]
    assert api["ontologia"]["extensao"] == "x-ethics", (
        "a extensão que carrega a ontologia mudou de nome: todo contrato já "
        "escrito deixaria de ser reconhecido em silêncio")
    for chave in ("campos_pii", "campos_sensiveis", "escopos"):
        assert api["ontologia"].get(chave), (
            f"grupo '{chave}' vazio: S-12 pararia de ler metade da ontologia")
    piso = {
        "marcas_de_spec": {"openapi", "swagger"},
        "verbos_de_rota": {"get", "post", "route"},
        "extratores_de_query": {"args", "query_params", "params"},
        "guardas_de_filtro": {"allowlist", "validar_filtro"},
        "construtores_de_resposta": {"jsonify", "jsonresponse"},
        "decoradores_de_erro": {"errorhandler", "exception_handler"},
        "ligadores_de_debug": {"run"},
    }
    for grupo, esperado in piso.items():
        presentes = {t.lower() for t in api[grupo]}
        faltando = esperado - presentes
        assert not faltando, (
            f"termo(s) removido(s) de api-contract.yaml [{grupo}]: "
            f"{sorted(faltando)}")
    for grupo in ("traceback", "caminho", "versao"):
        assert api["internals"].get(grupo), (
            f"categoria de internals '{grupo}' vazia: S-13 pararia de ver "
            f"aquela classe de vazamento")
        assert api["atributos_internos"].get(grupo), (
            f"categoria de atributo interno '{grupo}' vazia")
    assert "format_exc" in api["internals"]["traceback"]
    assert "__file__" in api["atributos_internos"]["caminho"]
    assert "sys.version" in api["atributos_internos"]["versao"], (
        "`sys.version` casa pelo nome pontuado inteiro — `version` sozinho "
        "reprovaria qualquer campo de negócio chamado assim")


def test_regua_dos_rastreadores_e_vigiada(regua):
    """P-22, S-17 e P-23 derivam de `rastreadores`. Esvaziar `rastreadores`
    cega o consentimento; esvaziar `cookies_essenciais` faz P-22 acusar o
    cookie de sessão e o time desligar o pack. O piso protege os dois lados."""
    r = regua["rastreadores"]
    piso = {
        "rastreadores": {"google-analytics.com", "googletagmanager.com",
                         "doubleclick.net", "hotjar.com"},
        "cookies_nao_essenciais": {"_ga", "_fbp", "_hj"},
        "cookies_essenciais": {"session", "csrf", "consent"},
        "cookies_de_sessao": {"session", "sessionid", "jwt", "access_token"},
        "engines_validas": {"chromium", "firefox", "webkit"},
    }
    for grupo, esperado in piso.items():
        presentes = {str(t).lower() for t in r[grupo]}
        faltando = esperado - presentes
        assert not faltando, (
            f"termo(s) removido(s) de rastreadores.yaml [{grupo}]: "
            f"{sorted(faltando)}")
    for atributo in ("httpOnly", "secure", "sameSite"):
        assert r["atributos_exigidos_em_sessao"].get(atributo), (
            f"S-17 pararia de cobrar `{atributo}` — e a explicação do porquê "
            f"some do achado junto")
    assert "none" in [str(v).lower() for v in r["samesite_sem_protecao"]], (
        "`SameSite=None` é explicitamente permissivo: sem ele na lista, o "
        "cookie mais exposto passaria como protegido")
    for superficie in ("query", "formulario_get", "referer"):
        assert r["superficies_de_transito"].get(superficie)


def test_cookie_essencial_e_de_sessao_nao_se_contradizem(regua):
    """`session` está nas duas listas de propósito, e isso NÃO é conflito:
    P-22 não o acusa (o produto precisa dele) e S-17 exige que ele venha
    protegido. Se algum dia as listas divergissem — um cookie essencial que
    S-17 ignorasse — a sessão ficaria sem dono. O teste fixa a interseção."""
    r = regua["rastreadores"]
    essenciais = {str(t).lower() for t in r["cookies_essenciais"]}
    de_sessao = {str(t).lower() for t in r["cookies_de_sessao"]}
    assert "session" in essenciais and "session" in de_sessao
    nao_essenciais = {str(t).lower() for t in r["cookies_nao_essenciais"]}
    conflito = essenciais & nao_essenciais
    assert not conflito, (
        f"cookie ao mesmo tempo essencial e não essencial: {sorted(conflito)} "
        f"— P-22 daria respostas diferentes conforme a ordem da lista")


def test_dinamicos_nao_tem_lista_propria():
    for pack, nome in (("privacy", "p22_consentimento_observavel.py"),
                       ("security", "s17_cookie_de_sessao.py"),
                       ("privacy", "p23_pii_em_transito.py")):
        fonte = _fonte(pack, nome)
        assert "rastreadores" in fonte
        intruso = _literais_de_colecao(pack, nome) & {
            "google-analytics.com", "_ga", "sessionid", "httponly", "cpf"}
        assert not intruso, f"vocabulário próprio em {nome}: {sorted(intruso)}"


def test_regua_da_anonimizacao_e_vigiada(regua):
    """P-20 deriva de `anonimizacao`. Remover um termo de
    `construcoes_com_chave` ou de `fontes_de_sal` faz o check passar a punir
    HMAC e sal aleatório — ou seja, a acusar exatamente quem acertou. É o
    D-13 com a consequência invertida, e por isso o piso é aqui."""
    anon = regua["anonimizacao"]
    piso = {
        "hashes_sem_chave": {"md5", "sha1", "sha256", "sha512"},
        "construcoes_com_chave": {"hmac", "pbkdf2_hmac", "scrypt", "bcrypt"},
        "fontes_de_sal": {"urandom", "token_bytes", "uuid4"},
        "argumentos_com_chave": {"key", "salt"},
        "verbos_de_persistencia": {"insert", "save", "write"},
        "verbos_de_exportacao": {"export", "publish"},
        "classes_de_anonimato": {"anonymized"},
    }
    for grupo, esperado in piso.items():
        presentes = {str(t).lower() for t in anon[grupo]}
        faltando = esperado - presentes
        assert not faltando, (
            f"termo(s) removido(s) de anonimizacao.yaml [{grupo}]: "
            f"{sorted(faltando)} — remover daqui faz P-20 punir o caso correto")


def test_regua_da_base_legal_e_vigiada(regua):
    """S-22 deriva de `legal-basis`. Remover uma base do Art. 7o faz o check
    parar de reconhecer o mapa de quem acertou, e o alvo correto passa a
    receber achado — o D-13 com a consequência invertida."""
    lb = regua["legal-basis"]
    bases = {str(b).lower() for b in lb["bases"]}
    piso = {"consentimento", "consent", "obrigacao_legal", "legal_obligation",
            "contrato", "contract", "legitimo_interesse", "legitimate_interest",
            "tutela_da_saude", "protecao_da_vida", "exercicio_de_direitos",
            "protecao_do_credito", "politica_publica", "pesquisa"}
    faltando = piso - bases
    assert not faltando, (
        f"base(s) removida(s) de legal-basis.yaml: {sorted(faltando)} — sem "
        f"elas S-22 deixa de reconhecer o mapa correto e passa a acusar quem "
        f"amarrou a finalidade direito")
    for grupo in ("cabecalhos", "chaves", "extratores_de_cabecalho"):
        assert lb["superficie"][grupo], f"superficie[{grupo}] vazia"
    for grupo in ("chamadas", "excecoes", "status"):
        assert lb["rejeicao"][grupo], f"rejeicao[{grupo}] vazia"
    assert {"purposes", "finalidades"} <= {c.lower() for c in
                                           lb["declaracao"]["containers"]}


def test_finalidade_disfarcada_nunca_entra_como_base_legal(regua):
    """O piso invertido, e o mais importante desta régua. `analytics` e
    `melhoria_do_produto` são FINALIDADES; tratá-las como base legal é o
    defeito que S-22 existe para achar. Se alguém as acrescentasse à lista, o
    check passaria a abençoar exatamente o que deveria reprovar — e o teste
    ficaria verde, porque o achado sumiria."""
    bases = {str(b).lower() for b in regua["legal-basis"]["bases"]}
    proibidas = {"analytics", "melhoria_do_produto", "interesse_do_negocio",
                 "business_interest", "product_improvement", "marketing",
                 "personalizacao", "experiencia_do_usuario"}
    intrusas = proibidas & bases
    assert not intrusas, (
        f"finalidade(s) tratada(s) como base legal em legal-basis.yaml: "
        f"{sorted(intrusas)}. Nenhuma delas está no Art. 7o nem no Art. 11 — "
        f"acrescentá-las inverte o sentido de S-22.")


def test_p20_nao_reimplementa_a_regua_de_pii(regua):
    """O identificador de P-20 vem de `pii-patterns`, sem o grupo
    `credenciais` — hashear senha é o que se deve fazer, e incluí-la faria o
    check acusar a prática certa."""
    fonte = _fonte("privacy", "p20_hash_como_anonimizacao.py")
    assert 'ctx.data["pii-patterns"]' in fonte
    assert 'ctx.data["sensitive-fields"]' in fonte
    intruso = _literais_de_colecao("privacy", "p20_hash_como_anonimizacao.py") & {
        "sha256", "md5", "hmac", "cpf", "urandom", "insert"}
    assert not intruso, f"vocabulário próprio em P-20: {sorted(intruso)}"
    assert '"credenciais"' in fonte, (
        "a exclusão do grupo de credenciais é deliberada e tem de estar "
        "explícita no check")


def test_regua_da_infra_de_backend_e_vigiada(regua):
    """S-14, S-15, P-18, P-19 e S-16 derivam de `backend-infra`. Esvaziar um
    grupo aqui apaga um vetor de infra inteiro — e infra é justamente onde
    ninguém revisita a decisão depois de tomada."""
    infra = regua["backend-infra"]
    piso = {
        "restauradores_de_dump": {"psql", "pg_restore", "mysql", "mongorestore"},
        "marcas_de_producao": {"prod", "producao", "production"},
        "marcas_de_nao_producao": {"staging", "homolog", "dev", "qa"},
        "pseudonimizacao": {"anonymize", "anonimiz", "mask", "scrub", "faker"},
        "privilegios_amplos": {"all privileges", "all"},
        "alvos_amplos": {"all tables"},
        "cifra_de_aplicacao": {"encrypt", "fernet"},
        "gerenciadores_de_chave": {"kms", "vault", "hsm"},
        "barramentos_de_evento": {"kafka", "event_store", "outbox"},
        "produtores_de_evento": {"send", "produce", "publish", "append"},
        "crypto_shredding": {"crypto_shred", "destroy_key", "revoke_key"},
        "chamadas_de_persistencia": {"create_engine", "client", "bucket"},
        "chaves_de_residencia": {"data_residency"},
    }
    for grupo, esperado in piso.items():
        presentes = {str(t).lower() for t in infra[grupo]}
        faltando = esperado - presentes
        assert not faltando, (
            f"termo(s) removido(s) de backend-infra.yaml [{grupo}]: "
            f"{sorted(faltando)}")
    for juris in ("BR", "US", "EU"):
        assert infra["regioes"].get(juris), (
            f"jurisdição '{juris}' sem região mapeada: S-16 pararia de "
            f"reconhecer aquele destino")
    assert "sa-east-1" in infra["regioes"]["BR"], (
        "sem a região nacional, S-16 acusaria toda escrita brasileira")
    assert "us-east-1" in infra["regioes"]["US"]


def test_regiao_nao_pertence_a_duas_jurisdicoes(regua):
    """Uma região em duas jurisdições faria S-16 aprovar e reprovar a mesma
    escrita conforme a ordem do dicionário — não-determinismo silencioso."""
    vistas = {}
    for juris, regioes in regua["backend-infra"]["regioes"].items():
        for r in regioes:
            anterior = vistas.get(str(r).lower())
            assert anterior is None, (
                f"região {r!r} mapeada para {anterior} e {juris}")
            vistas[str(r).lower()] = juris


def test_fundadores_de_backend_nao_tem_lista_propria():
    esperado = {
        ("security", "s14_dump_de_producao.py"): {"psql", "prod", "staging",
                                                  "anonymize"},
        ("security", "s16_residencia_na_escrita.py"): {"us-east-1", "sa-east-1",
                                                       "create_engine", "br"},
        ("privacy", "p18_sensivel_sem_cifra.py"): {"kms", "vault", "encrypt"},
        ("privacy", "p19_evento_sem_crypto_shredding.py"): {"kafka", "send",
                                                            "crypto_shred"},
    }
    for (pack, nome), proibidos in esperado.items():
        assert "backend-infra" in _fonte(pack, nome)
        intruso = _literais_de_colecao(pack, nome) & proibidos
        assert not intruso, f"vocabulário próprio em {nome}: {sorted(intruso)}"


def test_p17_nao_tem_lista_propria_de_campo_proibido():
    """O filtro proibido de P-17 vem de `prohibited-filters` e
    `sensitive-fields`, as mesmas réguas de E-05 e P-08. Se tivesse lista
    própria, remover `raca` de prohibited-filters deixaria E-05 cego e P-17
    enxergando — e ninguém saberia qual dos dois está certo."""
    fonte = _fonte("privacy", "p17_filtro_sensivel_na_busca.py")
    assert 'ctx.data["prohibited-filters"]' in fonte
    assert 'ctx.data["sensitive-fields"]' in fonte
    vocabulario = _literais_de_colecao("privacy", "p17_filtro_sensivel_na_busca.py")
    intruso = vocabulario & {"raca", "etnia", "nome_mae", "cep", "genero"}
    assert not intruso, f"vocabulário próprio em P-17: {sorted(intruso)}"


def test_s12_e_s13_nao_tem_lista_propria():
    for nome in ("s12_ontologia_no_contrato.py", "s13_erro_expoe_internals.py"):
        assert "api-contract" in _fonte("security", nome)
        vocabulario = _literais_de_colecao("security", nome)
        intruso = vocabulario & {"format_exc", "openapi", "swagger",
                                 "errorhandler", "x-ethics", "print_exc",
                                 "__file__", "sys.version", "jsonify"}
        assert not intruso, f"vocabulário próprio em {nome}: {sorted(intruso)}"


def test_s10_e_s11_nao_tem_lista_propria():
    raiz = Path(__file__).resolve().parent.parent / "pse" / "checks" / "security"
    for nome in ("s10_injecao_de_prompt.py", "s11_saida_do_modelo_em_sink.py"):
        codigo = (raiz / nome).read_text(encoding="utf-8")
        assert "adversarial-patterns" in codigo
        for proibido in ("\\u200b", "\\u202e", '"exec"', "'exec'", '"request"'):
            assert proibido not in codigo, f"{proibido!r} hardcoded em {nome}"


def test_regua_do_servido_ao_cliente_e_vigiada(regua):
    """S-18…S-21 derivam de `servido-ao-cliente`. Esvaziar
    `padroes_de_segredo` faz S-20 parar de ver credencial e passar a
    devolver verde — o D-13 com a consequência mais cara desta camada."""
    r = regua["servido-ao-cliente"]
    for cabecalho in ("content-security-policy", "x-content-type-options",
                      "referrer-policy"):
        assert r["cabecalhos_exigidos"].get(cabecalho), (
            f"S-19 pararia de cobrar `{cabecalho}` — e a explicação do porquê "
            f"some do achado junto")
    nomes = {p["nome"] for p in r["padroes_de_segredo"]}
    piso = {"CHAVE_PRIVADA_PEM", "AWS_ACCESS_KEY_ID", "GITHUB_TOKEN",
            "STRIPE_SECRET_KEY", "GOOGLE_API_KEY", "JWT", "CREDENCIAL_NOMEADA"}
    faltando = piso - nomes
    assert not faltando, f"formato(s) removido(s) de padroes_de_segredo: {faltando}"
    for grupo in ("tipos_varridos_por_segredo", "sufixos_varridos_por_segredo",
                  "sufixos_com_metadado", "sufixos_de_bundle"):
        assert r[grupo], f"grupo `{grupo}` vazio: o check fica cego em silêncio"
    assert r["metadados_publicados"].get("gps")


def test_todo_padrao_de_segredo_compila_e_casa_o_proprio_exemplo(regua):
    """Regex quebrado é ignorado por `_compilar` para não derrubar a
    varredura inteira — o que significa que um erro de digitação cegaria o
    formato em SILÊNCIO. Este teste é o que impede isso."""
    import re
    exemplos = {
        "CHAVE_PRIVADA_PEM": "-----BEGIN RSA PRIVATE KEY-----",
        "AWS_ACCESS_KEY_ID": "AKIAIOSFODNN7EXAMPLE",
        "GITHUB_TOKEN": "ghp_" + "a" * 36,
        "STRIPE_SECRET_KEY": "sk_live_" + "a" * 20,
        "GOOGLE_API_KEY": "AIza" + "a" * 35,
        "JWT": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NSJ9.SflKxwRJSMeKKF2QT4",
        "CREDENCIAL_NOMEADA": 'api_key: "valor-secreto-longo"',
    }
    for padrao in regua["servido-ao-cliente"]["padroes_de_segredo"]:
        nome = padrao["nome"]
        rx = re.compile(padrao["padrao"])          # levanta se estiver quebrado
        exemplo = exemplos.get(nome)
        assert exemplo, f"formato `{nome}` sem exemplo no teste — acrescente"
        assert rx.search(exemplo), (
            f"o padrão de `{nome}` não casa o próprio exemplo: ele está cego")


def test_padroes_de_segredo_nao_casam_prosa_inocente(regua):
    """Falso positivo em bateria regulatória custa a credibilidade da
    bateria inteira. Um `token` de CSRF público não pode virar CRÍTICO."""
    from pse.navegador.analise import segredos_em
    padroes = regua["servido-ao-cliente"]["padroes_de_segredo"]
    for inocente in ("Authorization: required",
                     "var token = getCsrfToken();",
                     "// a chave fica no servidor",
                     "eyJquealgoassim",
                     "const apiKey = process.env.API_KEY;"):
        achados = [n for n, sev in segredos_em(inocente, padroes)
                   if sev == "CRITICO"]
        assert not achados, f"{inocente!r} virou CRÍTICO: {achados}"


def test_fase2_nao_tem_lista_propria():
    for pack, nome in (("security", "s18_terceiro_observado.py"),
                       ("security", "s19_cabecalhos_e_conteudo.py"),
                       ("security", "s20_segredo_servido.py"),
                       ("privacy", "p24_metadado_publicado.py"),
                       ("security", "s21_sourcemap_em_producao.py")):
        vocabulario = _literais_de_colecao(pack, nome)
        # `gps` fica DE FORA da lista proibida de propósito: é o rótulo que
        # `analise.metadados_exif` devolve — protocolo interno entre o parser
        # e o check, como `ast.Call` é protocolo com a stdlib. Removê-lo da
        # régua não encolhe cobertura nenhuma (P-24 continua detectando, só
        # perde o texto da explicação), e é isso que o D-13 protege. O
        # vocabulário que ENCOLHE cobertura — tipos, sufixos, cabeçalhos e
        # formatos de segredo — está na lista.
        intruso = vocabulario & {"content-security-policy", "akia", ".js",
                                 ".jpg", "image/jpeg",
                                 "application/javascript"}
        assert not intruso, f"vocabulário próprio em {nome}: {sorted(intruso)}"


def test_regua_de_rust_e_vigiada(regua):
    """D-13 no alcance mais frágil da suite.

    O alcance a Rust é textual, sem árvore: a régua É o check. Esvaziar
    `formatos_de_credencial` faria S-06 parar de emitir CRÍTICO em Rust;
    esvaziar `macros_nao_resolviveis` faria `env!` virar verde silencioso em
    vez de indeterminado. Nenhuma das duas perdas apareceria num diff de
    código.
    """
    rust = regua["rust"]
    piso = {
        "nomes_de_credencial": {"api_key", "access_token", "client_secret",
                                "private_key", "password"},
        "macros_nao_resolviveis": {"env", "option_env", "include_str",
                                   "concat"},
        "cifra_de_aplicacao": {"aes_gcm", "chacha20poly1305", "encrypt"},
        "barramentos": {"rdkafka", "async_nats", "outbox"},
        "produtores": {"send", "publish", "produce"},
        "persistencia": {"PgPool", "connect", "Region"},
        "placeholders": {"changeme", "example", "placeholder"},
        # Aprendidos na triagem contra o btv real. Cada um destes grupos
        # existe porque um caso CORRETO estava sendo acusado — remover um
        # termo daqui traz o falso-positivo de volta, e falso-positivo num
        # alvo real ensina o time a ignorar o pack inteiro.
        "receptores_que_nao_sao_barramento": {"tx", "sender", "builder",
                                              "responder", "stream"},
        "leituras_de_persistencia": {"query_row", "query_map", "query_as",
                                     "fetch_one", "select"},
        "verbos_sql_de_escrita": {"insert", "update"},
        "verbos_sql_de_leitura": {"select"},
        "ddl_de_credencial_de_banco": {"create role", "create user"},
    }
    for grupo, esperado in piso.items():
        presentes = {str(t).lower() for t in rust[grupo]}
        faltando = {t.lower() for t in esperado} - presentes
        assert not faltando, (
            f"termo(s) removido(s) de rust.yaml [{grupo}]: {sorted(faltando)} — "
            f"o alcance a Rust é textual, então a régua É o check; remover "
            f"encolhe a cobertura em silêncio")

    assert rust["formatos_de_credencial"], (
        "sem formato conhecido, nenhum achado em Rust chega a CRÍTICO e o "
        "vetor mais universal da suite vira sempre ALTO")
    # A ORDEM entre escrita e leitura e o que impede o refino de virar
    # falso-negativo: `query_scalar("INSERT ...")` tem nome de leitura e faz
    # escrita, e o btv tem exatamente esse site. Se `verbos_sql_de_escrita`
    # esvaziar, o nome passa a decidir sozinho e aquele INSERT some do laudo.
    assert rust["verbos_sql_de_escrita"], (
        "sem verbo de escrita a régua decide por NOME de chamada, e "
        "`query_scalar(\"INSERT ...\")` — que existe no btv — vira "
        "falso-negativo silencioso")
    assert not (set(map(str.lower, rust["verbos_sql_de_escrita"]))
                & set(map(str.lower, rust["verbos_sql_de_leitura"]))), (
        "verbo em escrita E leitura ao mesmo tempo: a decisão fica dependendo "
        "da ordem do código, não da régua")

    teto = rust["tamanho_minimo_de_credencial"]
    assert isinstance(teto, int) and 12 <= teto <= 64, (
        f"mínimo de credencial implausível: {teto}. Abaixo de 12 o alcance "
        f"textual vira gerador de falso-positivo; acima de 64 ele não acha "
        f"chave nenhuma")


def test_sondas_cobrem_todo_check_com_vetor_em_backend(regua):
    """A sonda é o que faz `nao_aplicavel` ser MEDIDO. Check com vetor em
    backend e sem sonda nunca consegue ser declarado não-aplicável — fica
    eternamente meio-cego, mesmo num alvo onde o vetor não existe."""
    from pse import cobertura
    com_vetor = {c for c in cobertura.SUBSTRATO
                 if cobertura.teria_vetor_em_linguagem_de_servidor(c)}
    sondas = set(regua["rust"]["sondas"])
    # Os quatro com alcance textual não precisam de sonda: eles OLHAM.
    faltando = com_vetor - sondas - {"S-06", "P-18", "P-19", "S-16"}
    assert not faltando, (
        f"check com vetor em backend e sem sonda de substrato: "
        f"{sorted(faltando)}. Sem sonda ele não consegue ser declarado "
        f"não-aplicável nem num alvo onde o vetor comprovadamente não existe.")
    assert not (sondas & {"S-06", "P-18", "P-19", "S-16"}), (
        "check com alcance textual não pode ter sonda: a sonda empurra para "
        "não-aplicável, e ele OLHA — seria apagar o alcance que existe")


# ============================================ a regua do conserto de severidade
def test_piso_dos_caminhos_de_teste(regua):
    """Remover uma marca daqui faz P-06/S-06 voltarem a reprovar o CI por
    causa de fixture — o defeito que a rodada de reconhecimento mediu."""
    marcas = {str(m).lower() for m in regua["credenciais"]["caminhos_de_teste"]}
    piso = {"/tests/", "/fixtures/", "/__tests__/", "conftest",
            "^test_", "_test$", ".test.", ".spec."}
    faltando = piso - marcas
    assert not faltando, (
        f"marca(s) removida(s) de credenciais.yaml [caminhos_de_teste]: "
        f"{sorted(faltando)} — sem elas o gate volta a ser dirigido por fixture")


def test_a_posicao_da_marca_esta_declarada(regua):
    """`test_` sem ancora casaria `generate_test_password.py`, que e o unico
    caso REAL dos 19 medidos. A ancora nao e estilo: e o que impede o conserto
    de cegar o achado que ele existe para preservar."""
    marcas = {str(m).lower() for m in regua["credenciais"]["caminhos_de_teste"]}
    assert "test_" not in marcas, (
        "`test_` sem `^` casa em qualquer posicao do nome e cega "
        "`generate_test_password.py` — use `^test_`")
    assert "_test" not in marcas, "use `_test$`, nao `_test`"


def test_valor_sintetico_nao_pode_casar_segredo_real(regua):
    """O piso INVERTIDO. Acrescentar termo a esta lista encolhe a cobertura, e
    e o jeito mais silencioso de desligar os dois checks: os achados continuam
    saindo, em MEDIO, e o laudo parece o mesmo de antes."""
    valores = {str(v).lower() for v in regua["credenciais"]["valores_sinteticos"]}
    intrusos = valores & VALORES_QUE_NAO_PODEM_ENTRAR
    assert not intrusos, (
        f"marca(s) que rebaixariam segredo real em credenciais.yaml: "
        f"{sorted(intrusos)}. Marca que rebaixa por acidente e pior que marca "
        f"que falta — a primeira tira do gate um segredo vivo.")
    curtas = {v for v in valores if len(v) < 4}
    assert not curtas, (
        f"marca(s) curta(s) demais: {sorted(curtas)} — casariam por acidente")


def test_a_regua_de_credencial_nao_suprime(regua):
    """A garantia de contrato: nao existe grupo `ignorar` nesta regua. Se um
    dia existir, alguem esta transformando rebaixamento em supressao."""
    assert set(regua["credenciais"]) == {"caminhos_de_teste", "valores_sinteticos"}, (
        "grupo novo em credenciais.yaml — se for lista de supressao, a trava "
        "virou algo que o vigiado desliga movendo o segredo de arquivo")


def test_piso_dos_dominios_reservados(regua):
    """A lista que P-01, S-03 e S-04 leem JUNTOS desde a rodada de conserto.
    Remover `example.com` daqui reabre os tres CRITICOs de seed que a rodada
    de reconhecimento mediu; remover um TLD reabre a mesma classe."""
    tp = regua["third-party-endpoints"]
    ignorar = {str(d).lower() for d in tp["ignorar"]}
    assert {"example.com", "example.org", "localhost"} <= ignorar
    # `example.net` vale para E-MAIL e nao para HOST: como host ele segue
    # sendo egresso visivel, e junta-lo a `ignorar` fez tres mutacoes
    # canonicas pararem de morder. A assimetria esta declarada na regua.
    email = {str(d).lower() for d in tp["reservados_de_email"]}
    assert {"example.com", "example.org", "example.net"} <= email
    tlds = {str(t).lower() for t in tp["tld_reservados"]}
    assert {".test", ".invalid", ".localhost", ".example"} <= tlds


def test_dominio_vivo_nunca_entra_como_reservado(regua):
    """Piso invertido. Acrescentar um dominio real aqui cega P-01, S-03 e S-04
    de uma vez — e o laudo segue com a mesma cara, sem achado nenhum."""
    tp = regua["third-party-endpoints"]
    reservados = ({str(d).lower() for d in tp["ignorar"]}
                  | {str(d).lower() for d in tp["reservados_de_email"]})
    proibidos = {"gmail.com", "outlook.com", "hotmail.com", "com", "com.br",
                 "amazonaws.com", "googleapis.com", "sendgrid.net"}
    intrusos = reservados & proibidos
    assert not intrusos, (
        f"dominio vivo tratado como reservado: {sorted(intrusos)} — isto cega "
        f"P-01, S-03 e S-04 ao mesmo tempo, sem mudar a cara do laudo")
    tlds = {str(t).lower() for t in tp["tld_reservados"]}
    assert not (tlds & {".com", ".br", ".net", ".org", ".io", ".dev"}), (
        "TLD vivo na lista de reservados — casa por sufixo e apaga a internet "
        "inteira do alcance dos tres checks")
