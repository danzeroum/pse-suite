"""S-16 — residencia de dados no ponto de ESCRITA, nao no de egresso.

S-08 le o manifesto de terceiros e pergunta se ha base de transferencia
para o que o consumidor DECLAROU que sai. Parente proximo, e nao substituto:
o manifesto so cobre o que alguem se lembrou de registrar como integracao.

Um bucket em `us-east-1` nao e integracao com ninguem. E infraestrutura
propria, criada num terraform apply de terca-feira, e nao aparece em
manifesto nenhum — mas o dado do titular brasileiro pousa fisicamente nos
Estados Unidos do mesmo jeito, e o Art. 33 nao pergunta se o destino era um
parceiro ou o seu proprio disco.

Este check confronta a POLITICA declarada com o ponto onde o byte pousa: a
regiao literal que a chamada de persistencia carrega, seja em `region_name`,
seja embutida no host de uma connection string.

SEM POLITICA DECLARADA, SkipCheck. Supor `BR` porque a LGPD e brasileira
seria a suite decidindo pelo consumidor uma coisa que e dele — ha operacao
legitima com residencia europeia, e um achado inventado destroi a confianca
mais rapido do que um achado ausente.

D-01: `# migrar para us-east-1 no Q4` nao move nada. A regiao e lida de
literal que participa de uma CHAMADA de persistencia, na AST — comentario
nao chega la.
"""
import ast

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

BASE = "LGPD Art. 33 (transferencia internacional)"
REGUA = "backend-infra"


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _declarada(ctx) -> str | None:
    """A politica pode vir da config do consumidor ou do manifesto."""
    for chave in _r(ctx, "chaves_de_residencia"):
        valor = ctx.config.get(chave)
        if valor:
            return str(valor).strip().upper()
    manifesto = ctx.manifest_terceiros() or {}
    for chave in _r(ctx, "chaves_de_residencia"):
        valor = manifesto.get(chave)
        if valor:
            return str(valor).strip().upper()
    return None


def _mapa_de_regioes(ctx) -> dict:
    """{regiao_em_minusculas: jurisdicao}."""
    return {str(r).lower(): juris
            for juris, regioes in _r(ctx, "regioes").items()
            for r in regioes}


def _regiao_no_texto(texto: str, mapa: dict):
    baixo = str(texto).lower()
    # A mais longa primeiro: `us-east-1` antes de `us-east`, para o achado
    # nomear a regiao inteira em vez de um prefixo.
    for regiao in sorted(mapa, key=len, reverse=True):
        if regiao in baixo:
            return regiao, mapa[regiao]
    return None, None


@check("S-16", "security", "Persistencia fora da residencia declarada",
       base_legal=BASE)
def residencia_na_escrita(ctx):
    politica = _declarada(ctx)
    if not politica:
        raise SkipCheck(
            "nenhuma politica de residencia de dados declarada (`data_residency` "
            "na config ou no manifesto) — sem promessa nao ha o que confrontar, "
            "e supor uma jurisdicao seria a suite decidindo pelo consumidor")

    mapa = _mapa_de_regioes(ctx)
    persistencia = [str(t).lower() for t in _r(ctx, "chamadas_de_persistencia")]
    findings, vistos = [], set()

    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        rel = scan.rel(ctx.repo, p)
        linhas = scan.ler(p).splitlines()

        for no, nome in scan.chamadas(arvore):
            if not scan.nome_casa(nome, persistencia):
                continue
            for arg in list(no.args) + [k.value for k in no.keywords]:
                for sub in ast.walk(arg):
                    if not (isinstance(sub, ast.Constant)
                            and isinstance(sub.value, str)):
                        continue
                    regiao, juris = _regiao_no_texto(sub.value, mapa)
                    if not regiao or juris == politica:
                        continue
                    linha = no.lineno
                    chave = (rel, linha, regiao)
                    if chave in vistos:
                        continue
                    vistos.add(chave)
                    findings.append(Finding(
                        check_id="S-16", pack="security",
                        severidade=Severidade.ALTO,
                        titulo=f"Persistencia em `{regiao}` ({juris}) com "
                               f"residencia declarada {politica}",
                        descricao=(
                            f"A chamada `{nome}` grava numa regiao de "
                            f"jurisdicao {juris}, e a politica do consumidor "
                            f"declara residencia {politica}. Isto nao passa "
                            f"pelo manifesto de terceiros que S-08 audita: nao "
                            f"e integracao com parceiro nenhum, e "
                            f"infraestrutura propria criada num apply de "
                            f"terca-feira. O Art. 33 nao pergunta se o destino "
                            f"era um terceiro ou o seu proprio disco."),
                        recomendacao=(
                            f"Mover o recurso para uma regiao de {politica}, ou "
                            f"— se a transferencia for necessaria — declarar a "
                            f"base do Art. 33 (clausulas-padrao, adequacao, "
                            f"consentimento especifico) e registrar o destino "
                            f"no manifesto, para que S-08 tambem o audite."),
                        base_legal=BASE, arquivo=rel, linha=linha,
                        snippet=(linhas[linha - 1].strip()[:200]
                                 if linha <= len(linhas) else None)))
    return findings
