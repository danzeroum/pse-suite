"""Cobertura REAL contra um alvo: o que foi auditado, o que ficou cego, o que
nao se aplica.

    python -m pse.cobertura aceites/btv-medicao.json > docs/cobertura-btv.md

O bloco `alcance` do laudo responde "que linguagens a suite nao le". Esta e a
pergunta seguinte, e a que decide escopo: **quais CHECKS ficaram cegos, e
quais deles teriam vetor de verdade na linguagem que faltou?**

Sao perguntas diferentes. Saber que a PSE nao le Rust nao diz se isso importa:
importa muito para S-06 (chave hardcoded existe em qualquer linguagem) e nao
importa nada para P-13 (checkbox pre-marcado nao existe em Rust). Sem separar
os dois casos, a decisao "a PSE deveria falar Rust?" vira intuicao — e
intuicao aqui custa um parser inteiro a toa.

TRES ESTADOS, E COLAPSA-LOS E O VERDE FALSO QUE O btv QUASE PRODUZIU:

  AUDITADO         a suite leu o substrato onde o vetor deste check vive.
                   "Sem achado" aqui significa mesmo "olhei e esta limpo".
  FORA_DE_ALCANCE  o vetor deste check EXISTE no alvo, numa linguagem que a
                   suite nao le. "Sem achado" aqui significa "nao olhei" — e
                   e exatamente o que nao pode ser confundido com limpeza.
  NAO_APLICAVEL    o vetor deste check nao existe neste alvo. Nao ha o que
                   ler nem o que perder: um check de checkbox de consentimento
                   nao tem sentido num motor de execucao em Rust.

E um QUARTO que os dados exigiram, e que e o mais importante deles no btv:

  AUDITADO_PARCIAL o substrato do check existe em DUAS linguagens do alvo, e
                   a suite leu uma. E o caso de P-01 no btv: a orquestracao
                   Python foi lida, o motor Rust nao. Chamar isso de
                   "auditado" seria o verde falso pelo qual esta rodada
                   inteira existe — o check olhou 8 mil linhas e ficou cego
                   para 38 mil. Chamar de "fora de alcance" seria mentir para
                   o outro lado: ele olhou de verdade, e o que achou vale.
                   Sao 3 estados na pergunta e 4 na resposta porque o alvo
                   real e poliglota, e fingir que nao e seria inventar
                   simplicidade que os dados nao tem.

Mais os dois estados que o proprio laudo ja produz — INDETERMINADO (tentou e
nao decidiu) e NAO_HABILITADO (Trabalho A sem alvo declarado) — porque um
mapa que os escondesse mentiria por omissao no lugar mais visivel.

E UM SEGUNDO EIXO, porque junta-lo ao primeiro seria refazer o mesmo erro
numa escala menor. O estado acima responde "a suite leu o codigo onde o vetor
vive"; `no_laudo` responde "o check chegou a decidir alguma coisa". Sao
independentes: S-18 tem o substrato inteiro alcancado (a aplicacao estava no
ar) e mesmo assim foi PULADO, por nao haver manifesto de terceiros para
comparar. P-09 executou e rodou so metade — o laudo ja dizia isso em
`relatorios.cobertura_parcial`, e a primeira versao deste mapa ignorava.
Cruzando os dois eixos, dos 57 checks apenas 13 foram auditados de verdade
contra o btv. Esse e o numero que a rodada foi buscar.

O SUBSTRATO DE CADA CHECK E JULGAMENTO, e por isso fica DECLARADO aqui, com
justificativa, do mesmo jeito que as leituras da matriz. Inferir substrato a
partir do `domain` do catalogo nao serve: `domain` diz ONDE o valor se
manifesta (backend), nao EM QUE LINGUAGEM o vetor e escrito — e e a segunda
que decide se um parser novo compra alguma coisa.
"""
from collections import Counter

from pse import catalogo
from pse.alcance import ALCANCE_PARCIAL, COM_PARSER, IRRELEVANTES, SEM_PARSER

AUDITADO = "auditado"
AUDITADO_PARCIAL = "auditado_parcial"
FORA_DE_ALCANCE = "fora_de_alcance"
NAO_APLICAVEL = "nao_aplicavel"
INDETERMINADO = "indeterminado"
NAO_HABILITADO = "nao_habilitado"
PULADO = "pulado"
# O check rodou, mas so uma das metades dele. O laudo ja declara isso em
# `relatorios.cobertura_parcial`; aqui ele vira eixo, para nao virar verde.
PARCIAL = "executou_parcialmente"

# Familias de substrato. Nao sao linguagens: sao ONDE o vetor de um check
# pode existir. `qualquer_backend` e a familia que decide a pergunta do
# parser — sao os checks cujo vetor nao tem nada de especifico de Python ou
# de JS, e que portanto existem tambem em Rust, Go ou Java.
WEB = "web"                       # JS/TS/JSX/TSX rodando no navegador
PYTHON = "python"                 # o vetor e idiomatico de Python
BACKEND = "qualquer_backend"      # existe em QUALQUER linguagem de servidor
DECLARACAO = "declaracao"         # YAML/JSON: catalogo, manifesto, contrato
SQL = "sql"
INFRA = "infra"                   # shell, CI, migracao
RUNTIME = "runtime"               # observa a aplicacao NO AR; nao le fonte

# Que linguagens do alvo cada familia ocupa. `runtime` e `declaracao` nao
# dependem de parser de linguagem de programacao nenhuma — e por isso sao a
# parte da suite que um alvo poliglota nunca perde.
LINGUAGENS_DA_FAMILIA = {
    WEB: {"JavaScript", "JavaScript/JSX", "TypeScript", "TypeScript/TSX"},
    PYTHON: {"Python"},
    DECLARACAO: {"YAML", "JSON"},
    SQL: {"SQL"},
    INFRA: {"shell", "YAML"},
    # BACKEND e especial: ocupa a linguagem de servidor QUE O ALVO USAR, seja
    # ela qual for. E resolvido contra o alvo, nao fixado aqui.
}

# ----------------------------------------------------------------------------
# O SUBSTRATO DE CADA CHECK — julgamento declarado, com o porque.
#
# `familias`: onde o vetor pode existir.
# `nota`: por que. Entra no mapa; substrato sem justificativa e opiniao.
# ----------------------------------------------------------------------------
SUBSTRATO = {
    # --------------------------------------------------------------- etica
    "E-00": ([PYTHON, BACKEND], "guarda de escopo: procura sinal de decisao "
             "automatizada no codigo, e modelo se chama de qualquer linguagem"),
    "E-01": ([PYTHON, BACKEND], "explicacao anexada a decisao — a decisao pode "
             "ser tomada em qualquer linguagem"),
    "E-02": ([PYTHON, BACKEND], "decision log estruturado; o log e escrito por "
             "quem decide, seja em que linguagem for"),
    "E-03": ([RUNTIME], "endpoint de contestacao: so a aplicacao no ar responde"),
    "E-04": ([PYTHON, BACKEND], "rota de revisao humana no codigo de decisao"),
    "E-05": ([PYTHON], "feature proibida entrando em pipeline de ML — o "
             "pipeline e Python na pratica universal do setor"),
    "E-06": ([DECLARACAO], "cruza relatorio de fairness com dataset declarado; "
             "nao le codigo"),
    "E-07": ([DECLARACAO], "Model Card e Datasheet sao artefatos declarativos"),
    "E-08": ([DECLARACAO], "trilha de linhagem e artefato declarativo"),
    "E-09": ([RUNTIME], "kill switch: so se prova acionando o dry-run"),
    "E-10": ([PYTHON], "incerteza quantificada na saida do modelo"),
    "E-11": ([PYTHON, BACKEND], "PII indo para prompt de LLM. Hoje o SDK e "
             "Python na maioria esmagadora, mas a chamada existe em qualquer "
             "linguagem — e um cliente HTTP"),
    "E-12": ([PYTHON, BACKEND], "derivado exportado como anonimo"),
    "E-13": ([DECLARACAO], "host dentro de dependencia: le o manifesto de "
             "pacotes, nao o codigo da dependencia"),

    # ----------------------------------------------------------- privacidade
    "P-01": ([PYTHON, BACKEND], "PII em log. TODA linguagem tem logger, e a "
             "chamada crua e o vetor — vale igual em Rust (`tracing::info!`)"),
    "P-02": ([DECLARACAO, PYTHON, BACKEND], "retencao declarada vs job de "
             "purga; o job pode ser escrito em qualquer linguagem"),
    "P-03": ([PYTHON, BACKEND, SQL], "soft-delete sem eliminacao: o modelo e "
             "a migracao existem em qualquer stack"),
    "P-04": ([DECLARACAO], "catalogo de dados e artefato declarativo puro"),
    "P-05": ([RUNTIME], "DTO recusando campo fora da allowlist, provado na borda"),
    "P-06": ([PYTHON, BACKEND], "chave de pseudonimizacao em texto claro — "
             "literal hardcoded existe em qualquer linguagem"),
    "P-07": ([DECLARACAO, RUNTIME], "modelo de consentimento declarativo + "
             "prova na borda"),
    "P-08": ([DECLARACAO], "base legal de campo sensivel, no catalogo"),
    "P-09": ([RUNTIME], "k-anonimato medido na resposta da agregacao"),
    "P-10": ([RUNTIME], "endpoint de exportacao"),
    "P-11": ([RUNTIME], "403 vs 404 distinguivel"),
    "P-13": ([WEB], "checkbox pre-marcado e JSX. NAO EXISTE fora do navegador"),
    "P-14": ([WEB], "localStorage e URL do cliente. NAO EXISTE fora do navegador"),
    "P-15": ([PYTHON], "campo virando feature de treino — chamada de `fit`"),
    "P-16": ([PYTHON, DECLARACAO], "dataset de treino carregado no pipeline"),
    "P-17": ([PYTHON, BACKEND, DECLARACAO], "rota de busca aceitando filtro "
             "sensivel: le a view E a spec OpenAPI. A view existe em qualquer "
             "linguagem de servidor"),
    "P-18": ([DECLARACAO, PYTHON, BACKEND], "campo sensivel sem cifra: cruza "
             "catalogo com a chamada de cifra, que existe em qualquer stack"),
    "P-19": ([PYTHON, BACKEND], "produtor de evento em barramento append-only "
             "— Kafka, NATS e event store tem cliente em toda linguagem"),
    "P-20": ([PYTHON, BACKEND], "hash deterministico de identificador — "
             "`sha256(cpf)` em Rust e o mesmo defeito"),
    "P-22": ([RUNTIME], "consentimento observado no navegador"),
    "P-23": ([RUNTIME], "PII na URL entregue"),
    "P-24": ([RUNTIME], "EXIF em arquivo publicado"),

    # ------------------------------------------------------------- seguranca
    "S-01": ([RUNTIME], "BOLA/IDOR: sonda cruzando identidades"),
    "S-02": ([RUNTIME], "rate limit medido no alvo"),
    "S-03": ([RUNTIME], "payload de erro observado"),
    "S-04": ([PYTHON, BACKEND, WEB, DECLARACAO], "host externo no codigo — "
             "URL literal existe em qualquer linguagem"),
    "S-05": ([DECLARACAO], "campos de egresso declarados no manifesto"),
    "S-06": ([PYTHON, BACKEND, WEB], "credencial hardcoded. O vetor mais "
             "universal que existe: um literal de chave num `.rs` e "
             "exatamente a mesma exposicao que num `.py`"),
    "S-07": ([RUNTIME], "propagacao de finalidade na requisicao"),
    "S-08": ([DECLARACAO], "residencia declarada no manifesto de terceiros"),
    "S-09": ([WEB], "token guardado pelo codigo do front. NAO EXISTE fora do "
             "navegador"),
    "S-10": ([PYTHON, BACKEND], "entrada do usuario chegando ao prompt"),
    "S-11": ([PYTHON, BACKEND], "saida do modelo em sink perigoso"),
    "S-12": ([DECLARACAO, PYTHON, BACKEND], "ontologia no contrato OpenAPI "
             "cruzada com o DTO; o DTO existe em qualquer linguagem"),
    "S-13": ([PYTHON, BACKEND], "resposta de erro expondo pilha — todo "
             "framework tem o vetor, incluindo os de Rust"),
    "S-14": ([INFRA], "dump de producao restaurado: script e pipeline de CI"),
    "S-15": ([SQL], "GRANT em migracao SQL"),
    "S-16": ([PYTHON, BACKEND], "regiao literal na chamada de persistencia — "
             "`region_name` ou host de conexao existe em qualquer cliente"),
    "S-17": ([RUNTIME], "cookie observado no navegador"),
    "S-18": ([RUNTIME], "terceiro contactado no carregamento"),
    "S-19": ([RUNTIME], "cabecalhos da resposta"),
    "S-20": ([RUNTIME], "credencial no bundle servido"),
    "S-21": ([RUNTIME], "sourcemap referenciado no bundle servido"),
}


def _linguagens_do_alvo(alcance: dict) -> tuple:
    lidas = {x["linguagem"] for x in alcance.get("lidos") or []}
    fora = {x["linguagem"] for x in alcance.get("fora_de_alcance") or []}
    # Alcance parcial conta como PRESENTE para todo mundo e como LIDA so
    # para os checks nomeados. E o que impede as duas mentiras opostas:
    # "Rust foi auditado" (seria falso para 15 checks) e "Rust nao foi
    # olhado" (seria falso para os 4 que agora olham).
    parcial = {x["linguagem"]: set(x.get("checks") or [])
               for x in alcance.get("alcance_parcial") or []}
    return lidas, fora | set(parcial), parcial


# Linguagens em que codigo de SERVIDOR e escrito. Lista POSITIVA, e nao a
# lista do contrario, por um motivo que a primeira versao deste modulo
# aprendeu errando: com uma lista de exclusao, `.pyi` e `.jsonl` do btv
# entravam como "linguagem de backend nao lida" e apareciam em 19 checks
# como lacuna. Nao sao lacuna — um stub de tipos nao tem instrucao que
# execute, e um `.jsonl` e dado. Ruido dessa natureza e caro aqui: ele
# aparece ao lado de Rust, que E a lacuna de verdade, e dilui a unica
# informacao que este mapa existe para dar.
#
# Inclui JS/TS de proposito, e o motivo e o inverso do que parece: a suite
# NAO consegue distinguir um `.ts` de servidor (Node) de um `.ts` de
# navegador. Deixar JS/TS de fora faria um alvo Node puro cair em
# `nao_aplicavel` — o estado que mais se parece com verde — quando o certo
# e `auditado`. Deixar dentro, no maximo, faz um alvo poliglota parecer
# menos cego do que e; e por isso o estado nunca colapsa: no btv, TS lido
# NAO apaga Rust cego, so muda `fora_de_alcance` para `auditado_parcial`.
#
# Ficam de fora `shell` e `SQL`: sao substrato de familia propria (INFRA e
# SQL), e conta-los como backend faria um repositorio de scripts + Rust
# parecer meio auditado quando nenhuma linha da logica foi lida.
LINGUAGENS_DE_SERVIDOR = {
    "Python", "Rust", "Go", "Java", "Kotlin", "Ruby", "PHP", "C#",
    "Scala", "Elixir", "Erlang", "C", "C++", "C/C++", "Swift", "Objective-C",
    "Perl", "Lua", "Dart",
    "JavaScript", "JavaScript/JSX", "TypeScript", "TypeScript/TSX",
}


def extensoes_de_substrato_indeterminado(alcance: dict) -> list:
    """Extensoes fora de alcance que a suite nao sabe sequer NOMEAR.

    O preco de usar lista positiva e este: uma extensao que a suite nao
    reconhece nao entra em familia nenhuma, e portanto some do mapa por
    check. Somir em silencio seria a mesma omissao que esta rodada existe
    para combater, entao ela reaparece AQUI, em bloco proprio, dizendo o que
    e: nao se sabe se e codigo de servidor, porque ninguem olhou.
    """
    return sorted(
        ({"linguagem": x["linguagem"], "arquivos": x["arquivos"]}
         for x in alcance.get("fora_de_alcance") or []
         if "nao reconhecida" in x["linguagem"]),
        key=lambda x: -x["arquivos"])


def _familia_alcancada(familia: str, lidas: set, fora: set) -> tuple:
    """(linguagens_presentes, linguagens_lidas) desta familia NESTE alvo.

    BACKEND e resolvido contra o alvo concreto, e por LINGUAGEM — nao por
    sim/nao. E a diferenca que faz o mapa valer: dizer que P-01 "foi
    auditado" no btv porque a orquestracao Python foi lida esconderia que o
    motor, com 38 mil linhas de Rust, nao foi olhado. O estado tem de
    carregar as duas metades.
    """
    if familia == RUNTIME:
        # Nao depende de parser de linguagem nenhuma: ou o alvo esta no ar,
        # ou nao. E por isso a parte da suite que um alvo poliglota nunca
        # perde — o navegador ve a aplicacao, nao o codigo-fonte.
        return {"(aplicacao no ar)"}, {"(aplicacao no ar)"}
    if familia == BACKEND:
        presentes = (lidas | fora) & LINGUAGENS_DE_SERVIDOR
        return presentes, presentes & lidas
    alvo = LINGUAGENS_DA_FAMILIA.get(familia, set())
    return lidas & alvo | (fora & alvo), lidas & alvo


def teria_vetor_em_linguagem_de_servidor(check_id: str) -> bool:
    """Este check acharia algo num backend escrito em Rust, Go ou Java?

    E A pergunta desta rodada, e ela e respondida pelo SUBSTRATO declarado,
    nao por intuicao: um check com a familia `qualquer_backend` tem vetor em
    QUALQUER linguagem de servidor; um com familia `web` ou `runtime` nao
    ganharia nada com parser nenhum. Sem esta separacao, "a PSE deveria
    falar Rust?" so tem resposta por impressao.
    """
    substrato = SUBSTRATO.get(check_id)
    return bool(substrato) and BACKEND in substrato[0]


def classificar(check_id: str, laudo: dict) -> dict:
    """Estado deste check contra ESTE alvo, com o motivo.

    A ordem importa: o que o LAUDO ja disse vence a inferencia. Um check
    indeterminado nao pode virar "auditado" so porque a linguagem dele foi
    lida — ele tentou e nao decidiu, e isso e uma verdade mais forte.
    """
    substrato = SUBSTRATO.get(check_id)
    if substrato is None:
        return {"estado": "sem_substrato_declarado",
                "motivo": "check sem substrato declarado em pse/cobertura.py — "
                          "o mapa nao consegue dizer se ele foi cego ou nao"}
    familias, nota = substrato
    alcance = laudo.get("alcance") or {}
    lidas, fora, parcial = _linguagens_do_alvo(alcance)
    # As linguagens de alcance parcial que alcancam ESTE check contam como
    # lidas para ele — e so para ele.
    lidas = lidas | {ling for ling, checks in parcial.items()
                    if check_id in checks}
    # SONDA DE SUBSTRATO: linguagem em que o vetor deste check NAO EXISTE
    # sai da conta inteira. Nao-aplicavel medido, e nao alegado — a
    # diferenca entre este mapa e uma tabela de marketing.
    ausentes = set((laudo.get("sondas") or {}).get(check_id) or [])
    fora = fora - ausentes
    lidas = lidas - ausentes

    # O proprio laudo ja declara quando um check rodou PELA METADE — P-09
    # mede k-anonimato na resposta da agregacao, e em `pse_passive` a metade
    # runtime nao dispara. Ignorar esse relatorio faria o mapa marcar P-09
    # como auditado integral, que e o falso verde deste documento acontecendo
    # dentro do documento. O sinal ja existia; faltava consumi-lo.
    parciais = (laudo.get("relatorios") or {}).get("cobertura_parcial") or {}
    indeterminados = {c["id"]: c["motivo"] for c in
                      laudo.get("checks_indeterminados") or []}
    nao_habilitados = {c["id"]: c["motivo"] for c in
                       laudo.get("checks_nao_habilitados") or []}
    pulados = {c["id"]: c["motivo"] for c in laudo.get("checks_pulados") or []}

    if check_id in indeterminados:
        return {"estado": INDETERMINADO, "motivo": indeterminados[check_id],
                "familias": familias, "nota": nota, "no_laudo": INDETERMINADO,
                "motivo_no_laudo": indeterminados[check_id]}
    if check_id in nao_habilitados:
        return {"estado": NAO_HABILITADO, "motivo": nao_habilitados[check_id],
                "familias": familias, "nota": nota, "no_laudo": NAO_HABILITADO,
                "motivo_no_laudo": nao_habilitados[check_id]}

    presentes, lidas_ok = set(), set()
    for f in familias:
        existe, leu = _familia_alcancada(f, lidas, fora)
        presentes |= existe
        lidas_ok |= leu
    cegas = presentes - lidas_ok

    # DOIS EIXOS, e junta-los seria refazer o erro em outra escala. O ESTADO
    # responde "a suite leu o substrato onde o vetor vive"; `no_laudo`
    # responde "o check chegou a decidir alguma coisa". Um check PULADO com
    # motivo declarado (S-18 sem manifesto de terceiros para comparar) tem
    # substrato plenamente alcancado e mesmo assim nao concluiu nada — e
    # mostra-lo apenas como AUDITADO diria "olhei e esta limpo" sobre um
    # check que nao olhou coisa alguma.
    base = {"familias": familias, "nota": nota,
            "linguagens_do_substrato": sorted(presentes),
            "linguagens_lidas": sorted(lidas_ok),
            "linguagens_cegas": sorted(cegas),
            "no_laudo": (PULADO if check_id in pulados else
                         PARCIAL if check_id in parciais else "executou"),
            "motivo_no_laudo": pulados.get(check_id) or parciais.get(check_id, "")}

    if not presentes:
        return {**base, "estado": NAO_APLICAVEL,
                "motivo": f"o substrato deste check ({', '.join(familias)}) nao "
                          f"existe neste alvo — {nota}"}

    if not lidas_ok:
        return {**base, "estado": FORA_DE_ALCANCE,
                "motivo": (f"o vetor EXISTE no alvo, em {sorted(presentes)}, e a "
                           f"suite nao le essa(s) linguagem(ns). Ausencia de "
                           f"achado aqui significa 'nao olhei' — {nota}")}

    motivo = (f"a suite leu {sorted(lidas_ok)}. Ausencia de achado ALI "
              f"significa mesmo 'olhei e esta limpo'.")
    if check_id in pulados:
        motivo += f" Pulado com motivo declarado: {pulados[check_id]}"
    if cegas:
        return {**base, "estado": AUDITADO_PARCIAL,
                "motivo": (motivo + f" MAS o mesmo vetor existe em "
                           f"{sorted(cegas)}, que a suite nao le — essa metade "
                           f"NAO foi auditada.")}
    return {**base, "estado": AUDITADO, "motivo": motivo}


def mapear(laudo: dict) -> dict:
    """Mapa completo: todos os checks do catalogo, nenhum estado silencioso."""
    por_check = {cid: classificar(cid, laudo) for cid in sorted(catalogo.CATALOGO)}
    contagem = Counter(v["estado"] for v in por_check.values())
    return {
        "por_check": por_check,
        "contagem": dict(contagem),
        "total": len(por_check),
        "cegos_com_vetor": sorted(
            cid for cid, v in por_check.items() if v["estado"] == FORA_DE_ALCANCE),
        "parcialmente_cegos": sorted(
            cid for cid, v in por_check.items() if v["estado"] == AUDITADO_PARCIAL),
        "substrato_indeterminado": extensoes_de_substrato_indeterminado(
            laudo.get("alcance") or {}),
        "pulados": sorted(cid for cid, v in por_check.items()
                          if v.get("no_laudo") == PULADO),
        "meia_execucao": sorted(cid for cid, v in por_check.items()
                                if v.get("no_laudo") == PARCIAL),
    }


# ============================================================ escopo
# O QUE UM PARSER DE RUST COMPRARIA, POR CHECK.
#
# Nao e a mesma pergunta que "o check tem vetor em Rust". Todo check de
# `qualquer_backend` tem. A pergunta de ESCOPO e quanto de maquina cada um
# exige — e a resposta separa uma tarde de trabalho de um trimestre.
#
# Tres degraus, em ordem de custo. O primeiro nao precisa de gramatica
# nenhuma; o terceiro precisa entender atributo e derive, que e onde os
# frameworks de Rust escondem a semantica que interessa.
LITERAL = "literal"        # literais de string com posicao — um lexer basta
CHAMADA = "chamada"        # chamada e macro, com nome do alvo e argumentos
ESTRUTURA = "estrutura"    # item, atributo, derive: a semantica do framework

CUSTO_DO_DEGRAU = {
    LITERAL: ("Nenhuma gramatica. Basta varrer literais de string do `.rs` "
              "ignorando comentario — a mesma coisa que `codigo_efetivo` ja "
              "faz para `.js`, e Rust comenta igual (`//`, `/* */`)."),
    CHAMADA: ("`tree-sitter-rust`, que existe e e mantido. O trabalho real "
              "nao e o parser: e que macro (`tracing::info!`) e chamada nao "
              "sao o mesmo NO de arvore, e cada check teria de olhar os "
              "dois."),
    ESTRUTURA: ("`tree-sitter-rust` MAIS um modelo de atributo e derive — "
                "`#[derive(Serialize)]`, `#[serde(rename)]`, as macros de "
                "rota do axum. E aqui que o custo deixa de ser do parser e "
                "passa a ser de conhecer cada framework."),
}

EXIGENCIA_DE_PARSER = {
    "S-04": (LITERAL, "host externo e uma URL literal; nada mais e preciso"),
    "S-06": (LITERAL, "credencial hardcoded e literal por definicao — o "
             "vetor mais universal da suite, e o mais barato de alcancar"),
    "S-16": (LITERAL, "regiao aparece como literal (`us-east-1`) ou host de "
             "conexao, os dois literais"),
    "P-06": (LITERAL, "chave de pseudonimizacao em texto claro e literal"),
    "P-01": (CHAMADA, "logger: em Rust o vetor e MACRO (`tracing::info!`, "
             "`println!`) e o argumento e um template — precisa do no"),
    "P-02": (CHAMADA, "job de purga: chamada de delete/expire ligada a "
             "retencao declarada"),
    "P-19": (CHAMADA, "produtor de evento: `producer.send`, `js.publish`"),
    "P-20": (CHAMADA, "hash sem chave: `Sha256::digest(cpf)` — o defeito "
             "esta em QUEM entra na chamada, nao no nome dela"),
    "P-18": (CHAMADA, "cruza campo sensivel do catalogo com chamada de cifra"),
    "S-13": (CHAMADA, "pilha em resposta: `format!(\"{:?}\", e)` no corpo do "
             "handler de erro"),
    "S-10": (CHAMADA, "entrada do usuario concatenada ate o prompt"),
    "S-11": (CHAMADA, "saida do modelo chegando a sink perigoso"),
    "E-00": (CHAMADA, "sinal de decisao automatizada: chamada de inferencia"),
    "E-11": (CHAMADA, "PII indo para o cliente HTTP do LLM"),
    "E-12": (CHAMADA, "derivado exportado como anonimo"),
    "E-01": (CHAMADA, "explicacao anexada a decisao"),
    "E-02": (CHAMADA, "escrita no decision log"),
    "P-03": (ESTRUTURA, "soft-delete: campo `deleted_at` no modelo do ORM "
             "(Diesel, SeaORM) — vive em derive, nao em chamada"),
    "P-17": (ESTRUTURA, "rota de busca: o filtro esta no struct de query e "
             "na macro de rota do framework"),
    "S-12": (ESTRUTURA, "DTO cruzado com o contrato: os nomes de campo que "
             "importam estao em `#[serde(rename)]`"),
    "E-04": (ESTRUTURA, "rota de revisao humana: definicao de rota"),
}

def escopo(mapa: dict) -> dict:
    """Agrupa por degrau os checks que um parser da linguagem cega compraria.

    Duas listas por degrau, e nao uma. `cegos_agora` sao os que rodaram e
    ficaram meio ou totalmente cegos — o ganho imediato. `nao_executaram`
    sao os que tem o mesmo vetor mas nem chegaram a rodar neste alvo
    (indeterminados, ou Trabalho A sem alvo). Somar os dois inflaria o ganho
    do parser; omitir os segundos o esconderia, porque no dia em que a causa
    da indeterminacao for resolvida eles caem exatamente no mesmo buraco.
    """
    cegos = set(mapa["cegos_com_vetor"]) | set(mapa["parcialmente_cegos"])
    por_degrau, sem_exigencia = {}, []
    for cid in sorted(cegos):
        if cid not in EXIGENCIA_DE_PARSER:
            sem_exigencia.append(cid)
    for cid, (degrau, _) in sorted(EXIGENCIA_DE_PARSER.items()):
        alvo = por_degrau.setdefault(degrau, {"cegos_agora": [],
                                              "nao_executaram": []})
        alvo["cegos_agora" if cid in cegos else "nao_executaram"].append(cid)
    nunca = sorted(cid for cid in catalogo.CATALOGO
                   if not teria_vetor_em_linguagem_de_servidor(cid))
    return {"por_degrau": por_degrau, "sem_exigencia_declarada": sem_exigencia,
            "nunca_precisariam": nunca,
            "total_com_vetor": len(EXIGENCIA_DE_PARSER)}


# Leitura editorial da decisao de escopo. Fica declarada, como as leituras da
# matriz: recomendacao sem assinatura e opiniao anonima. As CONTAGENS sao
# interpoladas do mapa, nunca escritas na prosa — numero escrito a mao numa
# recomendacao envelhece em silencio e passa a contradizer a tabela logo
# abaixo dele, que e a forma mais barata de perder a confianca do leitor.
def recomendacao(esc: dict) -> str:
    def n(degrau, chave="cegos_agora"):
        return len(esc["por_degrau"].get(degrau, {}).get(chave, []))

    def ids(degrau, chave="cegos_agora"):
        return ", ".join(esc["por_degrau"].get(degrau, {}).get(chave, [])) or "—"

    return f"""\
**O degrau `literal` compra {n(LITERAL)} checks por um custo que nao e de
parser.** {ids(LITERAL)} dependem apenas de literais de string com posicao.
Rust comenta como JavaScript, e `scan.codigo_efetivo` ja apaga comentario
preservando literal — a extensao `.rs` entraria nesse caminho sem gramatica
nenhuma. Sao os de vetor mais universal, e aqueles cuja ausencia hoje e mais
enganosa: `S-06` existe justamente para achar chave em codigo, e as 38 mil
linhas de Rust do btv nunca foram olhadas por ele.

**O degrau `chamada` compra {n(CHAMADA)}, e ai o custo e real.** Precisa de
`tree-sitter-rust` e — o que costuma ser esquecido — de tratar MACRO como
chamada: o logger de Rust e `tracing::info!`, nao `logger.info()`, e um check
que so olhe `call_expression` acha zero e diz que esta limpo. Esse e o modo
de falhar que esta suite menos pode se permitir, porque produz verde.

**O degrau `estrutura` compra {n(ESTRUTURA)}, e nao se recomenda agora.**
{ids(ESTRUTURA)} dependem de derive e de macro de rota; o custo deixa de ser
o parser e passa a ser conhecer axum, Diesel e serde um a um. Cobertura de
fachada nasce exatamente assim — de um parser que le a arvore mas nao entende
o framework, nao acha nada, e parece verde.

**{len(esc['nunca_precisariam'])} dos checks nunca precisariam de parser de
Rust.** Os de `runtime` observam a aplicacao no ar e nao leem fonte; os de
`declaracao` leem catalogo, manifesto e contrato; os de `web` (P-13, P-14,
S-09) tem vetor que nao existe fora do navegador. Nenhum parser move um
milimetro nesses — e sabe-lo e o que impede de vender um parser como se ele
resolvesse a cobertura inteira.
"""


# ============================================================ volume
# Quantas LINHAS do alvo cada linguagem tem. `alcance.medir` conta ARQUIVOS
# de proposito (contar linhas do que nao se leu seria incoerente com o que o
# bloco diz). Aqui a incoerencia nao existe: o mapa de cobertura precisa da
# PROPORCAO, e proporcao em arquivo engana quando um `.rs` tem 300 linhas e
# um `.json` tem 4. Contar `\n` nao e ler: nao ha parser, nao ha decisao, e
# nenhum achado sai daqui.

def sondar_substrato(repo, data: dict) -> dict:
    """{check_id: [linguagens onde o vetor NAO existe]}.

    E o que faz `nao_aplicavel` ser MEDIDO. Sem esta sonda, dizer que o
    Rust de um alvo e "majoritariamente nao-aplicavel" seria alegacao — e
    alegar nao-aplicabilidade e a forma mais confortavel de inflar
    cobertura, exatamente o que este mapa foi criado para impedir.

    A sonda so empurra para NAO-APLICAVEL. Marca PRESENTE nao vira achado:
    significa que o vetor existe e que o check segue cego naquela metade.
    """
    from pathlib import Path

    from pse.engine import rustscan, scan
    sondas = (data.get("rust") or {}).get("sondas") or {}
    if not sondas:
        return {}
    textos = [rustscan.efetivo(scan.ler(p), sem_literais=True)
              for p in scan.arquivos(Path(repo), {".rs"})]
    if not textos:
        return {}
    saida = {}
    for check_id, marcas in sondas.items():
        if not any(rustscan.contem_token(t, marcas) for t in textos):
            saida[check_id] = ["Rust"]
    return saida


def censo_de_parse(repo) -> dict:
    """Dos arquivos que a suite SABE ler, quantos ela conseguiu ler?

    O bloco `alcance` responde "que linguagens tem parser". Isto responde a
    pergunta seguinte, e o btv mostrou que ela nao e a mesma: `.ts` e `.tsx`
    tem parser, sao a MAIOR fatia do alvo em numero de arquivos (165 de 174
    do estrato web) — e tres arquivos que nenhuma gramatica alcanca faziam
    P-13, P-14 e S-09 pararem antes de olhar os outros 171.

    Ter parser para a linguagem e ter lido o arquivo sao coisas diferentes,
    e o mapa nao pode confundi-las. Este censo e o unico lugar onde a
    diferenca aparece por numero.
    """
    from pathlib import Path as _P

    from pse.engine import jsast, scan
    from pse.model import CheckIndeterminado
    lidos, ilegiveis = 0, []
    for caminho in scan.arquivos(_P(repo), jsast.EXTS):
        try:
            jsast.arvore(caminho, scan.ler(caminho))
            lidos += 1
        except CheckIndeterminado as e:
            ilegiveis.append({"arquivo": scan.rel(_P(repo), caminho),
                              "motivo": str(e)})
        except Exception as e:            # noqa: BLE001
            ilegiveis.append({"arquivo": scan.rel(_P(repo), caminho),
                              "motivo": f"{type(e).__name__}: {e}"})
    total = lidos + len(ilegiveis)
    return {
        "familia": "JavaScript/TypeScript (tree-sitter)",
        "arquivos": total, "analisados": lidos,
        "nao_analisados": len(ilegiveis),
        "percentual_analisado": round(100 * lidos / total, 1) if total else 0.0,
        "ilegiveis": ilegiveis,
        "nota": ("Ter parser para a linguagem e ter conseguido ler o arquivo "
                 "sao coisas diferentes. Arquivo nao analisado nao produz "
                 "achado e nao produz conformidade — ele nao produz nada, e "
                 "por isso o check que o encontrou segue indeterminado mesmo "
                 "tendo lido todos os outros."),
    }


def volume_por_linguagem(repo) -> dict:
    """{linguagem: {"arquivos": n, "linhas": n, "lida": bool|"parcial"}}."""
    from pathlib import Path

    from pse.engine import scan
    saida = {}
    for p in sorted(Path(repo).rglob("*")):
        if any(x in scan.IGNORAR_DIRS for x in p.parts) or not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in COM_PARSER:
            rotulo, lida = COM_PARSER[ext][0], True
        elif ext in ALCANCE_PARCIAL:
            rotulo, lida = ALCANCE_PARCIAL[ext][0], "parcial"
        elif ext in SEM_PARSER:
            rotulo, lida = SEM_PARSER[ext], False
        elif ext in IRRELEVANTES or not ext:
            continue
        else:
            rotulo, lida = f"{ext} (nao reconhecida)", False
        try:
            n = len(p.read_bytes().split(b"\n"))
        except OSError:
            n = 0
        alvo = saida.setdefault(rotulo, {"arquivos": 0, "linhas": 0, "lida": lida})
        alvo["arquivos"] += 1
        alvo["linhas"] += n
    return saida


def proporcao(volume: dict) -> dict:
    """Quanto do alvo, em linhas, a suite consegue ler.

    O numero honesto que a decisao de escopo precisa. Sem ele, "a PSE nao le
    Rust" e um fato sem tamanho — e tamanho e o que separa uma lacuna
    aceitavel de uma que invalida o laudo.
    """
    lidas = sum(v["linhas"] for v in volume.values() if v["lida"] is True)
    parciais = sum(v["linhas"] for v in volume.values() if v["lida"] == "parcial")
    cegas = sum(v["linhas"] for v in volume.values() if v["lida"] is False)
    total = lidas + parciais + cegas
    def pct(x):
        return round(100 * x / total, 1) if total else 0.0
    return {
        "linhas_lidas": lidas,
        # Linha de alcance parcial NAO entra em `lidas`, e a separacao e o
        # ponto: 38 mil linhas de Rust sao olhadas por QUATRO checks e
        # invisiveis para os outros. Soma-las ao lido faria a proporcao
        # saltar de 47% para 98% e a suite passaria a mentir por
        # arredondamento — o alcance textual nao le a linguagem, alcanca
        # quatro vetores dela.
        "linhas_em_alcance_parcial": parciais,
        "linhas_cegas": cegas, "linhas_total": total,
        "percentual_lido": pct(lidas),
        "percentual_alcance_parcial": pct(parciais),
        "percentual_cego": pct(cegas),
    }


# ============================================================ medicao
# A medicao e um INSTANTANEO DATADO de um alvo concreto, e o documento e
# gerado dela — nunca do alvo ao vivo. O motivo e o mesmo pelo qual
# `docs/matriz-dominio.md` e gerado do catalogo: um documento que dependa de
# um clone que pode nao existir na maquina de quem le nao e reproduzivel, e
# um mapa que so uma pessoa consegue reproduzir nao e verificavel.
#
# A medicao guarda o que o mapa precisa e nada mais: os baldes do laudo, o
# bloco `alcance` e o volume por linguagem. O CRUZAMENTO com o substrato
# acontece na geracao, contra o codigo — assim, melhorar o julgamento de
# substrato regenera um documento melhor a partir do MESMO instantaneo, sem
# precisar do alvo de novo.

def resumir_laudo(laudo: dict) -> dict:
    """So o que o mapa consome. Laudo inteiro no repositorio seria evidencia
    do alvo versionada aqui — o que nao cabe a esta suite guardar."""
    def baldes(chave):
        # `checks_executados` e lista de ID; os outros baldes sao dicionarios
        # com motivo. Normalizar aqui, e nao no laudo, e deliberado: o formato
        # do laudo e contrato publicado e nao muda por conveniencia deste mapa.
        itens = [c if isinstance(c, dict) else {"id": c}
                 for c in laudo.get(chave) or []]
        return [{"id": c["id"], "motivo": c.get("motivo", "")}
                for c in sorted(itens, key=lambda c: c["id"])]
    # `relatorios` entra porque `cobertura_parcial` e `observacao_de_rede`
    # sao evidencia de cobertura, nao decoracao do laudo: um diz que o check
    # rodou pela metade, o outro diz o que a camada dinamica chegou a ver.
    relatorios = laudo.get("relatorios") or {}
    return {
        "veredito": laudo.get("veredito"),
        "sondas": laudo.get("sondas") or {},
        "relatorios": {k: relatorios[k] for k in (
            "cobertura_parcial", "observacao_de_rede",
            "recursos_nao_varridos", "cabecalhos_informativos_ausentes")
            if k in relatorios},
        "exit_code": laudo.get("exit_code"),
        "alcance": laudo.get("alcance") or {},
        "checks_executados": baldes("checks_executados"),
        "checks_pulados": baldes("checks_pulados"),
        "checks_indeterminados": baldes("checks_indeterminados"),
        "checks_nao_habilitados": baldes("checks_nao_habilitados"),
        "findings": [{"check_id": f["check_id"], "severidade": f["severidade"],
                      "titulo": f["titulo"]}
                     for f in sorted(laudo.get("findings") or [],
                                     key=lambda f: (f["check_id"], f["titulo"]))],
    }


def medir_alvo(repo, laudo: dict, data: dict | None = None) -> dict:
    """Instantaneo pronto para virar `aceites/<alvo>-medicao.json`."""
    if data is not None and "sondas" not in laudo:
        laudo = {**laudo, "sondas": sondar_substrato(repo, data)}
    volume = volume_por_linguagem(repo)
    return {"laudo": resumir_laudo(laudo), "volume": volume,
            "proporcao": proporcao(volume), "parse": censo_de_parse(repo)}


# ============================================================ geracao
#     python -m pse.cobertura aceites/btv-medicao.json > docs/cobertura-btv.md

ROTULO = {
    AUDITADO: "AUDITADO",
    AUDITADO_PARCIAL: "AUDITADO PARCIAL",
    FORA_DE_ALCANCE: "FORA DE ALCANCE",
    NAO_APLICAVEL: "NAO APLICAVEL",
    INDETERMINADO: "INDETERMINADO",
    NAO_HABILITADO: "NAO HABILITADO",
}

ORDEM_DOS_ESTADOS = (AUDITADO, AUDITADO_PARCIAL, FORA_DE_ALCANCE,
                     NAO_APLICAVEL, INDETERMINADO, NAO_HABILITADO)

GLOSSARIO = (
    (AUDITADO, "a suite leu o substrato onde o vetor deste check vive. "
     "*Sem achado* aqui significa **olhei e esta limpo**."),
    (AUDITADO_PARCIAL, "o substrato existe em mais de uma linguagem do alvo "
     "e a suite leu parte. *Sem achado* significa **olhei metade** — e a "
     "metade nao olhada esta nomeada na linha."),
    (FORA_DE_ALCANCE, "o vetor EXISTE no alvo, numa linguagem sem parser. "
     "*Sem achado* significa **nao olhei**."),
    (NAO_APLICAVEL, "o vetor nao existe neste alvo. Nao ha o que ler nem o "
     "que perder."),
    (INDETERMINADO, "tentou e nao decidiu. O laudo ja diz isso, e bloqueia."),
    (NAO_HABILITADO, "Trabalho A sem alvo declarado: nao foi executado."),
)


def _tabela_por_dominio(mapa: dict) -> list:
    doms = list(catalogo.DOMINIOS)
    L = ["| Dominio | " + " | ".join(ROTULO[e] for e in ORDEM_DOS_ESTADOS) +
         " | total |", "|---|" + "---|" * (len(ORDEM_DOS_ESTADOS) + 1)]
    for d in doms:
        ids = [c for c in sorted(catalogo.CATALOGO) if d in catalogo.dominios(c)]
        conta = Counter(mapa["por_check"][c]["estado"] for c in ids)
        L.append("| `" + d + "` | " +
                 " | ".join(str(conta.get(e, 0)) or "—" for e in ORDEM_DOS_ESTADOS) +
                 f" | {len(ids)} |")
    return L


def _tabela_por_check(mapa: dict) -> list:
    L = ["| Check | Dominio(s) | Alcance do substrato | No laudo | Leu | "
         "Cego em | Vetor em backend nao-Python? |",
         "|---|---|---|---|---|---|---|"]
    for cid in sorted(catalogo.CATALOGO, key=lambda c: (c[0], c)):
        v = mapa["por_check"][cid]
        leu = ", ".join(v.get("linguagens_lidas") or []) or "—"
        cego = ", ".join(v.get("linguagens_cegas") or []) or "—"
        vetor = "**sim**" if teria_vetor_em_linguagem_de_servidor(cid) else "nao"
        no_laudo = v.get("no_laudo", "executou")
        if no_laudo == PULADO:
            no_laudo = f"**pulado** — {v.get('motivo_no_laudo', '')}"
        elif no_laudo == PARCIAL:
            no_laudo = f"**so metade** — {v.get('motivo_no_laudo', '')}"
        else:
            no_laudo = ROTULO.get(no_laudo, no_laudo)
        L.append(f"| `{cid}` | {', '.join(catalogo.dominios(cid))} | "
                 f"{ROTULO.get(v['estado'], v['estado'])} | {no_laudo} | "
                 f"{leu} | {cego} | {vetor} |")
    return L


def gerar(medicao: dict, alvo: dict) -> str:
    laudo = medicao["laudo"]
    mapa = mapear(laudo)
    prop = medicao["proporcao"]
    esc = escopo(mapa)
    total = mapa["total"]

    L = [f"# Cobertura real da PSE contra `{alvo['nome']}`", ""]
    L += ["> **Gerado**, nunca escrito a mao:",
          f"> `python -m pse.cobertura {alvo['medicao_path']} > "
          f"docs/cobertura-{alvo['slug']}.md`.",
          "> O instantaneo e datado e vive no repositorio; o cruzamento com o",
          "> substrato de cada check acontece na geracao, contra o codigo. Ha",
          "> teste que reprova se este arquivo divergir de qualquer um dos dois.",
          ""]
    L += ["Este documento responde uma pergunta que o laudo sozinho nao "
          "responde:", "**do que a suite ficou cega, e isso importa?**", "",
          "Nao e para inflar cobertura nem para pedir desculpa por ela. E para "
          "que a", "decisao de escopo — *a PSE deveria aprender Rust?* — seja "
          "tomada com numero,", "nao com impressao.", ""]

    ant = alvo.get("anterior") or {}
    if ant:
        L += ["## Delta desta medicao", "",
              f"O que mudou desde `{ant['suite']}`, e por que. A rodada "
              "anterior mediu que",
              "53% do alvo estava cego e recomendou o degrau `literal`: quatro "
              "vetores",
              "alcancaveis sem gramatica nenhuma. Esta rodada implementou "
              "exatamente isso —",
              "nenhum parser, nenhum check novo, quatro checks existentes "
              "passando a", "reconhecer `.rs` por padrao textual ancorado.", "",
              "| | antes | agora |", "|---|---|---|"]
        agora_pl = sorted(c for c, v in mapa["por_check"].items()
                          if v["estado"] == AUDITADO
                          and v.get("no_laudo") == "executou")
        linhas_delta = [
            ("Linhas lidas por parser", f"{ant['percentual_lido']}%",
             f"{prop['percentual_lido']}%"),
            ("Linhas em alcance parcial (4 vetores)", "—",
             f"{prop.get('percentual_alcance_parcial', 0.0)}%"),
            ("Linhas cegas para TODO check", f"{ant['percentual_cego']}%",
             f"{prop['percentual_cego']}%"),
            ("Checks auditados de verdade", str(ant["auditados_de_verdade"]),
             str(len(agora_pl))),
            ("Checks meio-cegos em Rust", str(ant["parcialmente_cegos"]),
             str(len(mapa["parcialmente_cegos"]))),
        ]
        for rotulo, antes, agora in linhas_delta:
            L.append(f"| {rotulo} | {antes} | **{agora}** |")
        L += ["", "**A leitura honesta do delta.** O numero que encolheu de "
              "verdade foi o de linhas",
              "invisiveis para QUALQUER check — de "
              f"{ant['percentual_cego']}% para {prop['percentual_cego']}%. "
              "Mas ele encolheu porque",
              "38 mil linhas sairam de *cegas* e entraram em *alcance "
              "parcial*, nao em *lidas*:",
              "quatro checks passaram a olha-las e treze continuam sem ver "
              "nada ali. Ler a",
              "primeira linha da tabela como se fosse cobertura seria "
              "exatamente a fachada",
              "que esta serie de rodadas existe para impedir.", ""]

    L += ["## Procedencia da medicao", "",
          "| | |", "|---|---|",
          f"| Alvo | `{alvo['nome']}` |",
          f"| Commit do alvo | `{alvo['commit']}` |",
          f"| Medido em | {alvo['medido_em']} |",
          f"| Suite | `{alvo['suite']}` |",
          f"| Modo | {alvo['modo']} |",
          f"| Alvo no ar | {alvo['dinamico']} |", ""]

    L += ["## Os estados, e por que nenhum colapsa no outro", "",
          "Colapsar *fora de alcance* em *sem achado* e o verde falso que este",
          "documento existe para impedir. Sao coisas diferentes e ficam "
          "diferentes:", "",
          "| Estado | Significado |", "|---|---|"]
    for e, texto in GLOSSARIO:
        L.append(f"| **{ROTULO[e]}** | {texto} |")
    L += ["", "`AUDITADO PARCIAL` foi acrescentado por causa deste alvo. O btv "
          "e poliglota:", "a orquestracao e Python, o motor e Rust. Chamar P-01 "
          "de *auditado* porque a", "metade Python foi lida esconderia 38 mil "
          "linhas nao olhadas; chamar de *fora de", "alcance* apagaria o que "
          "ele de fato achou. Sao tres estados na pergunta e",
          "quatro na resposta porque o alvo real e poliglota — e fingir que "
          "nao e seria", "inventar uma simplicidade que os dados nao tem.", ""]

    parc = (laudo.get("alcance") or {}).get("alcance_parcial") or []
    if parc:
        L += ["## Alcance parcial: as linguagens que a suite NAO le e mesmo "
              "assim alcanca", "",
              "Terceira categoria, e ela existe para nao virar mentira nos "
              "dois sentidos.",
              "Dizer *lido* faria um leitor concluir que os 57 checks olharam "
              "o motor; dizer",
              "*nao lido* esconderia o alcance que existe, e o consumidor que "
              "corrigisse uma",
              "chave hardcoded no `.rs` nao entenderia de onde veio o achado.",
              "",
              "| Linguagem | Arquivos | Tecnica | Checks que alcancam |",
              "|---|---|---|---|"]
        for x in parc:
            L.append(f"| {x['linguagem']} | {x['arquivos']} | {x['tecnica']} | "
                     + " ".join(f"`{c}`" for c in x.get('checks') or []) + " |")
        L += ["", "**Ausencia de achado destes quatro significa *olhei e esta "
              "limpo*. Ausencia de", "achado de QUALQUER OUTRO check nestes "
              "arquivos nao significa nada** — eles nao", "foram olhados. E a "
              "mesma distincao do resto do documento, um nivel abaixo: o",
              "alcance textual nao le a linguagem, alcanca quatro vetores "
              "dela.", ""]

    vol = medicao["volume"]
    # ESTRATO, e nao rotulo de linguagem. `TypeScript` e `TypeScript/TSX` sao
    # rotulos separados no bloco `alcance` (ferramentas diferentes), e
    # compara-los um a um contra `Rust` divide o front em dois e faz o motor
    # parecer maior do que e em numero de arquivos. Somar o estrato web e o
    # que torna a comparacao honesta — e foi so somando que ficou visivel
    # que o front, e nao o motor, e a maior fatia por unidade examinada.
    ESTRATOS = {
        "web (JS/TS/JSX/TSX)": LINGUAGENS_DA_FAMILIA[WEB],
        "Rust (motor)": {"Rust"},
        "Python (orquestracao)": {"Python"},
        "declaracao (YAML/JSON)": LINGUAGENS_DA_FAMILIA[DECLARACAO],
    }
    def _soma(langs, campo):
        return sum(v[campo] for k, v in vol.items() if k in langs)
    linhas_estrato = sorted(
        ((nome, _soma(langs, "arquivos"), _soma(langs, "linhas"))
         for nome, langs in ESTRATOS.items()),
        key=lambda x: -x[1])
    outros_arq = sum(v["arquivos"] for k, v in vol.items()
                     if not any(k in langs for langs in ESTRATOS.values()))
    outras_lin = sum(v["linhas"] for k, v in vol.items()
                     if not any(k in langs for langs in ESTRATOS.values()))

    L += ["## Duas reguas de tamanho, e elas discordam", "",
          "**Nao ha uma resposta so para *qual e a maior fatia do alvo*, e "
          "escolher a que", "convem e como um mapa de cobertura mente sem "
          "dizer nada falso.**", "",
          "| Estrato | Arquivos | Linhas |", "|---|---|---|"]
    for nome, arq, lin in linhas_estrato:
        L.append(f"| {nome} | {arq} | {lin} |")
    L.append(f"| outros | {outros_arq} | {outras_lin} |")
    maior_arq = linhas_estrato[0]
    maior_lin = max(linhas_estrato, key=lambda x: x[2])
    L += ["",
          f"**Por ARQUIVOS o maior estrato e `{maior_arq[0]}`, com "
          f"{maior_arq[1]}. Por LINHAS e**",
          f"**`{maior_lin[0]}`, com {maior_lin[2]}.** As duas leituras sao "
          "verdadeiras e servem a", "perguntas diferentes.", "",
          "*Linhas* diz quanto CODIGO ficou sem parser — e a pergunta que "
          "decidiu nao",
          "escrever um parser de Rust. *Arquivos* diz quantas UNIDADES a "
          "suite examinou —",
          "e a pergunta certa para saber se o front foi auditado. Um `.rs` de "
          "motor e denso",
          "e um componente de tela e curto, entao o mesmo alvo troca de "
          "\"maior fatia\"", "conforme a regua.", "",
          "O documento passou a trazer as duas porque trazer so a primeira "
          "deixava a",
          "impressao de que o alvo era pouco auditavel — e isso nao e "
          "verdade. Rotulos de",
          "linguagem tambem eram somados errado: `TypeScript` e "
          "`TypeScript/TSX` aparecem",
          "separados no bloco `alcance` (ferramentas diferentes), e compara-"
          "los um a um",
          "contra `Rust` dividia o front em dois e fazia o motor parecer "
          "maior em numero", "de arquivos do que e.", ""]

    parse = medicao.get("parse")
    if parse:
        L += ["### Ter parser nao e ter lido", "",
              f"Dos **{parse['arquivos']}** arquivos JS/TS do alvo, a suite "
              f"analisou **{parse['analisados']}** "
              f"(**{parse['percentual_analisado']}%**)", "e nao conseguiu ler "
              f"**{parse['nao_analisados']}**:", ""]
        for x in parse["ilegiveis"]:
            L.append(f"  * `{x['arquivo']}`")
        L += ["", parse["nota"], "",
              "**Isto era um buraco de cobertura, e foi consertado.** Os "
              "checks de frontend",
              "chamavam o parser dentro do laco, e o primeiro arquivo "
              "ilegivel derrubava o",
              "check INTEIRO — os outros arquivos, que parseavam sem problema "
              "nenhum, ficavam",
              "sem veredito. O gate funcionava (exit 20) e a informacao se "
              "perdia: uma",
              "violacao real nos arquivos legiveis nunca seria reportada. "
              "Agora o arquivo",
              "ilegivel e contabilizado, os demais sao auditados, e os "
              "achados deles vao no",
              "laudo junto com a indeterminacao.", ""]

    L += ["## Proporcao do alvo que a suite consegue ler", "",
          f"**{prop['percentual_lido']}% lido, "
          f"{prop.get('percentual_alcance_parcial', 0.0)}% em alcance parcial "
          f"(4 vetores), {prop['percentual_cego']}% cego** — em linhas, nao em "
          f"arquivos.", "",
          "As tres fatias sao separadas de proposito. Somar o alcance parcial "
          "ao lido faria",
          f"a proporcao saltar de {prop['percentual_lido']}% para "
          f"{round(prop['percentual_lido'] + prop.get('percentual_alcance_parcial', 0.0), 1)}% "
          "e a suite passaria a mentir por",
          "arredondamento: aquelas linhas sao olhadas por quatro checks e "
          "invisiveis para", "os outros treze que tem vetor la.", "",
          "Linhas de proposito: `alcance` conta arquivos (contar linhas do que "
          "nao se leu",
          "seria incoerente com o que aquele bloco diz), mas proporcao em "
          "arquivo engana",
          "quando um `.rs` tem 300 linhas e um `.json` tem 4. Contar `\\n` nao "
          "e ler: nao ha", "parser, nao ha decisao, e nenhum achado sai daqui.",
          "",
          "| Linguagem | Arquivos | Linhas | A suite le? |", "|---|---|---|---|"]
    for k, v in sorted(medicao["volume"].items(), key=lambda kv: -kv[1]["linhas"]):
        estado = {True: "sim", False: "**nao**"}.get(
            v["lida"], "**parcial** (4 vetores)")
        L.append(f"| {k} | {v['arquivos']} | {v['linhas']} | {estado} |")
    L += ["| **total** | | "
          f"{prop['linhas_total']} | {prop['percentual_lido']}% lido |", ""]

    L += ["## Por dominio", "",
          "A soma de cada linha fecha o total de checks daquele dominio. Um "
          "check aparece",
          "em mais de uma linha quando examina mais de um estrato — e a mesma",
          "multiplicidade da matriz, nao erro de contagem.", ""]
    L += _tabela_por_dominio(mapa)
    L += ["", "| Estado | Checks | |", "|---|---|---|"]
    for e in ORDEM_DOS_ESTADOS:
        n = mapa["contagem"].get(e, 0)
        ids = sorted(c for c, v in mapa["por_check"].items() if v["estado"] == e)
        L.append(f"| **{ROTULO[e]}** | {n} | {' '.join(f'`{c}`' for c in ids) or '—'} |")
    L += [f"| **total** | {total} | |", "",
          f"A soma fecha {total}/{total}. Nenhum check fica sem estado: um "
          "check silencioso", "num mapa de cobertura e indistinguivel de um "
          "check que passou.", ""]

    plenos = sorted(c for c, v in mapa["por_check"].items()
                    if v["estado"] == AUDITADO and v.get("no_laudo") == "executou")
    L += ["### O numero que interessa", "",
          f"**{len(plenos)} dos {total} checks foram auditados DE VERDADE** — "
          "rodaram ate um", "veredito E tiveram todo o substrato lido. Sao os "
          "unicos em que *sem achado*", "significa mesmo *olhei e esta limpo*:",
          "", " ".join(f"`{c}`" for c in plenos) or "—", "",
          f"Os outros {total - len(plenos)} se dividem entre os que leram "
          "metade do substrato, os que", "foram pulados com motivo, os "
          "indeterminados e os que nem foram habilitados.",
          "Cada um desses e uma resposta legitima; nenhum deles e "
          "conformidade.", ""]

    zerados = [ROTULO[e] for e in (FORA_DE_ALCANCE, NAO_APLICAVEL)
               if not mapa["contagem"].get(e)]
    if zerados:
        L += [f"**{' e '.join(zerados)} deram zero neste alvo, e isso nao "
              "torna o estado decorativo.**", "",
              "`FORA DE ALCANCE` exige que TODA linguagem do substrato de um "
              "check esteja",
              "cega. No btv nenhum chega la porque a orquestracao Python e o "
              "front em TS",
              "foram lidos — o mesmo check contra um servico Rust puro sairia "
              "fora de",
              "alcance, e ha teste que prova exatamente isso com um alvo "
              "sintetico.",
              "`NAO APLICAVEL` exige que o substrato nao exista: o btv tem "
              "web, tem Python,",
              "tem SQL e esta no ar, entao nenhum dos cinco substratos falta. "
              "Um estado que", "so aparece quando e verdade e a unica forma "
              "dele valer alguma coisa.", ""]

    sondas = laudo.get("sondas") or {}
    if sondas:
        L += ["### Nao-aplicavel MEDIDO, e nao alegado", "",
              "Alegar que um vetor nao existe e a forma mais confortavel de "
              "inflar cobertura,",
              "e seria exatamente o que este mapa foi criado para impedir. "
              "Entao a suite",
              "SONDA: para cada check com vetor em backend, procura no codigo "
              "efetivo dos",
              "`.rs` — sem comentario e sem literal — as marcas daquele vetor. "
              "Ausencia de", "todas elas e a prova de que o vetor nao esta la.",
              "",
              "A sonda so empurra para *nao aplicavel*. Presenca de marca NAO "
              "e achado:", "significa que o vetor existe e que o check segue "
              "cego naquela metade — e por", "isso o resultado abaixo e "
              "pequeno, e nao grande.", "",
              "| Check | Vetor ausente em |", "|---|---|"]
        for cid, langs in sorted(sondas.items()):
            L.append(f"| `{cid}` | {', '.join(langs)} |")
        L += ["", f"Apenas {len(sondas)} dos checks tiveram o vetor "
              "efetivamente ausente do Rust do alvo.",
              "A expectativa que originou a rodada era de que o Rust do btv "
              "fosse *majoritariamente*",
              "nao-aplicavel — motor de execucao, sem consentimento nem dark "
              "pattern. A medicao", "**nao confirma isso**: logger, hash, "
              "serde, tratamento de erro e cliente HTTP",
              "estao todos presentes no motor, entao os vetores de P-01, "
              "S-13, P-20, S-12 e S-04",
              "existem la e seguem sem ser olhados. Registrar a divergencia e "
              "o ponto de medir.", ""]

    if mapa["substrato_indeterminado"]:
        L += ["### Extensoes que o mapa nao sabe classificar", "",
              "A suite nao reconhece estas extensoes, e por isso nao as atribui "
              "a familia de", "substrato nenhuma. Some do mapa por check; "
              "reaparece aqui, porque sumir em",
              "silencio seria a mesma omissao que este documento combate.", "",
              "| Extensao | Arquivos |", "|---|---|"]
        for x in mapa["substrato_indeterminado"]:
            L.append(f"| {x['linguagem']} | {x['arquivos']} |")
        L.append("")

    L += ["## Check a check", "",
          "**Duas colunas de estado, e junta-las seria refazer o mesmo erro "
          "em outra escala.**",
          "`Alcance do substrato` responde *a suite leu o codigo onde o vetor "
          "vive*;", "`No laudo` responde *o check chegou a decidir alguma "
          "coisa*. Sao independentes:", "um check pode ter substrato "
          "plenamente alcancado e mesmo assim ter sido PULADO",
          "com motivo declarado — S-18 nao tem manifesto de terceiros para "
          "comparar, e", "mostra-lo so como `AUDITADO` diria *olhei e esta "
          "limpo* sobre um check que", "nao olhou coisa alguma.", ""]
    pulados = mapa.get("pulados") or []
    if pulados:
        L += [f"Sao {len(pulados)} pulados neste alvo: "
              + " ".join(f"`{c}`" for c in pulados)
              + ". Pular com motivo nao bloqueia — mas nao e conformidade, e "
                "por isso nao pode", "desaparecer dentro do estado de "
                "alcance.", ""]
    L += ["A ultima coluna e a que decide escopo: ela nao pergunta se o check "
          "ficou cego",
          "neste alvo, e sim se o vetor dele existiria num backend escrito em "
          "Rust, Go ou",
          "Java. Sao perguntas diferentes, e so a segunda diz se um parser "
          "novo compra", "alguma coisa.", ""]
    L += _tabela_por_check(mapa)
    L.append("")

    L += ["## Recomendacao de escopo", "",
          "Nao ha decisao aqui: esta rodada foi de MEDICAO. O que segue e a "
          "leitura dos", "numeros acima, assinada, para que a decisao seja "
          "tomada sobre dados.", "", recomendacao(esc), ""]
    L += ["| Degrau | Custo | Cegos AGORA | Mesmo vetor, mas nao executaram |",
          "|---|---|---|---|"]
    for degrau in (LITERAL, CHAMADA, ESTRUTURA):
        d = esc["por_degrau"].get(degrau, {})
        agora = " ".join(f"`{c}`" for c in d.get("cegos_agora", [])) or "—"
        depois = " ".join(f"`{c}`" for c in d.get("nao_executaram", [])) or "—"
        L.append(f"| `{degrau}` | {CUSTO_DO_DEGRAU[degrau]} | {agora} | "
                 f"{depois} |")
    L += ["", "A ultima coluna nao entra na conta do ganho: sao checks que "
          "sequer rodaram", "neste alvo, e somar os dois inflaria o que o "
          "parser compra. Ficam a vista", "porque no dia em que a causa da "
          "indeterminacao for resolvida — identidade", "declarada, dataset de "
          "fairness — eles caem no mesmo buraco.", ""]
    if esc["sem_exigencia_declarada"]:
        L += ["> **Sem exigencia declarada:** "
              + " ".join(f"`{c}`" for c in esc["sem_exigencia_declarada"])
              + ". Um check cego sem custo estimado e um buraco nesta "
                "recomendacao.", ""]
    L += ["### O que um parser de Rust NAO compra", "",
          f"{len(esc['nunca_precisariam'])} dos {total} checks nao tem vetor em "
          "linguagem de servidor nenhuma:", "",
          " ".join(f"`{c}`" for c in esc["nunca_precisariam"]), "",
          "Sao os de `runtime` (observam a aplicacao no ar, nao leem fonte), os "
          "de", "`declaracao` (catalogo, manifesto, contrato) e os de `web` "
          "(P-13, P-14, S-09,", "cujo vetor nao existe fora do navegador). "
          "Nenhum parser move um milimetro", "nesses — e sabe-lo e o que "
          "impede de vender um parser como se ele resolvesse", "a cobertura "
          "inteira.", ""]

    obs = (laudo.get("relatorios") or {}).get("observacao_de_rede") or {}
    if obs:
        nao_varridos = ((laudo.get("relatorios") or {})
                        .get("recursos_nao_varridos") or {}).get("recursos") or []
        L += ["## A camada dinamica", "",
              "Cobertura estatica e cobertura dinamica nao se substituem, e o "
              "btv mostra por", "que: os checks de `runtime` foram os UNICOS "
              "que a cegueira de Rust nao", "tocou. O navegador ve a "
              "aplicacao, nao o codigo-fonte — e por isso essa metade",
              "da suite e a que um alvo poliglota nunca perde.", "",
              "| | |", "|---|---|",
              f"| URL observada | `{obs.get('url')}` |",
              f"| Engine | {obs.get('engine')} |",
              f"| Requisicoes | {obs.get('total_requisicoes')} |",
              f"| Hosts contactados | "
              f"{', '.join(f'`{h}`' for h in obs.get('hosts_contactados') or []) or '—'} |",
              f"| Cookies | "
              f"{', '.join(obs.get('cookies') or []) or 'nenhum'} |", ""]
        if len(obs.get("hosts_contactados") or []) > 1:
            L += ["O front do btv contacta `fonts.googleapis.com` no "
                  "carregamento — um terceiro que", "recebe o IP de todo "
                  "visitante. S-18 o denunciaria; ele foi PULADO porque nao ha "
                  "manifesto", "de terceiros no alvo para comparar, e S-04 ja "
                  "cobra a ausencia do manifesto.", "E um exemplo exato de por "
                  "que `pulado` nao pode virar `auditado` no mapa.", ""]
        if nao_varridos:
            L += ["**Nem tudo que foi servido foi lido.** Recursos acima do "
                  "teto de corpo ficaram", "fora da varredura de segredo, e a "
                  "suite diz quais:", ""]
            for r in nao_varridos:
                L.append(f"  * `{r}`")
            L += ["", "Ausencia de achado NESSES recursos nao e ausencia de "
                  "segredo. E a mesma regra", "do bloco `alcance`, aplicada "
                  "dentro da camada dinamica.", ""]

    L += ["## O laudo que originou este mapa", "",
          f"Veredito **{laudo['veredito']}**, exit `{laudo['exit_code']}`. "
          "Achados:", ""]
    if laudo["findings"]:
        L += ["| Check | Severidade | Titulo |", "|---|---|---|"]
        for f in laudo["findings"]:
            L.append(f"| `{f['check_id']}` | {f['severidade']} | {f['titulo']} |")
    else:
        L.append("Nenhum.")
    L += ["", "O laudo NAO foi tocado para produzir este documento. Ele "
          "continua indeterminado,", "com os mesmos achados e o mesmo exit "
          "code — cobertura de fachada comeca", "exatamente quando o mapa "
          "melhora o laudo que o originou.", ""]
    return "\n".join(L) + "\n"


def _main(argv) -> int:
    import json
    from pathlib import Path
    if len(argv) != 2:
        print("uso: python -m pse.cobertura <medicao.json>")
        return 30
    dados = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    print(gerar(dados["medicao"], dados["alvo"]), end="")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv))
