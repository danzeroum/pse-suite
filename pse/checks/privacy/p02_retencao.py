import re
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

RX_PURGA = re.compile(r"retencao|retention|purge|cleanup|expira", re.I)


@check("P-02", "privacy", "Retencao declarada sem job de purga", base_legal="LGPD Art. 15-16")
def retencao(ctx):
    cat = ctx.catalog()
    if cat is None:
        raise SkipCheck("catalogo de dados ausente — cobrado por P-04")
    declara = any(
        (props or {}).get("retention_years")
        for t in (cat.get("tables") or {}).values()
        for props in (t.get("fields") or {}).values())
    if not declara:
        raise SkipCheck("nenhum campo declara retention_years no catalogo")
    catalogo_path = ctx.repo / ctx.config.get("catalog_path", "tests/qa/catalog.yaml")
    for p in scan.arquivos(ctx.repo, {".py", ".sql", ".sh"}):
        if p == catalogo_path:
            continue  # declarar retencao no catalogo nao e implementar a purga
        if RX_PURGA.search(p.name) or RX_PURGA.search(scan.ler(p)[:5000]):
            return []
    return [Finding(
        check_id="P-02", pack="privacy", severidade=Severidade.ALTO,
        titulo="Retencao declarada no catalogo sem job de eliminacao",
        descricao="O catalogo declara prazos de retencao, mas nao ha job/script "
                  "de purga — dados serao mantidos alem do termino da finalidade.",
        recomendacao="Implementar job periodico que elimine dados expirados e "
                     "registre evidencia de eliminacao para auditoria.",
        base_legal="LGPD Art. 15-16")]
