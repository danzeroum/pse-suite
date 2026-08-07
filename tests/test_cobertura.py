"""O mapa de cobertura tem de reprovar exatamente o defeito que ele existe
para expor: cegueira disfarcada de limpeza.

Um mapa de cobertura errado e mais perigoso que mapa nenhum, porque a coisa
que ele produz — a impressao de que o alvo foi auditado — e justamente a que
ninguem vai reconferir. Entao os testes daqui nao verificam "o mapa roda":
verificam que ele MORDE.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from pse import catalogo, cobertura

RAIZ = Path(__file__).resolve().parent.parent
MEDICAO = RAIZ / "aceites" / "btv-medicao.json"
DOC = RAIZ / "docs" / "cobertura-btv.md"


def _dados():
    return json.loads(MEDICAO.read_text(encoding="utf-8"))


def _laudo_sintetico(lidos, fora, executados):
    """Laudo minimo: so o que `mapear` consome."""
    return {
        "alcance": {
            "lidos": [{"linguagem": x, "arquivos": 1} for x in lidos],
            "fora_de_alcance": [{"linguagem": x, "arquivos": 1} for x in fora],
        },
        "checks_executados": list(executados),
        "checks_pulados": [], "checks_indeterminados": [],
        "checks_nao_habilitados": [],
        "findings": [], "veredito": "conforme", "exit_code": 0,
    }


# ------------------------------------------------------- nenhum estado mudo

def test_todo_check_tem_substrato_declarado():
    """Substrato ausente e um buraco no mapa, nao um detalhe.

    Sem ele o check nao consegue nem ser classificado — e um check que o
    mapa nao classifica e exatamente o silencio que este documento combate.
    """
    faltando = sorted(set(catalogo.CATALOGO) - set(cobertura.SUBSTRATO))
    assert not faltando, f"sem substrato declarado: {faltando}"


def test_substrato_nao_declara_check_que_nao_existe():
    fantasma = sorted(set(cobertura.SUBSTRATO) - set(catalogo.CATALOGO))
    assert not fantasma, f"substrato de check inexistente: {fantasma}"


def test_a_soma_dos_estados_fecha_o_catalogo_inteiro():
    """auditado + parcial + fora + n/a + indeterminado + nao habilitado = 100%.

    Se um estado novo aparecer sem entrar na contagem, a soma abre e este
    teste reprova — que e o unico jeito de garantir que ninguem introduza um
    balde silencioso.
    """
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    assert sum(mapa["contagem"].values()) == len(catalogo.CATALOGO)
    assert mapa["total"] == len(catalogo.CATALOGO)
    assert set(mapa["por_check"]) == set(catalogo.CATALOGO)


def test_nenhum_check_cai_em_estado_desconhecido():
    """Estado fora do vocabulario declarado nao renderiza rotulo e some da
    tabela por estado — some do documento sem sumir do problema."""
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    conhecidos = set(cobertura.ORDEM_DOS_ESTADOS)
    desconhecidos = {c: v["estado"] for c, v in mapa["por_check"].items()
                     if v["estado"] not in conhecidos}
    assert not desconhecidos, desconhecidos


# ------------------------------------------- os estados nao podem colapsar

def test_alvo_so_de_rust_poe_os_checks_de_backend_fora_de_alcance():
    """O teste-mordida do documento inteiro.

    Um alvo em que TODO o codigo de servidor e Rust: nenhum check de vetor
    universal pode sair `auditado`. Se sair, "sem achado" naquele check
    estaria dizendo "olhei e esta limpo" sobre 100% de codigo nao lido — a
    cobertura de fachada, na forma exata em que ela aparece.
    """
    laudo = _laudo_sintetico(lidos=["YAML", "JSON"], fora=["Rust"],
                             executados=sorted(catalogo.CATALOGO))
    mapa = cobertura.mapear(laudo)
    universais = [c for c in catalogo.CATALOGO
                  if cobertura.BACKEND in cobertura.SUBSTRATO[c][0]]
    assert universais
    for cid in universais:
        v = mapa["por_check"][cid]
        assert v["estado"] != cobertura.AUDITADO, (
            f"{cid} saiu AUDITADO num alvo cujo servidor e 100% Rust nao lido")
        assert "Rust" in v["linguagens_cegas"]
        assert v["estado"] in (cobertura.FORA_DE_ALCANCE,
                               cobertura.AUDITADO_PARCIAL), (cid, v["estado"])
        # Cego INTEIRO so quem nao tem tambem substrato declarativo: P-18
        # cruza catalogo (YAML, lido) com chamada de cifra (Rust, cego), e
        # por isso e parcial de verdade — nao ha por que rebaixa-lo.
        if set(cobertura.SUBSTRATO[cid][0]) <= {cobertura.PYTHON,
                                                cobertura.BACKEND}:
            assert v["estado"] == cobertura.FORA_DE_ALCANCE, cid
    assert mapa["contagem"].get(cobertura.FORA_DE_ALCANCE), \
        "nenhum check chegou a fora_de_alcance num alvo 100% Rust"


def test_sem_achado_em_arquivo_nao_lido_nunca_vira_auditado():
    """Regra invariante, e nao coincidencia do alvo: `AUDITADO` so existe
    quando NAO ha linguagem cega no substrato. Sem isso, o estado mais forte
    do mapa poderia ser dado a um check que nao leu metade do alvo."""
    for lidos, fora in (
            (["Python"], ["Rust"]),
            (["TypeScript"], ["Go", "Java"]),
            (["YAML", "JSON", "Python", "TypeScript", "SQL", "shell"], []),
            ([], ["Rust"])):
        mapa = cobertura.mapear(_laudo_sintetico(
            lidos, fora, sorted(catalogo.CATALOGO)))
        for cid, v in mapa["por_check"].items():
            if v["estado"] == cobertura.AUDITADO:
                assert not v["linguagens_cegas"], (
                    f"{cid} AUDITADO com {v['linguagens_cegas']} cego "
                    f"(lidos={lidos}, fora={fora})")


def test_parcial_carrega_as_duas_metades():
    """`auditado_parcial` sem dizer o que leu E o que nao leu seria so um
    rotulo mais macio para o mesmo silencio."""
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    parciais = mapa["parcialmente_cegos"]
    assert parciais, "o alvo poliglota tem de produzir parciais"
    for cid in parciais:
        v = mapa["por_check"][cid]
        assert v["linguagens_lidas"], f"{cid} parcial sem metade lida"
        assert v["linguagens_cegas"], f"{cid} parcial sem metade cega"


def test_nao_aplicavel_nao_e_o_mesmo_que_fora_de_alcance():
    """Um alvo sem uma linha de web: os checks de navegador sao NAO
    APLICAVEL (o vetor nao existe), nunca FORA DE ALCANCE (nao ha nada que
    um parser resolveria)."""
    laudo = _laudo_sintetico(lidos=["Python"], fora=["Rust"],
                             executados=sorted(catalogo.CATALOGO))
    mapa = cobertura.mapear(laudo)
    for cid in ("P-13", "P-14", "S-09"):
        assert mapa["por_check"][cid]["estado"] == cobertura.NAO_APLICAVEL
        assert not cobertura.teria_vetor_em_linguagem_de_servidor(cid)


def test_o_laudo_vence_a_inferencia():
    """Indeterminado e nao-habilitado sao verdades mais fortes: um check que
    tentou e nao decidiu nao pode virar `auditado` porque a linguagem dele
    por acaso foi lida."""
    laudo = _laudo_sintetico(lidos=["Python", "YAML", "JSON"], fora=[],
                             executados=[])
    laudo["checks_indeterminados"] = [{"id": "P-04", "motivo": "x"}]
    laudo["checks_nao_habilitados"] = [{"id": "P-05", "motivo": "y"}]
    mapa = cobertura.mapear(laudo)
    assert mapa["por_check"]["P-04"]["estado"] == cobertura.INDETERMINADO
    assert mapa["por_check"]["P-05"]["estado"] == cobertura.NAO_HABILITADO


def test_extensao_nao_reconhecida_reaparece_em_bloco_proprio():
    """O preco da lista positiva de linguagens de servidor: uma extensao
    desconhecida some do mapa por check. Ela nao pode sumir do documento."""
    laudo = _laudo_sintetico(
        lidos=["Python"], fora=[".zig (linguagem nao reconhecida)"],
        executados=sorted(catalogo.CATALOGO))
    mapa = cobertura.mapear(laudo)
    assert mapa["substrato_indeterminado"] == [
        {"linguagem": ".zig (linguagem nao reconhecida)", "arquivos": 1}]


def test_stub_de_tipos_nao_conta_como_backend_cego():
    """`.pyi` e `.jsonl` do btv entravam como 'linguagem de backend nao
    lida' e apareciam como lacuna em 19 checks. Ruido ao lado de Rust, que e
    a lacuna de verdade, dilui a unica informacao que o mapa da."""
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    for cid in mapa["parcialmente_cegos"]:
        assert mapa["por_check"][cid]["linguagens_cegas"] == ["Rust"], cid


# --------------------------------------------------------------- escopo

def test_todo_check_com_vetor_universal_tem_custo_de_parser_estimado():
    """Recomendacao de escopo com check sem custo estimado e recomendacao
    incompleta — e incompleta para menos, que e o lado que engana."""
    com_vetor = {c for c in catalogo.CATALOGO
                 if cobertura.teria_vetor_em_linguagem_de_servidor(c)}
    assert com_vetor - set(cobertura.EXIGENCIA_DE_PARSER) == set()
    assert set(cobertura.EXIGENCIA_DE_PARSER) - com_vetor == set()


def test_o_que_o_parser_nao_compra_e_o_complemento_exato():
    esc = cobertura.escopo(cobertura.mapear(_dados()["medicao"]["laudo"]))
    assert (len(esc["nunca_precisariam"]) + esc["total_com_vetor"]
            == len(catalogo.CATALOGO))
    for cid in esc["nunca_precisariam"]:
        assert not cobertura.teria_vetor_em_linguagem_de_servidor(cid)


def test_o_ganho_do_parser_nao_soma_check_que_nem_rodou():
    """Contar um check indeterminado como 'ganho do parser' inflaria a
    recomendacao — e inflar a favor de gastar um trimestre em parser e
    exatamente o vies que esta rodada foi criada para evitar."""
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    esc = cobertura.escopo(mapa)
    cegos = set(mapa["cegos_com_vetor"]) | set(mapa["parcialmente_cegos"])
    for degrau, d in esc["por_degrau"].items():
        assert set(d["cegos_agora"]) <= cegos, degrau
        assert not set(d["nao_executaram"]) & cegos, degrau
    assert not esc["sem_exigencia_declarada"]


def test_a_prosa_da_recomendacao_nao_contradiz_a_tabela():
    """Numero escrito a mao numa recomendacao envelhece em silencio e passa
    a contradizer a tabela logo abaixo. Aqui ele e interpolado, e este teste
    e o que impede alguem de voltar a escreve-lo."""
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    esc = cobertura.escopo(mapa)
    texto = cobertura.recomendacao(esc)
    for degrau in (cobertura.LITERAL, cobertura.CHAMADA, cobertura.ESTRUTURA):
        n = len(esc["por_degrau"][degrau]["cegos_agora"])
        assert f"`{degrau}` compra {n}" in texto, degrau
    assert f"**{len(esc['nunca_precisariam'])} dos checks" in texto


# ------------------------------------------------------- documento gerado

def test_o_documento_versionado_e_o_gerado():
    """Mesma regra da matriz: documento mantido a mao diverge do territorio
    no primeiro check novo, e um mapa errado parece confiavel."""
    d = _dados()
    esperado = cobertura.gerar(d["medicao"], d["alvo"])
    assert DOC.read_text(encoding="utf-8") == esperado, (
        "docs/cobertura-btv.md desatualizado: rode "
        "`python -m pse.cobertura aceites/btv-medicao.json "
        "> docs/cobertura-btv.md`")


def test_o_documento_e_regeneravel_sem_o_alvo():
    """A medicao exige o clone; o DOCUMENTO nao pode exigir. Um mapa que so
    uma pessoa consegue regenerar nao e verificavel."""
    out = subprocess.run(
        [sys.executable, "-m", "pse.cobertura", str(MEDICAO)],
        capture_output=True, text=True, cwd=RAIZ, check=True)
    assert out.stdout == DOC.read_text(encoding="utf-8")


def test_o_documento_nomeia_a_linguagem_cega_e_o_tamanho_dela():
    texto = DOC.read_text(encoding="utf-8")
    prop = _dados()["medicao"]["proporcao"]
    assert "Rust" in texto
    assert f"{prop['percentual_cego']}% cego" in texto
    assert str(prop["linhas_total"]) in texto


def test_a_medicao_declara_procedencia_datada():
    """Medicao sem data e sem commit do alvo e impressao, nao evidencia."""
    alvo = _dados()["alvo"]
    for campo in ("nome", "commit", "medido_em", "suite", "modo", "dinamico"):
        assert alvo.get(campo), campo
    assert len(alvo["commit"]) == 40


def test_o_mapa_nao_melhora_o_laudo_que_o_originou():
    """Cobertura de fachada comeca quando o mapa suaviza o veredito. O
    documento repete o exit code e os achados como eles sairam."""
    laudo = _dados()["medicao"]["laudo"]
    texto = DOC.read_text(encoding="utf-8")
    assert f"exit `{laudo['exit_code']}`" in texto
    assert laudo["veredito"] in texto
    for f in laudo["findings"]:
        assert f["titulo"] in texto


# --------------------------------------------- a medicao contra o alvo vivo

def _clone_do_btv():
    import yaml
    aceite = yaml.safe_load(
        (RAIZ / "aceites" / "btv-estatico.yaml").read_text(encoding="utf-8"))
    return Path(aceite["alvo"]["caminho"])


@pytest.mark.skipif(not _clone_do_btv().exists(),
                    reason="clone de danzeroum/btv ausente: a medicao fica "
                           "PENDENTE, nunca verde (ver aceites/btv-estatico.yaml)")
def test_o_alcance_registrado_ainda_bate_com_o_alvo():
    """Com o alvo na maquina, o instantaneo tem de continuar verdadeiro.

    Nao compara linha a linha — o btv evolui, e aceite que quebra a cada
    commit do alvo e desligado no primeiro mes. Compara o que nao pode
    mudar em silencio: a linguagem cega dominante continua sendo Rust, e
    continua sendo a maior parte do repositorio.
    """
    from pse import alcance
    medido = alcance.medir(_clone_do_btv())
    fora = {x["linguagem"] for x in medido["fora_de_alcance"]}
    parcial = {x["linguagem"]: x for x in medido["alcance_parcial"]}

    # Este teste ja mordeu uma vez, e foi assim que deve ser: Rust estava em
    # `fora_de_alcance` e a suite ganhou alcance textual a quatro vetores. A
    # trava reprovou, obrigando a atualizar a afirmacao em vez de deixar o
    # documento continuar dizendo o que era. Agora ela vigia o outro lado.
    assert "Rust" not in fora, (
        "Rust voltou para fora-de-alcance total: o alcance textual dos quatro "
        "vetores sumiu. Se foi de proposito, refaca a medicao no mesmo PR.")
    assert "Rust" in parcial, (
        "Rust saiu do alcance parcial. Se a suite ganhou um parser de verdade, "
        "mova para COM_PARSER e refaca a medicao — o documento nao pode "
        "continuar afirmando o que era.")
    assert set(parcial["Rust"]["checks"]) == {"S-06", "P-18", "P-19", "S-16"}, (
        "a lista de checks com alcance a Rust mudou sem a medicao ser refeita. "
        "Check que entra ou sai muda o mapa de cobertura inteiro.")


# --------------------------------- alcance e execucao sao eixos diferentes

def test_check_pulado_nao_desaparece_dentro_de_auditado():
    """O defeito que a primeira versao deste mapa tinha.

    S-18 foi PULADO no btv (nao ha manifesto de terceiros para comparar) e
    aparecia so como `AUDITADO`, porque o substrato dele — a aplicacao no ar
    — de fato foi alcancado. Um leitor concluiria "olhei e esta limpo" sobre
    um check que nao olhou coisa alguma. Alcance de substrato e execucao sao
    eixos independentes, e o mapa mostra os dois.
    """
    laudo = _dados()["medicao"]["laudo"]
    mapa = cobertura.mapear(laudo)
    pulados = {c["id"] for c in laudo["checks_pulados"]}
    assert pulados, "o alvo tem de ter pulados para este teste valer"
    assert set(mapa["pulados"]) == pulados
    for cid in pulados:
        v = mapa["por_check"][cid]
        assert v["no_laudo"] == cobertura.PULADO
        assert v["motivo_no_laudo"], f"{cid} pulado sem motivo — proibido"


def _linha_do_mapa(texto, cid):
    """A tabela de achados tambem comeca com ``| `P-07` |``. A linha do mapa
    e a unica com sete colunas."""
    linhas = [x for x in texto.splitlines()
              if x.startswith(f"| `{cid}` |") and x.count("|") == 8]
    assert len(linhas) == 1, (cid, linhas)
    return linhas[0]


def test_o_documento_mostra_o_pulo_de_cada_check_pulado():
    texto = DOC.read_text(encoding="utf-8")
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    for cid in mapa["pulados"]:
        linha = _linha_do_mapa(texto, cid)
        assert "**pulado**" in linha, (
            f"{cid} foi pulado e a linha dele nao diz isso: {linha}")


def test_check_que_executou_nao_e_marcado_como_pulado():
    laudo = _dados()["medicao"]["laudo"]
    mapa = cobertura.mapear(laudo)
    parciais = set(laudo["relatorios"].get("cobertura_parcial") or {})
    for cid in {c["id"] for c in laudo["checks_executados"]}:
        esperado = cobertura.PARCIAL if cid in parciais else "executou"
        assert mapa["por_check"][cid]["no_laudo"] == esperado, cid


def test_todo_check_carrega_os_dois_eixos():
    """Nenhum check pode sair do mapa sem dizer AS DUAS coisas."""
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    for cid, v in mapa["por_check"].items():
        assert v["estado"] in cobertura.ORDEM_DOS_ESTADOS, cid
        assert v["no_laudo"] in (
            "executou", cobertura.PULADO, cobertura.PARCIAL,
            cobertura.INDETERMINADO,
            cobertura.NAO_HABILITADO), (cid, v["no_laudo"])


def test_o_numero_de_auditados_de_verdade_exige_as_duas_coisas():
    """`AUDITADO` e `executou` juntos, e nada menos. Um check pulado com
    substrato integro nao conta, e um que rodou cego pela metade tambem
    nao — os dois produziriam o mesmo *sem achado* que nao significa nada.
    """
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    plenos = [c for c, v in mapa["por_check"].items()
              if v["estado"] == cobertura.AUDITADO and v["no_laudo"] == "executou"]
    texto = DOC.read_text(encoding="utf-8")
    assert f"**{len(plenos)} dos {len(catalogo.CATALOGO)} checks foram " \
           f"auditados DE VERDADE**" in texto
    assert len(plenos) < mapa["contagem"][cobertura.AUDITADO], (
        "se os dois numeros coincidirem, a distincao nao esta sendo feita")
    for cid in plenos:
        assert not mapa["por_check"][cid]["linguagens_cegas"], cid
        assert cid not in mapa["pulados"], cid


def test_check_que_rodou_so_metade_nao_conta_como_auditado_de_verdade():
    """O laudo ja declarava isto em `relatorios.cobertura_parcial` e o mapa
    ignorava. P-09 mede k-anonimato na resposta da agregacao; em
    `pse_passive` a metade runtime nem dispara. Marcado como auditado
    integral, ele seria o falso verde deste documento acontecendo DENTRO do
    documento."""
    laudo = _dados()["medicao"]["laudo"]
    declarados = set(laudo["relatorios"]["cobertura_parcial"])
    assert declarados, "a medicao tem de carregar o relatorio para valer"
    mapa = cobertura.mapear(laudo)
    assert set(mapa["meia_execucao"]) == declarados
    plenos = {c for c, v in mapa["por_check"].items()
              if v["estado"] == cobertura.AUDITADO and v["no_laudo"] == "executou"}
    assert not (plenos & declarados), plenos & declarados
    for cid in declarados:
        assert mapa["por_check"][cid]["motivo_no_laudo"]


def test_o_documento_marca_a_meia_execucao_na_linha_do_check():
    texto = DOC.read_text(encoding="utf-8")
    mapa = cobertura.mapear(_dados()["medicao"]["laudo"])
    assert mapa["meia_execucao"]
    for cid in mapa["meia_execucao"]:
        assert "**so metade**" in _linha_do_mapa(texto, cid), cid


def test_a_camada_dinamica_declara_o_que_nao_conseguiu_ler():
    """O recurso acima do teto de corpo nao foi varrido por S-20. Ausencia
    de achado nele nao e ausencia de segredo — a mesma regra do bloco
    `alcance`, um nivel abaixo.

    O bloco e CONDICIONAL, e a medicao de producao mostrou por que: contra o
    bundle real nao ha recurso acima do teto (o `react-dom_client.js` de
    2,8 MB era do dev server, servido sem minificar). Exigir o relatorio
    sempre transformaria um bom resultado em falha de teste — mas quando ele
    existe, cada recurso PRECISA aparecer no documento.
    """
    rel = _dados()["medicao"]["laudo"]["relatorios"]
    texto = DOC.read_text(encoding="utf-8")
    for r in (rel.get("recursos_nao_varridos") or {}).get("recursos") or []:
        assert r in texto
    obs = rel["observacao_de_rede"]
    assert str(obs["total_requisicoes"]) in texto
    for host in obs["hosts_contactados"]:
        assert f"`{host}`" in texto
