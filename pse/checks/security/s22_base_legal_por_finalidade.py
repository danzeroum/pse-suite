"""S-22 — a finalidade chega, e nada a amarra a uma base legal.

O UNICO CHECK QUE SOBREVIVEU a avaliacao de seis materiais de security. Os
outros vetores ja tinham dono: BOLA e S-01, minimizacao e P-05, hash como
anonimizacao e P-20, DPA de terceiro e S-04, dado de treino e P-15. Seis
materiais renderem um check e resultado, nao falha — e o sinal de que a
regua generalizou alem dos exemplos que a produziram.

O QUE S-07 JA FAZ, E ONDE ELE PARA. S-07 exige que a finalidade seja
propagada (`X-Purpose`) e registrada no log de auditoria. Ele responde "o
sistema sabe PARA QUE o dado foi lido?". E uma pergunta de rastreabilidade
— Art. 37 — e ele a responde inteira.

A pergunta seguinte e de LEGALIDADE, e ninguem a fazia: **aquela finalidade
podia rodar sob aquela base legal?** Um sistema pode propagar
`X-Purpose: marketing`, registrar isso lindamente no log, e processar sob
legitimo interesse — e o log passa a ser a prova documental da propria
infracao. Art. 6o I: a finalidade e limitada, e a base legal e o que a
limita. S-07 verifica que a etiqueta existe; S-22 verifica que a etiqueta
tem consequencia.

Um sistema passa S-07 e falha S-22. E o caso mais comum, e e por isso que
sao dois IDs e nao um.

O QUE E O FATO, EM DUAS PARTES (D-01):

  1. O MAPA finalidade -> base legal existe. Duas formas valem, e as duas
     sao estrutura, nunca mencao:
       * no codigo, um dicionario LITERAL cujos valores sao bases legais do
         vocabulario da lei (`pse/data/legal-basis.yaml`);
       * na declaracao, uma lista de finalidades em que cada entrada carrega
         a sua base — a forma que `consent-model.yaml` ja usa.
     `# TODO: legal basis check` nao e mapa. Comentario nao chega a arvore
     sintatica, e por isso nao desliga nem liga nada.

  2. A COMBINACAO INVALIDA E RECUSADA. Uma funcao que CONSULTA o mapa e,
     no mesmo corpo, RECUSA — levanta excecao, chama `abort`, devolve 403.
     Sem esta metade o mapa e decorativo: uma tabela que ninguem consulta e
     papel, e papel nao e enforcement. Este e o segundo achado, e ele e o
     mais interessante dos dois, porque o alvo que o recebe ja fez o
     trabalho dificil de escrever o mapa.

QUANDO O CHECK PULA. A aplicabilidade e UMA coisa so: existe ponto no codigo
que LE a finalidade da requisicao. Sem lugar onde ela chegue nao ha lugar
onde a base possa ser exigida, e o desfecho e `SkipCheck` nomeando S-07 — a
mesma disciplina de S-08 -> S-04 e P-18 -> P-04.

Declarar `purposes:` num modelo de consentimento NAO torna o check aplicavel,
e essa fronteira custou uma correcao: a primeira versao tratava a declaracao
como superficie, e passou a acusar repositorios de dados que declaram
finalidades e nao tem servidor nenhum. Declaracao e uma das formas do MAPA,
nunca o gatilho — finalidade declarada e nao lida e defeito de propagacao,
que e de S-07.

QUANDO O CHECK INDETERMINA. Ha finalidade entrando, ha um identificador com
nome de mapa de base legal, e o que ele guarda NAO e literal decidivel (vem
de uma chamada, de um config carregado, de outro modulo). A suite nao
consegue dizer se as bases estao amarradas — e o pior desfecho possivel
seria adivinhar. Precisao sobre recall.

D-08. O alvo que tem o mapa E recusa a combinacao invalida nao recebe nada.
Punir quem escreveu a tabela e a checagem seria ensinar o time a nao
escrever nenhuma das duas.

SEVERIDADE ALTO, e a escolha segue o criterio ratificado em S-14/S-15: e
falha de limitacao de finalidade, grave, e ainda nao e exposicao consumada.
`CRITICO` fica reservado ao que ja vazou.

METADE RUNTIME, OPCIONAL. Quando o operador declara em
`target.endpoints.finalidade_incompativel` uma rota e uma finalidade que
DEVEM ser recusadas, a sonda confirma a recusa no ar. Sem a declaracao a
suite nao sai inventando qual combinacao testar, e a metade nao executada
entra em `relatorios.cobertura_parcial` — meia execucao silenciosa e
meia-verdade no laudo.
"""
import ast

import yaml

from pse.engine import scan, yamlloc
from pse.engine.registry import check
from pse.model import (CheckIndeterminado, Finding, NaoHabilitado, Severidade,
                       SkipCheck)
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo

BASE = "LGPD Art. 6o I (finalidade) + Art. 7o (base legal)"
REGUA = "legal-basis"
REJEICAO_RUNTIME = (400, 401, 403, 422, 428, 451)


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _norm(texto) -> str:
    """`X-Purpose`, `x_purpose` e `HTTP_X_PURPOSE` sao o mesmo fato."""
    s = str(texto).strip().lower().replace("-", "_").replace(" ", "_")
    return s[5:] if s.startswith("http_") else s


def _bases(ctx) -> tuple:
    return tuple(sorted({_norm(b) for b in _r(ctx, "bases")}))


def _e_base(valor, bases) -> bool:
    """Valor literal que a lei reconhece como base legal.

    Radical curto de proposito: `consent` alcanca `consentimento_expresso`
    sem que a regua precise prever cada variante. O que NAO alcanca e o que
    importa — `interesse_do_negocio` e `melhoria_do_produto` nao comecam com
    base nenhuma, e sao exatamente as finalidades disfarcadas de base que o
    check existe para achar.
    """
    if not isinstance(valor, str):
        return False
    v = _norm(valor)
    return any(v == b or v.startswith(b) for b in bases)


# ---------------------------------------------------------------------------
# 1. A finalidade chega ao servidor? Sem isto o check nao se aplica.
# ---------------------------------------------------------------------------

def _extratores(ctx) -> set:
    de_query = {t.lower() for t in ctx.data["api-contract"]["extratores_de_query"]}
    sup = _r(ctx, "superficie")
    return de_query | {t.lower() for t in sup["extratores_de_cabecalho"]}


def _chaves_de_finalidade(ctx) -> set:
    sup = _r(ctx, "superficie")
    return {_norm(k) for k in list(sup["cabecalhos"]) + list(sup["chaves"])}


def _nome_do_extrator(no) -> str:
    """De `request.headers.get(...)`, o extrator e `headers`, nao `get`."""
    if isinstance(no, ast.Attribute):
        return no.attr.lower()
    if isinstance(no, ast.Name):
        return no.id.lower()
    return ""


def _leituras_de_finalidade(arvore, extratores: set, chaves: set):
    """(chave, linha) para toda LEITURA de finalidade vinda da requisicao.

    Enviar um cabecalho nao conta — quem envia e cliente. O que torna S-22
    aplicavel e o servidor LENDO a finalidade de quem chamou.
    """
    for no in ast.walk(arvore):
        if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
            if no.func.attr.lower() in ("get", "getlist"):
                if _nome_do_extrator(no.func.value) in extratores:
                    for a in no.args:
                        if isinstance(a, ast.Constant) and _norm(a.value) in chaves:
                            yield _norm(a.value), no.lineno
        if isinstance(no, ast.Subscript) and isinstance(no.slice, ast.Constant):
            if _nome_do_extrator(no.value) in extratores:
                if _norm(no.slice.value) in chaves:
                    yield _norm(no.slice.value), no.lineno


def _declaracoes(ctx):
    """(caminho, texto, doc) para todo YAML/JSON que a suite consegue ler."""
    for p in scan.arquivos(ctx.repo, {".yaml", ".yml", ".json"}):
        texto = scan.ler(p)
        try:
            doc = yaml.safe_load(texto)
        except yaml.YAMLError:
            continue                     # P-07/S-12 respondem por ilegivel
        if isinstance(doc, dict):
            yield p, texto, doc


# ---------------------------------------------------------------------------
# 2. O mapa finalidade -> base legal existe?
# ---------------------------------------------------------------------------

def _dict_amarra_base(no: ast.Dict, chaves_de_base: set, bases) -> bool:
    """Um dicionario literal cujos valores sao bases legais.

    Duas formas: `{"marketing": "consentimento"}` e a direta;
    `{"marketing": {"base_legal": "consentimento"}}` e a aninhada, que
    aparece quando a finalidade carrega mais coisas que a base.
    """
    for chave, valor in zip(no.keys, no.values):
        if not (isinstance(chave, ast.Constant) and isinstance(chave.value, str)):
            continue
        if isinstance(valor, ast.Constant) and _e_base(valor.value, bases):
            return True
        if isinstance(valor, ast.Dict):
            for k2, v2 in zip(valor.keys, valor.values):
                if not (isinstance(k2, ast.Constant) and isinstance(v2, ast.Constant)):
                    continue
                if (_norm(k2.value) in chaves_de_base
                        and _e_base(v2.value, bases)):
                    return True
    return False


def _mapas_em_codigo(ctx, arvores, bases):
    """(rel, linha, nome) para todo mapa literal finalidade -> base legal."""
    chaves_de_base = {_norm(k) for k in _r(ctx, "declaracao")["chave_de_base"]}
    saida = []
    for rel, arvore in arvores:
        for no in ast.walk(arvore):
            alvo, valor = None, None
            if isinstance(no, ast.Assign) and len(no.targets) == 1:
                alvo, valor = no.targets[0], no.value
            elif isinstance(no, ast.AnnAssign) and no.value is not None:
                alvo, valor = no.target, no.value
            if not isinstance(alvo, ast.Name) or not isinstance(valor, ast.Dict):
                continue
            if _dict_amarra_base(valor, chaves_de_base, bases):
                saida.append((rel, no.lineno, alvo.id))
    return saida


def _mapa_declarado(ctx, bases):
    """(rel, linha, quantas) para lista de finalidades com base por entrada."""
    dec = _r(ctx, "declaracao")
    containers = [c.lower() for c in dec["containers"]]
    chaves_de_base = {_norm(k) for k in dec["chave_de_base"]}
    saida = []
    for p, texto, doc in _declaracoes(ctx):
        for chave, valor in doc.items():
            if str(chave).lower() not in containers or not isinstance(valor, list):
                continue
            amarradas = [e for e in valor if isinstance(e, dict) and any(
                _norm(k) in chaves_de_base and _e_base(v, bases)
                for k, v in e.items())]
            if amarradas:
                saida.append((scan.rel(ctx.repo, p),
                              yamlloc.localizar(texto, [chave]) or 1,
                              len(amarradas)))
    return saida


def _sinais_ambiguos(ctx, arvores, nomes_decididos: set):
    """(rel, linha, nome) para identificador com NOME de mapa e sem estrutura.

    E o gatilho da indeterminacao. `BASES_LEGAIS = carregar_config()` tem
    tudo de mapa menos o que a suite precisa para decidir — e chutar aqui
    seria trocar fail-closed por adivinhacao.
    """
    marcas = _r(ctx, "nomes_de_mapa")
    saida = []
    for rel, arvore in arvores:
        for no in ast.walk(arvore):
            alvo, valor = None, None
            if isinstance(no, ast.Assign) and len(no.targets) == 1:
                alvo, valor = no.targets[0], no.value
            elif isinstance(no, ast.AnnAssign) and no.value is not None:
                alvo, valor = no.target, no.value
            if not isinstance(alvo, ast.Name):
                continue
            if alvo.id in nomes_decididos:
                continue
            if isinstance(valor, (ast.Dict, ast.Constant)):
                continue                 # literal: decidido acima, de um jeito
                                         # ou de outro
            if scan.nome_casa_tokens(alvo.id.lower(), marcas):
                saida.append((rel, no.lineno, alvo.id))
    return saida


# ---------------------------------------------------------------------------
# 3. A combinacao invalida e recusada?
# ---------------------------------------------------------------------------

def _consulta_o_mapa(corpo, nomes: set, marcas) -> bool:
    for sub in ast.walk(corpo):
        if isinstance(sub, ast.Name) and sub.id in nomes:
            return True
        alvo = None
        if isinstance(sub, ast.Subscript):
            alvo = sub.value
        elif isinstance(sub, ast.Call) and isinstance(sub.func, ast.Attribute):
            if sub.func.attr.lower() in ("get", "keys", "items"):
                alvo = sub.func.value
        nome = getattr(alvo, "id", None) or getattr(alvo, "attr", None)
        if nome and scan.nome_casa_tokens(str(nome).lower(), marcas):
            return True
    return False


def _recusa(ctx, corpo) -> bool:
    rej = _r(ctx, "rejeicao")
    chamadas = [c.lower() for c in rej["chamadas"]]
    excecoes = {e.lower() for e in rej["excecoes"]}
    status = set(rej["status"])
    for sub in ast.walk(corpo):
        # Levantar excecao dentro de quem consulta o mapa JA e recusa: o
        # fluxo nao segue para o acesso ao dado. `excecoes` da regua nao
        # restringe isto — ela existe para o caso em que a excecao e
        # levantada por uma chamada, e serve de evidencia mais forte.
        if isinstance(sub, ast.Raise):
            return True
        if isinstance(sub, ast.Call):
            nome = scan.nome_chamado(sub).split(".")[-1].lower()
            if nome in excecoes or nome in chamadas:
                return True
            for a in list(sub.args) + [k.value for k in sub.keywords]:
                if isinstance(a, ast.Constant) and a.value in status:
                    return True
        if isinstance(sub, ast.Return):
            for filho in ast.walk(sub):
                if isinstance(filho, ast.Constant) and filho.value in status:
                    return True
    return False


def _enforcement(ctx, arvores, nomes: set):
    """(rel, linha, funcao) para toda funcao que consulta o mapa E recusa."""
    marcas = _r(ctx, "nomes_de_mapa")
    saida = []
    for rel, arvore in arvores:
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if _consulta_o_mapa(no, nomes, marcas) and _recusa(ctx, no):
                saida.append((rel, no.lineno, no.name))
    return saida


# ---------------------------------------------------------------------------
# A metade runtime, opcional e declarada.
# ---------------------------------------------------------------------------

def _runtime(ctx, findings):
    endpoints = autorizacao.alvo_de(ctx.config).get("endpoints") or {}
    if not endpoints.get("finalidade_incompativel"):
        raise NaoHabilitado(
            "target.endpoints.finalidade_incompativel nao declarado — a suite "
            "nao inventa qual combinacao finalidade/base testar no alvo")
    cliente, _ = exigir_alvo(ctx, "active")
    rota = autorizacao.endpoint(ctx.config, "finalidade_incompativel")
    token = autorizacao.token(ctx.config, "titular_a")
    finalidade = (autorizacao.alvo_de(ctx.config).get("purposes") or {}).get(
        "incompativel", "marketing")

    resposta, trace = cliente.requisitar(
        "GET", rota, token=token, identidade="titular_a",
        extra_headers={"X-Purpose": finalidade})
    if resposta.status in REJEICAO_RUNTIME or resposta.status >= 500:
        return
    findings.append(Finding(
        check_id="S-22", pack="security", severidade=Severidade.ALTO,
        titulo="Combinacao finalidade/base declarada incompativel foi atendida",
        descricao=(
            f"GET em {rota} com `X-Purpose: {finalidade}` respondeu "
            f"{resposta.status}. O operador declarou esta combinacao como a "
            f"que deve ser recusada, e o alvo a atendeu: a amarracao existe "
            f"no codigo e nao vale na borda."),
        recomendacao="Aplicar a checagem de base legal no mesmo ponto em que "
                     "a finalidade e lida, antes de qualquer acesso a dado.",
        base_legal=BASE, arquivo=rota, linha=1, trace=trace))


# ---------------------------------------------------------------------------

@check("S-22", "security", "Base legal nao amarrada a finalidade", base_legal=BASE)
def base_legal_por_finalidade(ctx):
    bases = _bases(ctx)
    extratores = _extratores(ctx)
    chaves = _chaves_de_finalidade(ctx)

    arvores = [(scan.rel(ctx.repo, p), scan.arvore(p))
               for p in scan.arquivos(ctx.repo, {".py"})]

    leituras = [(rel, chave, linha) for rel, arvore in arvores
                for chave, linha in _leituras_de_finalidade(
                    arvore, extratores, chaves)]
    if not leituras:
        raise SkipCheck(
            "nenhuma finalidade entra no servidor: nenhum ponto do codigo le "
            "`X-Purpose` nem chave equivalente da requisicao. Sem lugar onde a "
            "finalidade chegue nao ha lugar onde a base legal possa ser "
            "exigida — e declarar finalidades sem le-las e defeito de "
            "propagacao, que e de S-07")

    em_codigo = _mapas_em_codigo(ctx, arvores, bases)
    declarado = _mapa_declarado(ctx, bases)
    nomes = {n for _, _, n in em_codigo}

    ambiguos = _sinais_ambiguos(ctx, arvores, nomes)
    if ambiguos and not em_codigo and not declarado:
        rel, linha, nome = ambiguos[0]
        raise CheckIndeterminado(
            f"`{nome}` em {rel}:{linha} tem nome de mapa de base legal e nao "
            f"guarda estrutura literal — a suite nao consegue dizer se as "
            f"finalidades estao amarradas a bases do Art. 7o. Declarar o mapa "
            f"como literal, ou em {', '.join(_r(ctx, 'declaracao')['containers'][:2])} "
            f"no modelo de consentimento, torna a resposta decidivel")

    findings = []
    if not em_codigo and not declarado:
        arquivo, chave, linha = leituras[0]
        como = f"a finalidade e lida de `{chave}`"
        findings.append(Finding(
            check_id="S-22", pack="security", severidade=Severidade.ALTO,
            titulo="Finalidade sem base legal amarrada",
            descricao=(
                f"{como}, e nenhum mapa liga finalidade a base legal. O "
                f"sistema sabe PARA QUE o dado foi lido e nao sabe SOB QUE "
                f"AMPARO — qualquer finalidade roda sob qualquer base, e o "
                f"log de finalidade vira a prova documental da propria "
                f"infracao. Art. 6o I: a finalidade e limitada, e a base "
                f"legal e o que a limita. Isto e o passo seguinte a S-07, "
                f"nao o mesmo defeito: um sistema pode propagar e registrar "
                f"a finalidade impecavelmente e ainda assim processar "
                f"marketing sob legitimo interesse."),
            recomendacao=(
                "Declarar o mapa finalidade -> base legal (dicionario literal "
                "no codigo ou `purposes:` com `base_legal:` no modelo de "
                "consentimento) e recusar 403 quando a combinacao nao "
                "constar dele, no mesmo ponto em que a finalidade e lida."),
            base_legal=BASE, arquivo=arquivo, linha=linha))
    else:
        aplicado = _enforcement(ctx, arvores, nomes)
        if not aplicado:
            rel, linha, quem = (em_codigo[0] if em_codigo else
                                (declarado[0][0], declarado[0][1], "declaracao"))
            findings.append(Finding(
                check_id="S-22", pack="security", severidade=Severidade.ALTO,
                titulo="Mapa de base legal existe e nao e aplicado",
                descricao=(
                    f"O mapa finalidade -> base legal esta em {rel}:{linha}, e "
                    f"nenhuma funcao o consulta para RECUSAR a combinacao "
                    f"invalida. Uma tabela que ninguem consulta e papel, e "
                    f"papel nao e enforcement: a finalidade continua podendo "
                    f"rodar sob qualquer base, com a agravante de que a "
                    f"declaracao correta existe e sera lida como se valesse."),
                recomendacao=(
                    "Consultar o mapa no ponto em que a finalidade e lida e "
                    "recusar (403) quando a base declarada para aquela "
                    "finalidade nao for a base sob a qual a operacao roda."),
                base_legal=BASE, arquivo=rel, linha=linha))

    try:
        _runtime(ctx, findings)
    except NaoHabilitado as e:
        ctx.relatorio("cobertura_parcial", {
            **ctx.relatorios.get("cobertura_parcial", {}),
            "S-22": f"metade runtime nao executada: {e}"})
    return findings
