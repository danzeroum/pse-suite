"""E-08 — provenance/lineage: origem → transformacao → destino rastreavel.

A pergunta que ninguem consegue responder depois de um incidente: *este dado
veio de onde, passou por que e foi parar aonde?* Sem trilha, o Art. 18 vira
arqueologia — nao se corrige, elimina ou porta o que ninguem sabe rastrear —
e o Art. 37 fica sem lastro, porque registrar a operacao pressupoe saber qual
operacao foi feita.

ANCORA NO FATO (D-01): o que satisfaz este check e um ARTEFATO que resolve,
com origem, transformacao e destino por dataset. Um README afirmando
"temos rastreabilidade completa" e exatamente o tipo de evidencia recusada
aqui — se afirmacao bastasse, a trava seria desligavel escrevendo um
paragrafo. Por isso a busca so olha `.jsonl`/`.json`/`.yaml`, nunca `.md`.

SEM FALSO-POSITIVO EM CRITICO (D-08): E-08 e ALTO. E gap de governanca, nao
violacao legal direta, e nao entra no conjunto fail-closed ratificado.

Tres estados honestos:
  - nao ha tratamento de dado pessoal a rastrear      -> SkipCheck (N/A)
  - ha tratamento e a trilha falta/nao cobre/incompleta -> Finding ALTO
  - a trilha existe e nao pode ser lida                -> CheckIndeterminado

O que precisa ser rastreado sai do catalogo do consumidor cruzado com a
regua curada de campos sensiveis: remover um termo de `sensitive-fields.yaml`
encolhe a cobertura de E-08 tambem, e o teste-guarda da regua vigia isso.
"""
import json
from pathlib import Path

import yaml

from pse.engine import scan
from pse.engine.registry import check
from pse.model import CheckIndeterminado, Finding, Severidade, SkipCheck

BASE = "rastreabilidade (LGPD Art. 37)"
BASE_COM_TERCEIRO = ("rastreabilidade (LGPD Art. 37) + Art. 42 "
                     "(responsabilidade solidaria)")

CANDIDATOS = ("lineage.jsonl", "lineage.json", "lineage.yaml", "lineage.yml",
              "docs/lineage.jsonl", ".privacy/lineage.jsonl",
              "data/lineage.jsonl", "harness/lineage.jsonl")
OBRIGATORIOS = ("origem", "transformacao", "destino")


def _caminho(ctx):
    """(caminho_relativo, declarado_explicitamente).

    Declaracao explicita vence: se o consumidor aponta um arquivo e ele nao
    existe, isso e o achado — nao motivo para sair procurando outro.
    """
    declarado = ctx.config.get("lineage_path")
    if declarado:
        return declarado, True
    for c in CANDIDATOS:
        if (ctx.repo / c).exists():
            return c, False
    return CANDIDATOS[0], False


def _carregar(arquivo: Path) -> list:
    texto = scan.ler(arquivo)
    try:
        if arquivo.suffix == ".jsonl":
            return [json.loads(l) for l in texto.splitlines() if l.strip()]
        if arquivo.suffix == ".json":
            dado = json.loads(texto)
        else:
            dado = yaml.safe_load(texto)
    except (ValueError, yaml.YAMLError) as e:
        raise CheckIndeterminado(
            f"trilha de lineage ilegivel ({arquivo.name}): {e}. Arquivo "
            f"quebrado nao e 'sem trilha' — e 'nao consegui ler', e isso "
            f"bloqueia em vez de virar achado ou verde") from e
    if isinstance(dado, dict):
        dado = dado.get("datasets") or dado.get("lineage") or []
    if not isinstance(dado, list):
        raise CheckIndeterminado(
            f"trilha de lineage em formato inesperado ({arquivo.name}): "
            f"esperada lista de registros")
    return dado


def _tabelas_a_rastrear(ctx) -> dict:
    """Tabelas com dado pessoal — o que a trilha precisa alcancar."""
    cat = ctx.catalog()
    if cat is None:
        return {}
    sensiveis = {t.lower() for t in ctx.data["sensitive-fields"]["sensiveis"]}
    saida = {}
    for tabela, tmeta in (cat.get("tables") or {}).items():
        campos = []
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            classe = (props or {}).get("class")
            if classe in ("personal", "sensitive") or str(campo).lower() in sensiveis:
                campos.append(str(campo))
        if campos:
            saida[str(tabela)] = sorted(campos)
    return saida


def _base_legal(ctx) -> str:
    manifesto = ctx.manifest_terceiros()
    if manifesto and manifesto.get("integrations"):
        return BASE_COM_TERCEIRO
    return BASE


@check("E-08", "ethics", "Provenance/lineage rastreavel", base_legal=BASE)
def lineage(ctx):
    tabelas = _tabelas_a_rastrear(ctx)
    if not tabelas:
        raise SkipCheck(
            "nenhum tratamento de dado pessoal a rastrear: o catalogo nao "
            "declara campo personal/sensitive (catalogo em si e cobrado por P-04)")

    rel, declarado = _caminho(ctx)
    arquivo = ctx.repo / rel
    base_legal = _base_legal(ctx)

    if not arquivo.exists():
        como = "declarado e inexistente" if declarado else "ausente"
        return [Finding(
            check_id="E-08", pack="ethics", severidade=Severidade.ALTO,
            titulo="Tratamento de dado pessoal sem trilha de proveniencia",
            descricao=f"{len(tabelas)} tabela(s) com dado pessoal "
                      f"({', '.join(sorted(tabelas))}) e nenhuma trilha "
                      f"origem->transformacao->destino ({rel} {como}). "
                      f"Afirmar rastreabilidade em documentacao nao vale: sem "
                      f"artefato que resolva, nao ha como responder de onde o "
                      f"dado veio nem para onde foi depois de um incidente.",
            recomendacao="Emitir lineage.jsonl no pipeline (um registro por "
                         "dataset, com origem, transformacao, destino e campos) "
                         "e versiona-lo junto do codigo que o produz.",
            base_legal=base_legal, arquivo=rel, linha=1)]

    registros = _carregar(arquivo)          # ilegivel -> CheckIndeterminado
    findings = []
    cobertos = set()

    for i, reg in enumerate(registros, 1):
        if not isinstance(reg, dict):
            continue
        faltando = [c for c in OBRIGATORIOS if not str(reg.get(c) or "").strip()]
        nome = str(reg.get("dataset") or reg.get("tabela") or f"registro {i}")
        if faltando:
            findings.append(Finding(
                check_id="E-08", pack="ethics", severidade=Severidade.ALTO,
                titulo=f"Trilha de '{nome}' incompleta",
                descricao=f"O registro nao declara: {', '.join(faltando)}. "
                          f"Uma trilha que para no meio nao rastreia nada ate o "
                          f"fim — e o fim (o destino) e justamente o que "
                          f"interessa quando se pergunta para onde o dado foi.",
                recomendacao="Completar origem, transformacao e destino no "
                             "registro emitido pelo pipeline.",
                base_legal=base_legal, arquivo=rel, linha=i))
            continue
        cobertos.add(nome.lower())
        cobertos.add(nome.lower().split(".")[-1])

    for tabela, campos in sorted(tabelas.items()):
        if tabela.lower() in cobertos:
            continue
        findings.append(Finding(
            check_id="E-08", pack="ethics", severidade=Severidade.ALTO,
            titulo=f"Tabela '{tabela}' com dado pessoal fora da trilha",
            descricao=f"Os campos {campos} sao pessoais e nenhum registro de "
                      f"lineage cobre '{tabela}'. Existir trilha nao basta: ela "
                      f"tem de alcancar os dados que existem, senao a cobertura "
                      f"aparente esconde o buraco.",
            recomendacao=f"Acrescentar registro de lineage para '{tabela}' com "
                         f"origem, transformacao e destino.",
            base_legal=base_legal, arquivo=rel, linha=1))
    return findings
