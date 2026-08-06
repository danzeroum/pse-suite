"""P-02 — retencao declarada no catalogo sem job de eliminacao.

ANCORA NO FATO (D-01): o que satisfaz este check e um job de purga que
EXECUTA — funcao de expurgo cujo corpo apaga de verdade. Em 1eb616b bastava
a palavra 'purge' num comentario, ou um nome de arquivo, para o check passar.
Declarar retencao no catalogo nao e implementar a purga; citar a purga num
comentario, menos ainda.
"""
import ast
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

RX_PURGA = re.compile(r"purg|expurg|retencao|retention|cleanup|expira", re.I)
RX_APAGA = re.compile(r"\b(delete|drop|purge|expurg|remove|destroy|truncate)\b", re.I)
RX_SQL_APAGA = re.compile(r"\b(DELETE\s+FROM|TRUNCATE|DROP\s+TABLE)\b", re.I)


def _apaga_de_verdade(fn: ast.AST) -> bool:
    """A funcao executa uma eliminacao? Chamada com nome de exclusao, ou
    comando SQL de exclusao passado como argumento de uma chamada."""
    for no, nome in scan.chamadas(fn):
        if RX_APAGA.search(nome.split(".")[-1]):
            return True
        for arg in no.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) \
                    and RX_SQL_APAGA.search(arg.value):
                return True
    return False


def _job_de_purga(ctx) -> bool:
    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)      # SyntaxError -> CheckIndeterminado
        for no in ast.walk(arvore):
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and RX_PURGA.search(no.name) and _apaga_de_verdade(no):
                return True
    # Job fora do Python: script/SQL cujo NOME indica purga e que contem um
    # comando de exclusao real (fora de comentario).
    for p in scan.arquivos(ctx.repo, {".sql", ".sh"}):
        if RX_PURGA.search(p.name) and RX_SQL_APAGA.search(
                scan.codigo_efetivo(scan.ler(p), p.suffix)):
            return True
    return False


@check("P-02", "privacy", "Retencao declarada sem job de purga", base_legal="LGPD Art. 15-16")
def retencao(ctx):
    cat = ctx.catalog()
    if cat is None:
        raise SkipCheck("catalogo de dados ausente — cobrado por P-04")
    declara = any(
        (props or {}).get("retention_years")
        for t in (cat.get("tables") or {}).values()
        for props in ((t or {}).get("fields") or {}).values())
    if not declara:
        raise SkipCheck("nenhum campo declara retention_years no catalogo")
    if _job_de_purga(ctx):
        return []
    return [Finding(
        check_id="P-02", pack="privacy", severidade=Severidade.ALTO,
        titulo="Retencao declarada no catalogo sem job de eliminacao",
        descricao="O catalogo declara prazos de retencao, mas nao existe job "
                  "de purga que execute uma eliminacao — dados serao mantidos "
                  "alem do termino da finalidade.",
        recomendacao="Implementar job periodico que elimine dados expirados e "
                     "registre evidencia de eliminacao para auditoria.",
        base_legal="LGPD Art. 15-16",
        arquivo=ctx.config.get("catalog_path", "tests/qa/catalog.yaml"))]
