"""P-17 — discriminacao sem modelo nenhum: o filtro da busca.

E-05 procura proxy de discriminacao entrando em score. Este pergunta uma
coisa muito mais simples e muito mais comum: **a API deixa alguem pedir a
lista de pessoas por raca?**

Nao precisa de ML, nem de score, nem de feature engineering. Um endpoint
com `?raca=` e `?cep=` entrega segmentacao discriminatoria pronta para
quem souber montar a URL — e a combinacao de dois filtros aparentemente
inocentes (bairro + faixa de renda) reconstroi o recorte que a lei proibe
sem que nenhuma linha do codigo mencione discriminacao.

E um check de BORDA porque a borda e onde a capacidade fica publica. O
mesmo `WHERE raca = ?` dentro de um relatorio interno tem outro perfil de
risco; exposto num endpoint, vira produto.

DOIS LADOS DO MESMO FATO:
  - o CODIGO: a view liga um parametro de consulta ao repositorio, seja
    por `request.args.get("raca")`, seja por parametro nomeado da funcao.
  - o CONTRATO: `parameters: [{in: query, name: raca}]` na spec. E aqui
    que a capacidade fica publica, entao o contrato conta sozinho.

D-01: rota e reconhecida por DECORATOR com literal de caminho (AST), e o
parametro por chamada de extrator com chave literal. Comentario citando
`raca` nao cria achado; comentario citando a guarda nao desliga nenhum.

D-08: uma guarda que EXECUTA no corpo da view — allowlist de filtros
permitidos, validador que recusa o resto — desliga o achado. O caminho
correto mais comum sequer chega aqui: quem monta o filtro a partir de um
vocabulario fechado nunca menciona um campo proibido.
"""
import ast

import yaml

from pse.engine import scan, yamlloc
from pse.engine.registry import check
from pse.model import Finding, Severidade

BASE = "LGPD Art. 6o IX + Art. 11 (nao discriminacao)"
REGUA = "api-contract"


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _proibidos(ctx) -> set:
    """Proxies de discriminacao + sensiveis. Regua compartilhada, nao propria."""
    return ({t.lower() for t in ctx.data["prohibited-filters"]["proxies_discriminacao"]}
            | {t.lower() for t in ctx.data["sensitive-fields"]["sensiveis"]})


def _rotas(arvore):
    """(funcao, caminho) para toda funcao decorada como rota HTTP.

    O fato e o decorator COM literal de caminho: `@app.get("/clientes")`.
    `@lru_cache` nao entra, e um `get` que nao recebe rota tampouco.
    """
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in no.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            nome = scan.nome_chamado(dec).split(".")[-1].lower()
            caminho = next((a.value for a in dec.args
                            if isinstance(a, ast.Constant)
                            and isinstance(a.value, str)), None)
            if caminho is not None:
                yield no, nome, caminho
                break


def _guardada(no, guardas) -> bool:
    for sub in ast.walk(no):
        if isinstance(sub, ast.Call) and scan.nome_casa_tokens(
                scan.nome_chamado(sub), guardas):
            return True
    return False


def _filtros_da_view(no, extratores: set) -> list:
    """(nome_do_filtro, linha) — as duas formas de a view receber um filtro."""
    achados = []
    for arg in no.args.args + no.args.kwonlyargs:
        if arg.arg != "self":
            achados.append((arg.arg.lower(), no.lineno))
    for sub in ast.walk(no):
        if not isinstance(sub, ast.Call):
            continue
        alvo = sub.func
        if not isinstance(alvo, ast.Attribute):
            continue
        # `request.args.get("raca")`: o extrator e o objeto sobre o qual
        # `.get` e chamado, nao o `.get`.
        dono = alvo.value
        nome_dono = (dono.attr if isinstance(dono, ast.Attribute)
                     else dono.id if isinstance(dono, ast.Name) else "")
        if nome_dono.lower() not in extratores:
            continue
        for a in sub.args:
            if isinstance(a, ast.Constant) and isinstance(a.value, str):
                achados.append((a.value.lower(), sub.lineno))
    for sub in ast.walk(no):
        # `request.args["raca"]` — a forma por indice.
        if isinstance(sub, ast.Subscript) and isinstance(sub.value, ast.Attribute):
            if sub.value.attr.lower() in extratores and isinstance(
                    sub.slice, ast.Constant) and isinstance(sub.slice.value, str):
                achados.append((sub.slice.value.lower(), sub.lineno))
    return achados


def _do_contrato(ctx, proibidos: set) -> list:
    """(arquivo, linha, rota, filtro) para filtro proibido declarado na spec."""
    marcas = [m.lower() for m in ctx.data[REGUA]["marcas_de_spec"]]
    saida = []
    for p in scan.arquivos(ctx.repo, {".yaml", ".yml", ".json"}):
        try:
            doc = yaml.safe_load(scan.ler(p))
        except yaml.YAMLError:
            continue                     # S-12 e quem responde por spec ilegivel
        if not isinstance(doc, dict) or not any(m in doc for m in marcas):
            continue
        texto = scan.ler(p)
        for rota, metodos in (doc.get("paths") or {}).items():
            if not isinstance(metodos, dict):
                continue
            for verbo, op in metodos.items():
                if not isinstance(op, dict):
                    continue
                for par in op.get("parameters") or []:
                    if not isinstance(par, dict) or par.get("in") != "query":
                        continue
                    nome = str(par.get("name", "")).lower()
                    if nome in proibidos:
                        linha = yamlloc.localizar_valor(texto, "name", nome)
                        saida.append((scan.rel(ctx.repo, p), linha,
                                      f"{verbo.upper()} {rota}", nome))
    return saida


@check("P-17", "privacy", "Filtro sensivel em endpoint de busca", base_legal=BASE)
def filtro_sensivel_na_busca(ctx):
    proibidos = _proibidos(ctx)
    extratores = {t.lower() for t in _r(ctx, "extratores_de_query")}
    guardas = _r(ctx, "guardas_de_filtro")
    findings, vistos = [], set()

    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        rel = scan.rel(ctx.repo, p)
        linhas = scan.ler(p).splitlines()
        for no, verbo, caminho in _rotas(arvore):
            if _guardada(no, guardas):
                continue                 # D-08: a allowlist executa
            for nome, linha in _filtros_da_view(no, extratores):
                if nome not in proibidos:
                    continue
                chave = (rel, linha, nome)
                if chave in vistos:
                    continue
                vistos.add(chave)
                findings.append(Finding(
                    check_id="P-17", pack="privacy", severidade=Severidade.ALTO,
                    titulo=f"Rota `{verbo.upper()} {caminho}` filtra por "
                           f"'{nome}'",
                    descricao=(
                        f"A view `{no.name}` liga o parametro de consulta "
                        f"'{nome}' a busca sem allowlist. Isto e discriminacao "
                        f"sem modelo nenhum: quem souber montar a URL recebe a "
                        f"lista de pessoas segmentada pelo criterio, e a "
                        f"combinacao de dois filtros inocentes reconstroi o "
                        f"recorte que a lei proibe sem que nenhuma linha do "
                        f"codigo mencione discriminacao."),
                    recomendacao=(
                        "Fechar o vocabulario de busca numa allowlist aplicada "
                        "no servidor e recusar o que estiver fora dela. Se o "
                        "recorte for legitimo (pesquisa, relatorio "
                        "obrigatorio), tira-lo da borda publica e trata-lo "
                        "como agregado com k-anonimato (P-09)."),
                    base_legal=BASE, arquivo=rel, linha=linha,
                    snippet=(linhas[linha - 1].strip()[:200]
                             if linha and linha <= len(linhas) else None)))

    for arquivo, linha, rota, nome in _do_contrato(ctx, proibidos):
        findings.append(Finding(
            check_id="P-17", pack="privacy", severidade=Severidade.ALTO,
            titulo=f"Contrato publica filtro '{nome}' em `{rota}`",
            descricao=(
                f"A spec declara '{nome}' como parametro de consulta. No "
                f"contrato a capacidade deixa de ser detalhe de "
                f"implementacao e vira produto: qualquer consumidor le que "
                f"a busca por esse criterio existe e e suportada."),
            recomendacao=("Remover o parametro do contrato. Enquanto ele "
                          "estiver publicado, remove-lo do codigo apenas "
                          "quebra o contrato — a promessa continua de pe."),
            base_legal=BASE, arquivo=arquivo, linha=linha))
    return findings
