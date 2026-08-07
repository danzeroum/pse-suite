"""E-12 — embedding/hash exportado como se fosse anonimo.

O erro que este check ataca tem uma frase-tipo: "nao e dado pessoal, e so o
hash" — ou "so o embedding". Nao e verdade. Um derivado deterministico
continua ligando de volta ao titular (rainbow, linkagem, inversao de
embedding), e a Art. 12 so trata como anonimo o que for irreversivel por
meios razoaveis. O que revela a crenca errada nao e o codigo do export: e a
AUSENCIA do campo de origem no catalogo como pessoal.

Por isso a pergunta do check nao e "voce exporta derivados?", e sim
"**voce reconhece a origem como dado pessoal?**". Se o catalogo diz que o
campo de origem e personal/sensitive, a organizacao ja assumiu o que ele e,
e o resto e P-04/S-05. Se nao diz nada, o derivado esta saindo sob uma
alegacao de anonimato que ninguem registrou.

Sem catalogo: indeterminado. Nao da para saber se a origem e pessoal, e
"nao sei" nunca degrada para verde.
"""
import ast
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import CheckIndeterminado, Finding, Severidade, SkipCheck

BASE_LEGAL = "LGPD Art. 12 + Art. 42 (responsabilidade solidaria)"

# O derivado: o que se calcula a partir do dado e se acredita anonimizar.
RX_DERIVADO = re.compile(
    r"embedding|embeddings|vetor|vector|hash|digest|sha\d|hmac|fingerprint|"
    r"impressao|assinatura|token_derivado|pseudo", re.I)
# A saida: o verbo que faz o derivado deixar o perimetro.
EXPORTACOES = {"send", "publish", "post", "put", "upload", "emit", "enqueue",
               "produce", "export", "sync", "track", "index", "upsert",
               "write", "ingest", "push"}
# Ruido de composicao de nome, nao campo de origem.
_LIGACOES = {"do", "da", "de", "dos", "das", "the", "of", "user", "usr",
             "obj", "item", "reg", "val", "tmp", "novo", "new"}


def _origens(identificador: str) -> list:
    """Campos candidatos a origem, extraidos do nome do derivado.

    `embedding_do_usuario` -> ['usuario'] · `hash_cpf` -> ['cpf']
    """
    partes = re.split(r"[_\W]+", identificador.lower())
    return [p for p in partes
            if p and p not in _LIGACOES and not RX_DERIVADO.fullmatch(p)
            and not RX_DERIVADO.match(p)]


def _campos_do_catalogo(cat) -> dict:
    saida = {}
    for tmeta in (cat.get("tables") or {}).values():
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            saida[str(campo).lower()] = (props or {}).get("class")
    return saida


def _derivados_exportados(arvore):
    """(no_da_chamada, identificador_derivado) para cada export de derivado."""
    for no, nome in scan.chamadas(arvore):
        if nome.split(".")[-1].lower() not in EXPORTACOES:
            continue
        for arg in list(no.args) + [k.value for k in no.keywords]:
            for sub in ast.walk(arg):
                ident = None
                if isinstance(sub, ast.Name):
                    ident = sub.id
                elif isinstance(sub, ast.Attribute):
                    ident = sub.attr
                if ident and RX_DERIVADO.search(ident):
                    yield no, ident
                    break


@check("E-12", "ethics", "Derivado tratado como anonimo", base_legal=BASE_LEGAL)
def derivado_anonimo(ctx):
    findings = []
    catalogo_cache = None

    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        linhas = scan.ler(p).splitlines()
        vistos = set()

        for no, ident in _derivados_exportados(arvore):
            if catalogo_cache is None:
                cat = ctx.catalog()
                if cat is None:
                    raise CheckIndeterminado(
                        "exportacao de derivado (embedding/hash) encontrada, mas "
                        "nao ha catalogo de dados para dizer se a origem e "
                        "pessoal — sem inventario a alegacao de anonimato nao e "
                        "verificavel (catalogo cobrado por P-04)")
                catalogo_cache = _campos_do_catalogo(cat)

            origens = _origens(ident)
            reconhecida = [o for o in origens
                           if catalogo_cache.get(o) in ("personal", "sensitive")]
            if reconhecida or not origens:
                continue
            chave = (scan.rel(ctx.repo, p), no.lineno)
            if chave in vistos:
                continue
            vistos.add(chave)
            i = no.lineno
            findings.append(Finding(
                check_id="E-12", pack="ethics", severidade=Severidade.ALTO,
                titulo=f"Derivado '{ident}' exportado sem origem reconhecida "
                       f"como dado pessoal",
                descricao=f"O derivado sai do perimetro e o catalogo nao "
                          f"classifica {origens} como personal/sensitive. Hash e "
                          f"embedding nao anonimizam: continuam ligando ao "
                          f"titular por linkagem ou inversao, e so e anonimo o "
                          f"que for irreversivel por meios razoaveis (Art. 12). "
                          f"O silencio do catalogo aqui e a alegacao de "
                          f"anonimato que ninguem assinou.",
                recomendacao="Classificar o campo de origem no catalogo como "
                             "personal/sensitive e tratar o derivado como dado "
                             "pessoal (base legal, retencao, egresso declarado) "
                             "— ou provar a irreversibilidade e registrar a prova.",
                base_legal=BASE_LEGAL,
                arquivo=scan.rel(ctx.repo, p), linha=i,
                snippet=linhas[i - 1].strip()[:200] if i <= len(linhas) else None))
    if findings or catalogo_cache is not None:
        return findings
    raise SkipCheck("nenhuma exportacao de embedding/hash derivado no codigo")
