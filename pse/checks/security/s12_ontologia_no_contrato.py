"""S-12 — a ontologia do contrato: declarada, e implementada.

O artefato proprio do estrato de API e o CONTRATO. Uma API existe para ser
consumida por quem nao le o seu codigo: o time do outro lado toma decisoes
— o que loga, o que cacheia, o que manda para um terceiro — olhando so a
spec. Se a spec carrega dado pessoal e nao diz que carrega, a ontologia
existe apenas na cabeca de quem a escreveu, e some junto com essa pessoa.

`x-` e o espaco de extensao do proprio OpenAPI. Declarar ali a PII, os
campos sensiveis e a allowlist por escopo poe a governanca no lugar onde o
consumidor ja olha, em vez de num wiki que ninguem le.

DOIS VETORES, e o segundo e o que interessa:

  A. SILENCIO — o schema expoe campo de PII e nao declara ontologia
     nenhuma (ou declara uma que omite justamente esse campo).
  B. PROMESSA SEM LASTRO — o `x-ethics` declara campos que a implementacao
     nao tem. Pior que o silencio: o silencio nao engana ninguem, e uma
     ontologia que ninguem implementou e confiada por quem le.

O QUE ESTE CHECK NAO FAZ. A ligacao schema -> DTO e por NOME de classe. Se
o repositorio nao tem classe com o nome do schema, o vetor B nao e avaliado
para ele — e nao vira achado nem indeterminacao, porque um repositorio que
so publica contrato (gateway, monorepo de specs) nao tem DTO nenhum e nao
esta errado por isso. Prometer resolucao de nomes que nao se entrega seria
pior que a lacuna: o consumidor confiaria numa cobertura inexistente.

D-01: o contrato e lido pelo PARSER, nunca por texto. `# x-ethics: ...`
num comentario de YAML nao chega ao documento carregado, entao nao liga
nem desliga nada — ha teste que prova.

D-08: schema sem dado pessoal nao precisa de ontologia. Exigir `x-ethics`
de um `Pedido` com id e valor seria burocracia, e burocracia ensina o time
a preencher por reflexo — que e o oposto de uma ontologia util.
"""
import ast

import yaml

from pse.engine import scan, yamlloc
from pse.engine.registry import check
from pse.model import CheckIndeterminado, Finding, Severidade, SkipCheck

BASE = "LGPD Art. 6o VI (transparencia) + Art. 46 (seguranca)"
REGUA = "api-contract"
EXTENSOES = {".yaml", ".yml", ".json"}


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _parece_spec(ctx, p) -> bool:
    """O NOME sugere contrato. So decide indeterminacao — nunca conformidade.

    Usar o nome do arquivo para BLOQUEAR e seguro: o pior caso e um arquivo
    inocente virar pergunta. Usa-lo para liberar seria o oposto, e ai sim
    romperia o D-01.
    """
    nome = p.name.lower()
    return any(str(m).lower() in nome
               for m in _r(ctx, "nomes_de_arquivo_de_contrato"))


def _specs(ctx):
    """(caminho, documento) de todo arquivo que SE DECLARA spec de API."""
    marcas = [m.lower() for m in _r(ctx, "marcas_de_spec")]
    for p in scan.arquivos(ctx.repo, EXTENSOES):
        try:
            doc = yaml.safe_load(scan.ler(p))
        except yaml.YAMLError as e:
            if _parece_spec(ctx, p):
                raise CheckIndeterminado(
                    f"{scan.rel(ctx.repo, p)} tem nome de contrato de API e nao "
                    f"pode ser lido ({e.__class__.__name__}) — sem parser nao ha "
                    f"como dizer que campos ele expoe, e nao decidir bloqueia") from e
            continue
        if isinstance(doc, dict) and any(m in doc for m in marcas):
            yield p, doc


def _schemas(doc: dict):
    """OpenAPI 3 (`components.schemas`) e Swagger 2 (`definitions`)."""
    saida = {}
    comp = (doc.get("components") or {}).get("schemas") or {}
    if isinstance(comp, dict):
        saida.update({k: v for k, v in comp.items() if isinstance(v, dict)})
    defs = doc.get("definitions") or {}
    if isinstance(defs, dict):
        saida.update({k: v for k, v in defs.items() if isinstance(v, dict)})
    return saida


def _caminho_do_schema(doc: dict, nome: str) -> list:
    if nome in ((doc.get("components") or {}).get("schemas") or {}):
        return ["components", "schemas", nome]
    return ["definitions", nome]


def _ontologia(ctx, schema: dict):
    ext = _r(ctx, "ontologia")["extensao"]
    valor = schema.get(ext)
    return valor if isinstance(valor, dict) else None


def _declarados(ctx, ontologia: dict) -> set:
    """Campos que a ontologia assume carregar — PII e sensiveis somados."""
    onto = _r(ctx, "ontologia")
    chaves = list(onto["campos_pii"]) + list(onto["campos_sensiveis"])
    saida = set()
    for chave in chaves:
        valor = ontologia.get(chave)
        if isinstance(valor, str):
            saida.add(valor.lower())
        elif isinstance(valor, (list, tuple, set)):
            saida |= {str(v).lower() for v in valor}
        elif isinstance(valor, dict):
            saida |= {str(v).lower() for v in valor}
    return saida


def _pii_da_regua(ctx) -> set:
    pii = {t.lower() for grupo in ctx.data["pii-patterns"].values() for t in grupo}
    return pii | {t.lower() for t in ctx.data["sensitive-fields"]["sensiveis"]}


def _dtos(ctx) -> dict:
    """{nome_da_classe_em_minusculas: {campos}} — o FATO, colhido da AST.

    Conta como campo o que uma instancia realmente carrega: anotacao de
    classe (`cpf: str`), atribuicao de classe e parametro de `__init__`.
    """
    saida = {}
    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        for no in ast.walk(arvore):
            if not isinstance(no, ast.ClassDef):
                continue
            campos = set()
            for corpo in no.body:
                if isinstance(corpo, ast.AnnAssign) and isinstance(
                        corpo.target, ast.Name):
                    campos.add(corpo.target.id.lower())
                elif isinstance(corpo, ast.Assign):
                    for alvo in corpo.targets:
                        if isinstance(alvo, ast.Name):
                            campos.add(alvo.id.lower())
                elif isinstance(corpo, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and corpo.name == "__init__":
                    for arg in corpo.args.args + corpo.args.kwonlyargs:
                        if arg.arg != "self":
                            campos.add(arg.arg.lower())
            anterior = saida.get(no.name.lower())
            saida[no.name.lower()] = {
                "campos": campos | (anterior["campos"] if anterior else set()),
                "arquivo": scan.rel(ctx.repo, p), "linha": no.lineno}
    return saida


@check("S-12", "security", "Ontologia x-ethics no contrato", base_legal=BASE)
def ontologia_no_contrato(ctx):
    specs = list(_specs(ctx))
    if not specs:
        raise SkipCheck(
            "nenhum arquivo se declara contrato de API (sem chave `openapi` "
            "nem `swagger` de topo) — nao ha contrato a confrontar")

    pii = _pii_da_regua(ctx)
    ext = _r(ctx, "ontologia")["extensao"]
    dtos = _dtos(ctx)
    findings = []

    for p, doc in specs:
        rel = scan.rel(ctx.repo, p)
        texto = scan.ler(p)
        for nome, schema in sorted(_schemas(doc).items()):
            props = schema.get("properties")
            if not isinstance(props, dict):
                continue
            expostos = sorted(c for c in props if str(c).lower() in pii)
            onto = _ontologia(ctx, schema)
            declarados = _declarados(ctx, onto) if onto else set()
            linha = yamlloc.localizar(texto, _caminho_do_schema(doc, nome))

            # --------------------------------------------- vetor A: silencio
            omitidos = [c for c in expostos if str(c).lower() not in declarados]
            if omitidos:
                findings.append(Finding(
                    check_id="S-12", pack="security", severidade=Severidade.ALTO,
                    titulo=f"Schema `{nome}` expoe dado pessoal sem declarar "
                           f"ontologia `{ext}`",
                    descricao=(
                        f"Campos {omitidos} sao dado pessoal pela regua da "
                        f"suite e o contrato nao os declara"
                        + ("" if onto else f" — o schema nao tem `{ext}`") + ". "
                        f"Quem consome esta API decide o que logar, cachear e "
                        f"repassar a terceiro lendo a spec, nao o seu codigo: "
                        f"contrato que carrega dado pessoal em silencio delega "
                        f"a decisao sem dar a informacao."),
                    recomendacao=(
                        f"Declarar `{ext}` no schema com os campos de PII, os "
                        f"sensiveis, a finalidade e a allowlist por escopo. E "
                        f"extensao do proprio OpenAPI: a governanca fica onde o "
                        f"consumidor ja olha."),
                    base_legal=BASE, arquivo=rel, linha=linha,
                    snippet=f"{nome}: properties {sorted(props)[:8]}"))

            # ------------------------------- vetor B: promessa sem lastro
            if not declarados:
                continue
            dto = dtos.get(nome.lower())
            if dto is None:
                continue                 # sem classe homonima: ver docstring
            faltando = sorted(c for c in declarados if c not in dto["campos"])
            if not faltando:
                continue
            findings.append(Finding(
                check_id="S-12", pack="security", severidade=Severidade.ALTO,
                titulo=f"Ontologia de `{nome}` promete campo que a implementacao "
                       f"nao tem",
                descricao=(
                    f"O contrato declara em `{ext}` os campos {faltando}, e a "
                    f"classe `{nome}` em {dto['arquivo']} nao os implementa. "
                    f"Isto e pior que a ausencia de ontologia: silencio nao "
                    f"engana ninguem, e uma declaracao que a implementacao nao "
                    f"cumpre e confiada por quem le. Auditoria, DPIA e o time "
                    f"do outro lado passam a raciocinar sobre um sistema que "
                    f"nao existe."),
                recomendacao=(
                    "Alinhar as duas pontas: ou o DTO passa a carregar o campo "
                    "declarado, ou a declaracao sai do contrato. Ontologia so "
                    "vale enquanto descreve o que roda."),
                base_legal=BASE, arquivo=rel, linha=linha,
                snippet=f"{ext} de {nome} declara {sorted(declarados)}"))
    return findings
