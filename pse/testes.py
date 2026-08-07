"""Documentacao de testes — GERADA do codigo, nunca redigida a mao.

    python -m pse.testes           > docs/TESTES.md
    python -m pse.testes --indice  > docs/INDICE-DE-TESTES.md

POR QUE GERADA. Uma doc de 57 checks e 559 funcoes de teste redigida a mao
envelhece em uma versao e passa a mentir: alguem acrescenta P-25, esquece de
atualizar o texto, e o documento passa a afirmar 57 quando ha 58. E o mesmo
defeito que `docs/RATIFICACOES.md` existe para evitar — uma decisao que
ninguem encontra nao foi tomada — e o mesmo que a suite cobra dos alvos:
laudo silencioso sobre o que nao foi olhado e indistinguivel de laudo que
olhou e nao achou nada.

POR QUE TRAVADA. Gerar nao basta. Um gerador que ninguem e obrigado a rodar
produz doc velha do mesmo jeito — a diferenca e so de quem e a culpa. Por
isso `tests/test_indice.py` REGENERA os dois documentos em memoria e COMPARA
com o que esta commitado: divergiu, o merge nao abre. A doutrina da suite
aplicada a si mesma — uma trava que o vigiado pode desligar nao e trava.

DETERMINISMO E PRE-REQUISITO DA TRAVA, nao detalhe de implementacao. Gerador
que produz bytes diferentes a cada execucao faz a comparacao falhar por
ruido; o time aprende a ignorar o vermelho, e a trava morre de fadiga —
exatamente como falso-positivo em CRITICO ensina a ignorar o laudo. Entao:
toda iteracao e ordenada, nenhum `set` chega ao texto sem `sorted`, e nada
volatil entra no corpo comparado. O que for volatil (versao do pacote, data
de geracao) vive DEPOIS de `MARCA_FIM_DO_CORPO`, que a comparacao corta.

O QUE ELE LE, e por que nao ha terceira fonte:

  * `pse/data/checks-catalog.yaml` — a declaracao autoritativa dos checks;
  * o registro (`pse.engine.registry.CHECKS`) — o que de fato existe em
    codigo, e em que modulo;
  * a arvore sintatica de `pse/checks/**` — severidades emitidas, reguas
    consumidas, desfechos possiveis;
  * a arvore sintatica de `tests/**` — funcoes, casos, marcadores e quais
    checks cada arquivo exercita.

Nenhum numero deste documento e digitado. Se um deles estiver errado, o erro
esta no codigo, e e la que se corrige.
"""
import ast
import re
from pathlib import Path

from pse import catalogo, cobertura
from pse.alcance import ALCANCE_PARCIAL, SEM_PARSER

PACOTE = Path(__file__).resolve().parent
RAIZ = PACOTE.parent
DIR_TESTES = RAIZ / "tests"
DIR_DATA = PACOTE / "data"
DIR_DOCS = RAIZ / "docs"

DOC_TESTES = DIR_DOCS / "TESTES.md"
DOC_INDICE = DIR_DOCS / "INDICE-DE-TESTES.md"

# Tudo que vem depois desta marca fica FORA da comparacao da trava. E onde
# mora o que e volatil de proposito: versao do pacote, data de geracao. Sem
# esta separacao, um bump de versao reprovaria o merge por ruido, e a trava
# ensinaria o time a ignora-la.
MARCA_FIM_DO_CORPO = "<!-- fim-do-corpo-comparado -->"

COMO_REGENERAR = (
    "python -m pse.testes > docs/TESTES.md\n"
    "python -m pse.testes --indice > docs/INDICE-DE-TESTES.md")

# Um ID de check tem prefixo de PILAR e dois digitos. Serve para achar
# referencia a check dentro de um teste — e para achar referencia a check
# que NAO EXISTE, que e o defeito simetrico do check orfao.
RX_ID = re.compile(r"^([A-Z]{1,2})-(\d{2})$")

# Um modulo de teste que precisa citar um ID fora do catalogo (para provar
# que o registro o rejeita, ou para nomear um buraco deliberado) DECLARA a
# excecao neste nome, com motivo. Declarada, ela aparece no indice; calada,
# ela reprova. E o padrao D-13: a excecao e visivel, nao silenciosa.
DECLARACAO_DE_EXCECAO = "CHECKS_FORA_DO_CATALOGO"

EXCECOES = ("SkipCheck", "CheckIndeterminado", "NaoHabilitado")

# As portas por onde um teste EXERCITA um check. Citar o ID nao basta: uma
# asercao de que `S-22` consta do catalogo e uma verificacao sobre a
# DECLARACAO, nao sobre o comportamento — e contar isso como cobertura faria
# a trava de orfao aceitar um check que ninguem jamais rodou.
#
# Foi assim que a trava quase deixou passar: removidos os testes de S-22,
# duas asercoes de pertencimento sobreviveram e o check continuou "coberto".
# Um teste conta quando a funcao que cita o ID ALCANCA uma destas portas —
# diretamente, ou por um auxiliar de modulo (`rodar`, `escrever`) que as
# alcance. E o mesmo D-01 mais uma volta: nao basta o ID aparecer no codigo,
# ele tem de aparecer em codigo que executa o check.
MOTORES = ("executar", "main", "provar", "provar_todas")


class ArvoreAusente(Exception):
    """Gerador rodando fora do repositorio — sem `tests/`, nao ha o que gerar.

    Fail-closed: produzir um documento dizendo "0 testes" seria pior que nao
    produzir nenhum, porque teria a forma de uma resposta.
    """


# ---------------------------------------------------------------------------
# Leitura do codigo — nada aqui adivinha; tudo sai da arvore sintatica.
# ---------------------------------------------------------------------------

def _constantes_de_modulo(arvore) -> dict:
    """`NOME = "literal"` no topo do modulo, para resolver `ctx.data[REGUA]`."""
    saida = {}
    for no in arvore.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1:
            alvo = no.targets[0]
            if isinstance(alvo, ast.Name):
                saida[alvo.id] = no.value
    return saida


def _texto(no):
    return no.value if isinstance(no, ast.Constant) and isinstance(no.value, str) else None


def _registro() -> dict:
    from pse.engine.registry import CHECKS
    from pse.engine.runner import _carregar_checks
    _carregar_checks()
    return CHECKS


def marcadores_declarados() -> dict:
    """`marker: descricao` de `pyproject.toml` — a fonte unica dos eixos.

    Marcador em uso e nao declarado ali ja reprova o proprio pytest; o que
    este documento acrescenta e a separacao entre os eixos que a suite
    inventou e os embutidos (`parametrize`, `skipif`), que nao dividem nada.
    """
    texto = (RAIZ / "pyproject.toml").read_text(encoding="utf-8")
    dentro, saida = False, {}
    for linha in texto.splitlines():
        crua = linha.strip()
        if crua.startswith("markers"):
            dentro = True
            continue
        if dentro and crua.startswith("]"):
            break
        if dentro and crua.startswith('"'):
            corpo = crua.strip('",')
            nome, _, desc = corpo.partition(":")
            saida[nome.strip()] = desc.strip()
    return saida


def reguas_declaradas() -> list:
    """Nomes das reguas de `pse/data/` — o vocabulario que um check pode citar."""
    return sorted(p.stem for p in DIR_DATA.glob("*.yaml"))


def analisar_modulo_de_check(caminho: Path) -> dict:
    """Severidades emitidas, reguas consumidas e desfechos possiveis.

    Ancorado no FATO (D-01): severidade vem de `Severidade.X` como atributo,
    regua vem do subscrito `ctx.data[...]`, desfecho vem do nome da excecao
    usado em codigo. Mencao em comentario nao entra — comentario nao chega a
    arvore sintatica.
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    consts = _constantes_de_modulo(arvore)
    conhecidas = set(reguas_declaradas())

    severidades, reguas, desfechos = set(), set(), set()
    severidade_dinamica = False

    for no in ast.walk(arvore):
        if isinstance(no, ast.Attribute) and isinstance(no.value, ast.Name):
            if no.value.id == "Severidade":
                severidades.add(no.attr)
        if isinstance(no, ast.Subscript):
            base = no.value
            if isinstance(base, ast.Name) and base.id == "Severidade":
                severidade_dinamica = True
            if isinstance(base, ast.Attribute) and base.attr == "data":
                chave = _texto(no.slice)
                if chave is None and isinstance(no.slice, ast.Name):
                    chave = _texto(consts.get(no.slice.id))
                if chave in conhecidas:
                    reguas.add(chave)
        if isinstance(no, ast.Name) and no.id in EXCECOES:
            desfechos.add(no.id)

    doc = (ast.get_docstring(arvore) or "").strip()
    primeira = doc.split("\n")[0].strip() if doc else ""
    return {
        "descricao": primeira,
        "severidades": sorted(severidades),
        "severidade_dinamica": severidade_dinamica,
        "reguas": sorted(reguas),
        "desfechos": sorted(desfechos),
    }


def _marcadores(arvore) -> set:
    """`@pytest.mark.X` em funcao e `pytestmark = ...` no modulo."""
    marcas = set()

    def da_expressao(no):
        alvo = no.func if isinstance(no, ast.Call) else no
        if isinstance(alvo, ast.Attribute) and isinstance(alvo.value, ast.Attribute):
            if alvo.value.attr == "mark":
                marcas.add(alvo.attr)

    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            for d in no.decorator_list:
                da_expressao(d)
        if isinstance(no, ast.Assign) and len(no.targets) == 1:
            alvo = no.targets[0]
            if isinstance(alvo, ast.Name) and alvo.id == "pytestmark":
                valores = (no.value.elts if isinstance(no.value, (ast.List, ast.Tuple))
                           else [no.value])
                for v in valores:
                    da_expressao(v)
    return marcas


def _casos_da_funcao(no, consts) -> tuple:
    """Quantos casos a funcao vira apos `parametrize`, quando isso e legivel.

    Argvalues computado em tempo de execucao NAO e chutado: a funcao volta
    contando 1 — o PISO, que e o que a arvore garante — e e NOMEADA no
    documento como nao-contavel. Inventar o numero real aqui seria a
    cobertura de fachada em miniatura; contar zero seria mentir para o outro
    lado, dizendo que a funcao nao roda.
    """
    casos = 1
    for d in no.decorator_list:
        if not isinstance(d, ast.Call):
            continue
        if "parametrize" not in ast.unparse(d.func):
            continue
        valores = d.args[1] if len(d.args) > 1 else None
        if isinstance(valores, ast.Name):
            valores = consts.get(valores.id)
        if isinstance(valores, (ast.List, ast.Tuple)):
            casos *= len(valores.elts)
        else:
            return 1, True
    return casos, False


def analisar_arquivo_de_teste(caminho: Path) -> dict:
    texto = caminho.read_text(encoding="utf-8")
    arvore = ast.parse(texto)
    consts = _constantes_de_modulo(arvore)

    funcoes, casos, nao_resolviveis = [], 0, []
    for no in ast.walk(arvore):
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) and no.name.startswith("test_"):
            funcoes.append(no.name)
            n, opaco = _casos_da_funcao(no, consts)
            if opaco:
                nao_resolviveis.append(no.name)
            casos += n

    # Funcoes de modulo que alcancam o motor, direta ou indiretamente.
    chamadas_de = {}
    for no in arvore.body:
        if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chamadas_de[no.name] = {
                ast.unparse(x.func).split(".")[-1]
                for x in ast.walk(no) if isinstance(x, ast.Call)}

    def alcanca_o_motor(nome, vistos=None):
        vistos = vistos if vistos is not None else set()
        if nome in vistos:
            return False
        vistos.add(nome)
        for chamada in chamadas_de.get(nome, ()):
            if chamada in MOTORES:
                return True
            if chamada in chamadas_de and alcanca_o_motor(chamada, vistos):
                return True
        return False

    # `ids` e TODA citacao — e o que pega a referencia fantasma, esteja ela
    # onde estiver. `exercitados` e o subconjunto que vale como cobertura.
    ids, exercitados = set(), set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.Constant) and isinstance(no.value, str):
            if RX_ID.match(no.value):
                ids.add(no.value)
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not no.name.startswith("test_") or not alcanca_o_motor(no.name):
            continue
        for sub in ast.walk(no):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if RX_ID.match(sub.value):
                    exercitados.add(sub.value)

    modulos = set()
    for no in ast.walk(arvore):
        if isinstance(no, ast.ImportFrom) and (no.module or "").startswith("pse.checks."):
            modulos.add(no.module)
        if isinstance(no, ast.Import):
            for a in no.names:
                if a.name.startswith("pse.checks."):
                    modulos.add(a.name)

    excecoes = {}
    for no in arvore.body:
        if isinstance(no, ast.Assign) and len(no.targets) == 1:
            alvo = no.targets[0]
            if isinstance(alvo, ast.Name) and alvo.id == DECLARACAO_DE_EXCECAO:
                if isinstance(no.value, ast.Dict):
                    for k, v in zip(no.value.keys, no.value.values):
                        chave, motivo = _texto(k), _texto(v)
                        if chave:
                            excecoes[chave] = motivo or ""

    doc = (ast.get_docstring(arvore) or "").strip()
    return {
        "arquivo": caminho.name,
        "linhas": len(texto.splitlines()),
        "funcoes": sorted(funcoes),
        "casos": casos,
        "parametrizacoes_opacas": sorted(nao_resolviveis),
        "marcadores": sorted(_marcadores(arvore)),
        "ids_citados": sorted(ids),
        "ids_exercitados": sorted(exercitados),
        "modulos_de_check": sorted(modulos),
        "excecoes_declaradas": excecoes,
        "descricao": doc.split("\n")[0].strip() if doc else "",
    }


def arquivos_de_teste() -> list:
    if not DIR_TESTES.is_dir():
        raise ArvoreAusente(
            f"{DIR_TESTES} nao existe. O gerador de documentacao de testes le "
            f"a arvore sintatica de `tests/` e nao tem outra fonte: rode-o de "
            f"dentro do repositorio.")
    return [analisar_arquivo_de_teste(p) for p in sorted(DIR_TESTES.glob("*.py"))]


# ---------------------------------------------------------------------------
# Camada A — os checks
# ---------------------------------------------------------------------------

def checks() -> list:
    reg = _registro()
    saida = []
    for cid in sorted(catalogo.CATALOGO):
        meta = catalogo.meta(cid)
        entrada = reg.get(cid)
        modulo = entrada["fn"].__module__ if entrada else None
        caminho = RAIZ / (modulo.replace(".", "/") + ".py") if modulo else None
        analise = (analisar_modulo_de_check(caminho)
                   if caminho and caminho.is_file() else {})
        mut = meta.get("canonical_mutation") or {}
        familias, nota = cobertura.SUBSTRATO.get(cid, ([], ""))
        grau = cobertura.EXIGENCIA_DE_PARSER.get(cid)
        saida.append({
            "id": cid,
            "pack": meta.get("pack"),
            "dominios": catalogo.dominios(cid),
            "titulo": meta.get("titulo", ""),
            "base_legal": meta.get("base_legal", ""),
            "tipo": meta.get("tipo", ""),
            "modo": meta.get("modo", ""),
            "fase": meta.get("fase"),
            "status": meta.get("status", ""),
            "guarda_de_pack": bool(meta.get("guarda_de_pack")),
            "modulo": (modulo.replace(".", "/") + ".py") if modulo else None,
            "descricao": analise.get("descricao", ""),
            "severidades": analise.get("severidades", []),
            "severidade_dinamica": analise.get("severidade_dinamica", False),
            "reguas": analise.get("reguas", []),
            "desfechos": analise.get("desfechos", []),
            "mutacao": {"descricao": mut.get("descricao", ""),
                        "espera": mut.get("espera_severidade", "")} if mut else None,
            "substrato": sorted(familias),
            "substrato_nota": nota,
            "exigencia_de_parser": (grau[0] if grau else None),
        })
    return saida


def _sem_prefixo(descricao: str, cid: str) -> str:
    """`"S-06 — credencial hardcoded."` vira `"credencial hardcoded."`."""
    if not descricao:
        return ""
    d = descricao
    for sep in (" — ", " - ", " -- "):
        if d.startswith(cid + sep):
            d = d[len(cid) + len(sep):]
            break
    return d.strip()


def descricao_de(c: dict) -> str:
    """O que o check faz: docstring do modulo; sem ela, o titulo do catalogo."""
    return _sem_prefixo(c["descricao"], c["id"]) or c["titulo"]


# ---------------------------------------------------------------------------
# A ponte — cada check, os testes que o exercitam
# ---------------------------------------------------------------------------

def cobertura_de_checks(fichas=None) -> dict:
    """check -> arquivos de teste que o cobrem, e os dois defeitos simetricos.

    Coberto por IMPORTACAO (o teste importa o modulo do check) ou por ID —
    e, no segundo caso, so quando o ID aparece dentro de uma funcao de teste
    que ALCANCA o motor (`executar`, `main`, `provar`), direta ou por um
    auxiliar de modulo. Citar o ID numa asercao sobre o catalogo verifica a
    declaracao, nao o comportamento, e contar isso como cobertura faria a
    trava aceitar um check que ninguem jamais rodou. As duas evidencias sao
    registradas separadamente para que o indice diga COMO cada check e
    coberto, e nao apenas que e.

    Os dois defeitos:

      * ORFAO — check no catalogo que nenhum teste exercita. A doc listaria
        os checks e os testes sem nunca provar que os segundos cobrem os
        primeiros; e isso que faz do indice uma prova e nao uma lista.
      * FANTASMA — teste citando ID que nao existe no catalogo. Ou o check
        foi renomeado e o teste ficou para tras, ou o teste cita um ID
        deliberadamente inexistente e nao declarou isso.

    A prova de mutacao NAO conta como cobertura, e a exclusao e deliberada:
    ela parametriza sobre `catalogo.implementados()` e alcanca TODOS por
    construcao. Se contasse, nenhum check jamais seria orfao e a trava nao
    provaria nada. Ela prova que o inverso canonico fica vermelho; nao prova
    que o caso conforme fica quieto, nem que o skip nomeia o motivo.

    `fichas` existe para que os testes desta trava possam alimentar uma
    arvore sintetica sem escrever arquivo dentro de `tests/`.
    """
    fichas = arquivos_de_teste() if fichas is None else fichas
    por_check = {}
    modulo_do_check = {}
    for c in checks():
        por_check[c["id"]] = {"por_import": [], "por_id": []}
        if c["modulo"]:
            modulo_do_check[c["modulo"][:-3].replace("/", ".")] = c["id"]

    fantasmas, declaradas = [], []
    for f in fichas:
        for mod in f["modulos_de_check"]:
            cid = modulo_do_check.get(mod)
            if cid:
                por_check[cid]["por_import"].append(f["arquivo"])
        for cid in f["ids_exercitados"]:
            if cid in por_check:
                por_check[cid]["por_id"].append(f["arquivo"])
        for cid in f["ids_citados"]:
            if cid in por_check:
                continue
            if not catalogo.PILAR_DO_PREFIXO.get(cid.split("-")[0]):
                continue          # `FE-01` e prefixo de dominio: outro teste cuida
            motivo = f["excecoes_declaradas"].get(cid)
            if motivo is None:
                fantasmas.append({"arquivo": f["arquivo"], "id": cid})
            else:
                declaradas.append({"arquivo": f["arquivo"], "id": cid,
                                   "motivo": motivo})

    for v in por_check.values():
        v["por_import"] = sorted(set(v["por_import"]))
        v["por_id"] = sorted(set(v["por_id"]))
        v["arquivos"] = sorted(set(v["por_import"]) | set(v["por_id"]))

    orfaos = sorted(cid for cid, v in por_check.items() if not v["arquivos"])
    return {
        "por_check": por_check,
        "orfaos": orfaos,
        "fantasmas": sorted(fantasmas, key=lambda d: (d["arquivo"], d["id"])),
        "excecoes_declaradas": sorted(declaradas,
                                      key=lambda d: (d["arquivo"], d["id"])),
    }


# ---------------------------------------------------------------------------
# Secao C — o que NAO esta testado. Gerada, porque lacuna redigida vira
# propaganda: quem escreve escolhe o que confessar, e escolhe pouco.
# ---------------------------------------------------------------------------

def _ids_ausentes_na_numeracao() -> list:
    """Buracos deliberados na sequencia de IDs — P-12, P-21 e o que vier.

    Um ID que some da sequencia e uma decisao (o check foi investigado e
    concluiu-se que nao ha artefato verificavel), nao um esquecimento. Mas
    ele so e visivel para quem le a lista inteira procurando furo — por isso
    o documento o computa.
    """
    por_prefixo = {}
    for cid in catalogo.CATALOGO:
        pref, num = cid.split("-")
        por_prefixo.setdefault(pref, set()).add(int(num))
    saida = []
    for pref in sorted(por_prefixo):
        nums = por_prefixo[pref]
        for n in range(min(nums), max(nums)):
            if n not in nums:
                saida.append(f"{pref}-{n:02d}")
    return sorted(saida)


def _mecanismo_de_exclusao() -> dict:
    """A varredura sabe pular caminho? E o consumidor pode dizer qual?

    Sonda real, nao memoria: procura em `pse/` alguma leitura de configuracao
    cuja chave fale de excluir/ignorar caminho. Nao achando, o unico
    mecanismo e a lista fixa de `scan.IGNORAR_DIRS` — e o autoscan da suite
    contra si mesma continua contando as proprias fixtures como achado.
    """
    from pse.engine import scan
    chaves = set()
    for p in sorted(PACOTE.rglob("*.py")):
        try:
            arvore = ast.parse(p.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for no in ast.walk(arvore):
            if isinstance(no, ast.Subscript):
                base = no.value
                nome = getattr(base, "attr", None) or getattr(base, "id", None)
                if nome not in ("config", "cfg", "pse_suite"):
                    continue
                chave = _texto(no.slice)
                if chave and re.search(r"exclu|ignor", chave, re.I):
                    chaves.add(chave)
            if isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute):
                if no.func.attr == "get" and no.args:
                    nome = (getattr(no.func.value, "attr", None)
                            or getattr(no.func.value, "id", None))
                    chave = _texto(no.args[0])
                    if (nome in ("config", "cfg", "pse_suite") and chave
                            and re.search(r"exclu|ignor", chave, re.I)):
                        chaves.add(chave)
    return {"fixo": sorted(scan.IGNORAR_DIRS), "configuravel": sorted(chaves)}


def _pendencias_ratificadas() -> list:
    """As pendencias abertas, lidas de `docs/RATIFICACOES.md`.

    Lidas, nao recopiadas: se uma pendencia for ratificada e sair daquela
    tabela, ela sai deste documento no mesmo commit, sem ninguem lembrar.
    """
    arquivo = DIR_DOCS / "RATIFICACOES.md"
    if not arquivo.is_file():
        return []
    linhas = arquivo.read_text(encoding="utf-8").splitlines()
    dentro, saida = False, []
    for linha in linhas:
        if linha.startswith("## "):
            dentro = "segue pendente" in linha.lower()
            continue
        if not dentro or not linha.startswith("|"):
            continue
        celulas = [c.strip() for c in linha.strip("|").split("|")]
        if len(celulas) < 2 or celulas[0].lower().startswith("pend"):
            continue
        if set(celulas[0]) <= {"-", ":", " "}:
            continue
        saida.append({"pendencia": celulas[0], "nasceu_em": celulas[1]})
    return saida


def _buracos_assumidos() -> list:
    """Os vetores investigados e deliberadamente nao implementados.

    Lidos de `docs/BURACOS-ASSUMIDOS.md`, nao recopiados: fechado um buraco,
    ele some deste documento no mesmo commit em que sai daquela tabela. Uma
    lista de lacunas que precisa ser lembrada e uma lista que envelhece.
    """
    arquivo = DIR_DOCS / "BURACOS-ASSUMIDOS.md"
    if not arquivo.is_file():
        return []
    dentro, saida = False, []
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        if linha.startswith("## "):
            dentro = linha.strip().lower().endswith("os buracos")
            continue
        if not dentro or not linha.startswith("|"):
            continue
        celulas = [c.strip() for c in linha.strip("|").split("|")]
        if len(celulas) < 4 or not celulas[0].isdigit():
            continue
        saida.append({"vetor": celulas[1], "motivo": celulas[2],
                      "nasceu_em": celulas[3]})
    return saida


def lacunas() -> list:
    """O estado real do que a suite NAO cobre. Cada item sai de uma sonda."""
    cs = checks()
    cob = cobertura_de_checks()
    fichas = arquivos_de_teste()

    parciais = {rot: chks for _, (rot, _, chks) in ALCANCE_PARCIAL.items()}
    idiomas_parciais = set(parciais)
    sem_parser = sorted({v for v in SEM_PARSER.values()} - idiomas_parciais)

    exclusao = _mecanismo_de_exclusao()
    opacas = [(f["arquivo"], n) for f in fichas for n in f["parametrizacoes_opacas"]]
    sem_docstring = sorted(c["id"] for c in cs if c["modulo"] and not c["descricao"])
    sem_mutacao = sorted(c["id"] for c in cs
                         if c["status"] == catalogo.IMPLEMENTADO and not c["mutacao"])
    previstos = sorted(c["id"] for c in cs if c["status"] != catalogo.IMPLEMENTADO)

    itens = [
        {
            "titulo": "Nenhuma linguagem de servidor alem de Python tem parser",
            "aberta": bool(sem_parser),
            "detalhe": (
                "A suite nomeia mas nao le: " + ", ".join(sem_parser) + ". "
                + ("Alcance parcial declarado: "
                   + "; ".join(f"{k} (somente {', '.join(v)})"
                               for k, v in sorted(parciais.items())) + ". "
                   if parciais else "")
                + "Ausencia de achado nessas linguagens nao e atestado de "
                  "conformidade — e ausencia de leitura."),
        },
        {
            "titulo": "Nao ha mecanismo de exclusao de caminho declaravel",
            "aberta": not exclusao["configuravel"],
            "detalhe": (
                "O unico filtro e a lista fixa `scan.IGNORAR_DIRS` ("
                + ", ".join("`%s`" % d for d in exclusao["fixo"]) + "). "
                "O consumidor nao pode declarar caminho fora de escopo, e o "
                "autoscan da propria suite conta as fixtures de teste como "
                "achado. Fechar a lacuna exige que a exclusao seja DECLARADA "
                "e CONTADA no laudo — filtro silencioso seria a cobertura de "
                "fachada de volta pela porta dos fundos."
                if not exclusao["configuravel"] else
                "Chaves de configuracao reconhecidas: "
                + ", ".join("`%s`" % k for k in exclusao["configuravel"]) + "."),
        },
        {
            "titulo": "IDs deliberadamente ausentes da sequencia do catalogo",
            "aberta": bool(_ids_ausentes_na_numeracao()),
            "detalhe": (
                "Sem entrada no catalogo: "
                + ", ".join("`%s`" % i for i in _ids_ausentes_na_numeracao())
                + ". Buraco honesto e melhor que check que nao verifica nada "
                  "real — mas so quando o buraco esta escrito."),
        },
        {
            "titulo": "Vetores reais deliberadamente nao implementados",
            "aberta": bool(_buracos_assumidos()),
            "detalhe": (
                "Investigados e assinados em `docs/BURACOS-ASSUMIDOS.md` "
                "porque o check possivel verificaria a fachada, nao o "
                "direito: "
                + "; ".join(f"{b['vetor']} — {b['motivo']} (desde "
                            f"{b['nasceu_em']})"
                            for b in _buracos_assumidos())
                if _buracos_assumidos() else
                "Nenhum — todo vetor investigado virou check."),
        },
        {
            "titulo": "Pendencias de ratificacao ainda abertas",
            "aberta": bool(_pendencias_ratificadas()),
            "detalhe": "; ".join(
                f"{p['pendencia']} (desde {p['nasceu_em']})"
                for p in _pendencias_ratificadas()) or "Nenhuma.",
        },
        {
            "titulo": "Parametrizacoes que este documento nao consegue contar",
            "aberta": bool(opacas),
            "detalhe": (
                "Os argvalues sao computados em tempo de execucao, entao o "
                "numero de casos destas funcoes nao entra na contagem: "
                + "; ".join(f"`{a}::{n}`" for a, n in sorted(opacas))
                + ". O total de casos declarado abaixo e portanto um PISO, "
                  "nao o numero que o pytest coleta." if opacas else "Nenhuma."),
        },
        {
            "titulo": "Checks sem teste que os cubra (orfaos)",
            "aberta": bool(cob["orfaos"]),
            "detalhe": (", ".join("`%s`" % c for c in cob["orfaos"])
                        if cob["orfaos"] else
                        "Nenhum — a trava do indice reprova o merge que "
                        "introduzir o primeiro."),
        },
        {
            "titulo": "Checks implementados sem mutacao canonica declarada",
            "aberta": bool(sem_mutacao),
            "detalhe": (", ".join("`%s`" % c for c in sem_mutacao)
                        if sem_mutacao else
                        "Nenhum — todo check implementado declara no catalogo "
                        "a violacao minima que deve produzir vermelho."),
        },
        {
            "titulo": "Checks sem docstring de modulo",
            "aberta": bool(sem_docstring),
            "detalhe": (
                ", ".join("`%s`" % c for c in sem_docstring)
                + " — a descricao destes cai para o titulo do catalogo."
                if sem_docstring else
                "Nenhum — a descricao de todos eles sai do proprio modulo."),
        },
        {
            "titulo": "Checks previstos no catalogo e ausentes nesta versao",
            "aberta": bool(previstos),
            "detalhe": (", ".join("`%s`" % c for c in previstos) if previstos
                        else f"Nenhum — os {len(cs)} catalogados estao implementados."),
        },
    ]
    return itens


# ---------------------------------------------------------------------------
# Numeros — todos derivados, nenhum digitado.
# ---------------------------------------------------------------------------

def numeros() -> dict:
    cs = checks()
    fichas = arquivos_de_teste()
    com_teste = [f for f in fichas if f["funcoes"]]
    return {
        "checks": len(cs),
        "por_pilar": {p: len([c for c in cs if c["pack"] == p])
                      for p in sorted({c["pack"] for c in cs})},
        "por_dominio": {d: len([c for c in cs if d in c["dominios"]])
                        for d in catalogo.DOMINIOS},
        "por_tipo": {t: len([c for c in cs if c["tipo"] == t])
                     for t in sorted({c["tipo"] for c in cs})},
        "por_modo": {m: len([c for c in cs if c["modo"] == m])
                     for m in sorted({c["modo"] for c in cs})},
        "por_fase": {f: len([c for c in cs if c["fase"] == f])
                     for f in sorted({c["fase"] for c in cs if c["fase"] is not None})},
        "criticos": sorted(c["id"] for c in cs if "CRITICO" in c["severidades"]),
        "podem_pular": sorted(c["id"] for c in cs if "SkipCheck" in c["desfechos"]),
        "podem_indeterminar": sorted(c["id"] for c in cs
                                     if "CheckIndeterminado" in c["desfechos"]),
        "arquivos_de_teste": len(com_teste),
        "arquivos_auxiliares": sorted(f["arquivo"] for f in fichas if not f["funcoes"]),
        "funcoes": sum(len(f["funcoes"]) for f in fichas),
        "casos": sum(f["casos"] for f in fichas),
        "linhas_de_teste": sum(f["linhas"] for f in fichas),
    }


# ---------------------------------------------------------------------------
# As famílias de teste. A unica coisa deste documento que e JULGAMENTO, e por
# isso fica declarada — como o substrato em `pse/cobertura.py`. O que a
# declaracao NAO faz e inventar numero: os totais de cada familia sao somados
# das fichas, e um arquivo novo sem familia declarada REPROVA (nao cai num
# balde "outros", que e onde a divisao de um documento vai morrer).
# ---------------------------------------------------------------------------

FAMILIAS = (
    ("estratos", "Um arquivo por pacote de checks",
     "Cada estrato tecnico tem o seu: o teste vive perto do check que prova.",
     ["test_frontend.py", "test_api_estrato.py", "test_backend_estrato.py",
      "test_data_estrato.py", "test_ia_estrato.py", "test_ia_terceiros.py",
      "test_lineage.py", "test_rust.py"]),
    ("dinamica", "Camada dinamica — o navegador",
     "O que so existe com a aplicacao no ar. `NetworkLog` fabricado verde nao "
     "prova observacao, e por isso o motor e testado antes dos checks.",
     ["test_navegador.py", "test_dinamico.py", "test_dinamico_fase2.py",
      "test_superficie_dinamica.py"]),
    ("contrato", "Contrato e autorizacao",
     "O que a suite promete ao consumidor, e o que ela promete ao ALVO: "
     "passivo que emita uma requisicao a mais reprova.",
     ["test_contrato.py", "test_trabalho_a.py", "test_trabalho_b.py",
      "test_alvo_local.py"]),
    ("cobertura", "Cobertura honesta",
     "A fachada e o inimigo: os estados nao colapsam, `pulado` nao vira "
     "auditado, arquivo ilegivel nao apaga o veredito dos demais.",
     ["test_cobertura.py", "test_cobertura_web.py", "test_html_no_alcance.py"]),
    ("regua", "A regua e o catalogo (D-13)",
     "Lista curada mora em `pse/data/`, nunca no `.py` do check e nunca "
     "copiada ao consumidor; e nao muda em silencio.",
     ["test_regua.py", "test_catalogo.py", "test_dominio.py", "test_versao.py"]),
    ("mordida", "Provas negativas — o gate tem de morder",
     "Check que nunca foi visto reprovando nada e hipotese, nao trava.",
     ["test_mordida.py", "test_mutacao.py", "test_ratificacao.py",
      "test_reprodutibilidade.py", "test_indice.py"]),
    ("integracao", "Integracao de ponta a ponta",
     "A regua contra um sistema de verdade, e os riscos que so aparecem "
     "quando as pecas correm juntas.",
     ["test_aceite.py", "test_fase3.py"]),
)


class FamiliaAusente(Exception):
    """Arquivo de teste sem familia declarada em `FAMILIAS`.

    Nao ha balde `outros`: um documento cuja divisao aceita qualquer coisa
    deixa de dividir. Arquivo novo entra numa familia existente ou funda uma,
    e as duas decisoes sao de quem escreve o teste.
    """


def familias() -> list:
    fichas = {f["arquivo"]: f for f in arquivos_de_teste()}
    declarados = {a for _, _, _, arqs in FAMILIAS for a in arqs}
    orfaos = sorted(a for a, f in fichas.items() if f["funcoes"] and a not in declarados)
    if orfaos:
        raise FamiliaAusente(
            "arquivo(s) de teste sem familia declarada em pse.testes.FAMILIAS: "
            + ", ".join(orfaos)
            + ". Declare a familia (ou funde uma nova) e regenere a doc: "
            + COMO_REGENERAR.replace("\n", " / "))
    saida = []
    for chave, titulo, nota, arqs in FAMILIAS:
        membros = [fichas[a] for a in sorted(arqs) if a in fichas]
        saida.append({
            "chave": chave, "titulo": titulo, "nota": nota,
            "arquivos": membros,
            "funcoes": sum(len(m["funcoes"]) for m in membros),
            "casos": sum(m["casos"] for m in membros),
            "ausentes": sorted(a for a in arqs if a not in fichas),
        })
    return saida


# ---------------------------------------------------------------------------
# Renderizacao
# ---------------------------------------------------------------------------

def _cab(nivel, texto):
    return f"{'#' * nivel} {texto}"


def _tabela(cabecalho, linhas) -> list:
    saida = ["| " + " | ".join(cabecalho) + " |",
             "|" + "|".join("---" for _ in cabecalho) + "|"]
    saida += ["| " + " | ".join(c) + " |" for c in linhas]
    return saida


def _sev(c) -> str:
    s = [x for x in c["severidades"] if x in ("CRITICO", "ALTO", "MEDIO", "BAIXO")]
    if c["severidade_dinamica"]:
        s.append("por tipo")
    return ", ".join(s) or "—"


def _desfecho(c) -> str:
    mapa = {"SkipCheck": "pula", "CheckIndeterminado": "indetermina",
            "NaoHabilitado": "nao-habilitado"}
    return ", ".join(mapa[d] for d in c["desfechos"] if d in mapa) or "—"


def _rodape(versao=None, data=None) -> list:
    L = ["", MARCA_FIM_DO_CORPO, ""]
    L.append("> Tudo acima desta marca e comparado byte a byte pela trava de CI.")
    L.append("> O que vier abaixo dela e volatil de proposito e nao reprova merge.")
    L.append("")
    if versao:
        L.append(f"- pacote: `pse-suite {versao}`")
    if data:
        L.append(f"- gerado em: {data}")
    L.append("- regenerar: `python -m pse.testes > docs/TESTES.md`")
    L.append("- regenerar indice: `python -m pse.testes --indice > "
             "docs/INDICE-DE-TESTES.md`")
    return L


def corpo_comparado(texto: str) -> str:
    """O trecho do documento que a trava compara — tudo antes da marca.

    Existe para que versao do pacote e data de geracao possam viver no
    arquivo sem transformar cada bump em merge reprovado por ruido.
    """
    return texto.split(MARCA_FIM_DO_CORPO)[0]


def gerar_documento(versao=None, data=None) -> str:
    n = numeros()
    cs = checks()
    cob = cobertura_de_checks()
    fams = familias()
    fichas = {f["arquivo"]: f for f in arquivos_de_teste()}

    L = [_cab(1, "Testes da PSE Suite"), ""]
    L += [
        "> **Este documento e GERADO.** Nao edite: rode",
        "> `python -m pse.testes > docs/TESTES.md`. A trava de CI regenera e",
        "> compara a cada merge — divergiu, o merge nao abre.",
        "",
        "A palavra *teste* cobre duas coisas nesta suite, e mistura-las e o erro",
        "mais facil de cometer. A **Camada A** e o que a PSE audita num alvo; a",
        "**Camada B** e o que prova que a Camada A funciona. A primeira e o",
        "produto; a segunda e a garantia de que o produto nao mente.",
        "",
    ]
    L += _tabela(
        ["Camada", "O que e", "Quantidade", "Onde vive", "Contra quem roda"],
        [["**A — Checks**", "O que a PSE audita num alvo",
          f"**{n['checks']}** checks", "`pse/checks/**`", "O sistema auditado"],
         ["**B — Testes**", "O que prova que os checks funcionam",
          f"**{n['funcoes']}** funcoes / **{n['casos']}+** casos",
          "`tests/**`", "A propria PSE"]])
    L += ["", "---", ""]

    # ------------------------------------------------------------ Camada A
    L += [_cab(1, f"Camada A — os {n['checks']} checks"), "",
          _cab(2, "A.1 Como estao divididos"), "",
          "Quatro eixos ortogonais. Nenhum check e duplicado para servir a dois.", ""]

    L += [_cab(3, "Por pilar — que valor esta em jogo"), "",
          "O prefixo do ID codifica o pilar, sempre. Dominio e multivalorado e",
          "vive em `domain`, nunca no prefixo.", ""]
    L += _tabela(["Pilar", "Prefixo", "Checks"],
                 [[p, f"`{catalogo.PREFIXO_DO_PILAR[p]}-`", str(q)]
                  for p, q in sorted(n["por_pilar"].items())])

    total_dom = sum(n["por_dominio"].values())
    L += ["", _cab(3, "Por dominio — onde o risco se manifesta"), "",
          f"E lista: {n['checks']} checks produzem {total_dom} atribuicoes.", ""]
    L += _tabela(["Dominio", "Checks"],
                 [[f"`{d}`", str(q)] for d, q in sorted(n["por_dominio"].items(),
                                                        key=lambda kv: (-kv[1], kv[0]))])

    L += ["", _cab(3, "Por tipo — de onde vem o fato"), ""]
    L += _tabela(["Tipo", "Checks"],
                 [[f"`{t}`", str(q)] for t, q in sorted(n["por_tipo"].items(),
                                                        key=lambda kv: (-kv[1], kv[0]))])

    L += ["", _cab(3, "Por modo — quem pode disparar"), "",
          "O contrato de autorizacao: `inventory` nao toca rede, `passive` le",
          "com a propria identidade, `active` sonda e exige revisores.", ""]
    L += _tabela(["Modo", "Checks"],
                 [[f"`{m}`", str(q)] for m, q in sorted(n["por_modo"].items(),
                                                        key=lambda kv: (-kv[1], kv[0]))])

    L += ["", _cab(3, "Desfechos possiveis"), "",
          "E o que distingue a suite de um linter: nem todo check termina em",
          "verde ou achado.", ""]
    L += _tabela(["Desfecho", "Quantos podem", "O que significa"],
                 [[f"`CRITICO`", str(len(n["criticos"])),
                   "emitem a severidade que reprova fail-closed (exit 10)"],
                  ["`pulado`", str(len(n["podem_pular"])),
                   "pre-requisito declarado ausente, com motivo no laudo"],
                  ["`indeterminado`", str(len(n["podem_indeterminar"])),
                   "tentou e nao decidiu — **bloqueia** (exit 20)"]])
    L += ["", "Emitem `CRITICO`: " + ", ".join(f"`{c}`" for c in n["criticos"]) + ".", ""]

    L += ["---", ""]
    nomes = {"privacy": "P — Privacidade", "security": "S — Seguranca",
             "ethics": "E — Etica"}
    letra = {"privacy": "2", "security": "3", "ethics": "4"}
    for pack in ("privacy", "security", "ethics"):
        doss = [c for c in cs if c["pack"] == pack]
        L += [_cab(2, f"A.{letra[pack]} Pacote {nomes[pack]} ({len(doss)})"), ""]
        L += _tabela(
            ["ID", "Dominio", "Tipo / Modo", "Severidade", "Desfechos", "O que faz"],
            [[f"**{c['id']}**",
              ", ".join(c["dominios"]),
              f"{c['tipo']} / {c['modo']}",
              _sev(c),
              _desfecho(c),
              descricao_de(c)] for c in doss])
        L += [""]

    L += ["---", ""]

    # ------------------------------------------------------------ Camada B
    L += [_cab(1, f"Camada B — os {n['funcoes']} testes da suite"), "",
          f"{n['arquivos_de_teste']} arquivos com teste "
          f"({n['linhas_de_teste']} linhas), mais "
          f"{len(n['arquivos_auxiliares'])} auxiliares "
          f"({', '.join('`%s`' % a for a in n['arquivos_auxiliares'])}). "
          f"Divididos por **familia de garantia**, nao por ordem alfabetica.",
          ""]

    L += [_cab(2, "B.1 As familias"), ""]
    L += _tabela(["Familia", "Arquivos", "Funcoes", "Casos"],
                 [[f["titulo"], str(len(f["arquivos"])), str(f["funcoes"]),
                   str(f["casos"])] for f in fams])
    L += [""]

    for i, f in enumerate(fams, start=2):
        L += [_cab(2, f"B.{i} {f['titulo']} — {f['funcoes']} funcoes"), "",
              f["nota"], ""]
        L += _tabela(["Arquivo", "Fn", "Casos", "Marcadores", "O que garante"],
                     [[f"`{m['arquivo']}`", str(len(m["funcoes"])), str(m["casos"]),
                       ", ".join(f"`{x}`" for x in m["marcadores"]) or "—",
                       m["descricao"] or "—"] for m in f["arquivos"]])
        L += [""]

    n_fam = len(fams) + 2
    declarados = marcadores_declarados()
    em_uso = sorted({m for fi in fichas.values() for m in fi["marcadores"]})
    L += [_cab(2, f"B.{n_fam} Marcadores"), "",
          "Selecao por eixo, declarada em `pyproject.toml`. Marcador em uso e",
          "nao declarado la reprova o proprio pytest.", ""]
    L += _tabela(["Marcador", "O que seleciona", "Arquivos que o usam"],
                 [[f"`{m}`", declarados[m],
                   ", ".join(f"`{a}`" for a in sorted(fichas)
                             if m in fichas[a]["marcadores"]) or "—"]
                  for m in sorted(declarados)])
    embutidos = [m for m in em_uso if m not in declarados]
    L += ["", "Embutidos do pytest, que aparecem na arvore mas nao sao eixo de",
          "selecao desta suite: " + ", ".join(f"`{m}`" for m in embutidos) + ".",
          ""]

    # ------------------------------------------------------- A ponte A x B
    L += ["---", "",
          _cab(1, "A ponte — todo check tem teste"), "",
          "Um documento que lista checks e testes sem provar que os segundos",
          "cobrem os primeiros e meia-garantia. O indice",
          "(`docs/INDICE-DE-TESTES.md`) faz a ligacao check a check, e",
          "`tests/test_indice.py` **reprova o merge** que introduzir um check",
          "sem teste — ou um teste citando check que nao existe.", ""]
    L += _tabela(["Situacao", "Hoje", "O que acontece se mudar"],
                 [["Checks cobertos por teste",
                   f"{n['checks'] - len(cob['orfaos'])} de {n['checks']}",
                   "check orfao reprova a trava"],
                  ["Referencias a check inexistente",
                   str(len(cob["fantasmas"])),
                   "referencia fantasma reprova a trava"],
                  ["Excecoes declaradas (`CHECKS_FORA_DO_CATALOGO`)",
                   str(len(cob["excecoes_declaradas"])),
                   "excecao calada reprova; declarada, aparece no indice"]])
    L += [""]

    # ------------------------------------------------------------- Lacunas
    L += ["---", "",
          _cab(1, "O que NAO esta testado"), "",
          "Esta secao e gerada do estado real, e isso e o ponto. Uma doc",
          "obrigatoria que so listasse o que tem cobertura seria propaganda —",
          "e omitir lacuna e exatamente a cobertura de fachada que a suite",
          "cobra dos alvos.", ""]
    for item in lacunas():
        marca = "**LACUNA ABERTA**" if item["aberta"] else "fechada"
        L += [f"- **{item['titulo']}** — {marca}. {item['detalhe']}"]
    L += [""]

    L += _rodape(versao, data)
    return "\n".join(L) + "\n"


def gerar_indice(versao=None, data=None) -> str:
    cs = checks()
    cob = cobertura_de_checks()
    fichas = {f["arquivo"]: f for f in arquivos_de_teste()}

    L = [_cab(1, "Indice de testes — check a check"), ""]
    L += [
        "> **Este documento e GERADO.** Nao edite: rode",
        "> `python -m pse.testes --indice > docs/INDICE-DE-TESTES.md`.",
        "",
        "Para cada check: o modulo que o implementa, os arquivos de teste que o",
        "exercitam, a mutacao canonica que ele tem de reprovar, as reguas que",
        "consome e o substrato onde o vetor vive.",
        "",
        "A coluna **Como** diz de que evidencia a cobertura foi deduzida —",
        "`import` (o teste importa o modulo do check) ou `id` (o ID aparece",
        "como literal na arvore do teste). As duas sao ancoradas no fato: um",
        "comentario citando o check nao chega a arvore sintatica, e portanto",
        "nao cobre nada (D-01).",
        "",
    ]

    for pack, nome in (("privacy", "P — Privacidade"),
                       ("security", "S — Seguranca"),
                       ("ethics", "E — Etica")):
        L += [_cab(2, f"Pacote {nome}"), ""]
        linhas = []
        for c in [x for x in cs if x["pack"] == pack]:
            v = cob["por_check"][c["id"]]
            como = "+".join(x for x in (
                "import" if v["por_import"] else "", "id" if v["por_id"] else "") if x)
            mut = c["mutacao"] or {}
            linhas.append([
                f"**{c['id']}**",
                f"`{c['modulo']}`" if c["modulo"] else "—",
                ", ".join(f"`{a}`" for a in v["arquivos"]) or "**NENHUM**",
                como or "—",
                (f"{mut.get('espera')}: {mut.get('descricao')}" if mut else "—"),
                ", ".join(f"`{r}`" for r in c["reguas"]) or "—",
                ", ".join(c["substrato"]) or "—",
            ])
        L += _tabela(["Check", "Modulo", "Testes que cobrem", "Como",
                      "Mutacao canonica (espera)", "Reguas", "Substrato"], linhas)
        L += [""]

    L += ["---", "", _cab(2, "Os dois defeitos que a trava reprova"), ""]
    L += [_cab(3, "Checks orfaos — sem teste que os cubra"), ""]
    L += (["- " + ", ".join(f"`{c}`" for c in cob["orfaos"])] if cob["orfaos"]
          else ["Nenhum. Todo check do catalogo e exercitado por pelo menos um",
                "arquivo de teste.", ""])
    L += ["", _cab(3, "Referencias fantasma — teste citando check inexistente"), ""]
    if cob["fantasmas"]:
        L += _tabela(["Arquivo", "ID citado"],
                     [[f"`{d['arquivo']}`", f"`{d['id']}`"] for d in cob["fantasmas"]])
    else:
        L += ["Nenhuma nao declarada.", ""]

    L += ["", _cab(3, "Excecoes declaradas"), "",
          f"ID fora do catalogo que um teste precisa citar de proposito. Vive em",
          f"`{DECLARACAO_DE_EXCECAO}` no proprio modulo de teste, com motivo:",
          "declarada, aparece aqui; calada, reprova.", ""]
    if cob["excecoes_declaradas"]:
        L += _tabela(["Arquivo", "ID", "Motivo"],
                     [[f"`{d['arquivo']}`", f"`{d['id']}`", d["motivo"]]
                      for d in cob["excecoes_declaradas"]])
    else:
        L += ["Nenhuma.", ""]

    L += ["", "---", "", _cab(2, "O caminho inverso — de cada teste aos checks"), ""]
    L += _tabela(["Arquivo", "Checks que exercita"],
                 [[f"`{a}`",
                   ", ".join(f"`{c}`" for c in sorted(
                       set(fichas[a]["ids_exercitados"]) & set(cob["por_check"])))
                   or "—"]
                  for a in sorted(fichas) if fichas[a]["funcoes"]])

    L += _rodape(versao, data)
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------------------

def _main(argv) -> int:
    from pse.evidence import versao_suite
    quer_indice = "--indice" in argv[1:]
    desconhecidos = [a for a in argv[1:] if a != "--indice"]
    if desconhecidos:
        print("uso: python -m pse.testes [--indice]")
        return 30
    versao = versao_suite()
    texto = (gerar_indice(versao) if quer_indice else gerar_documento(versao))
    print(texto, end="")
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv))
