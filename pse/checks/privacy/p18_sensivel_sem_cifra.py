"""P-18 — dado sensivel no banco em texto claro.

P-06 pergunta se a chave de pseudonimizacao esta segregada; ele so aparece
quando ja HA cifra. Este pergunta o passo anterior, que ninguem faz: **tem
cifra?** Um campo `class: sensitive` gravado em claro esta legivel para o
dump de backup, para a replica de leitura, para o DBA com SELECT e para o
proximo S-14 que alguem escrever.

A cifra tem de ser de APLICACAO. Criptografia de disco (`at rest` do
provedor) protege contra o roubo do disco fisico, que nao e o cenario real:
protege contra ninguem que ja tenha uma conexao ao banco. O dado precisa
chegar cifrado ao banco para que o banco nao possa le-lo.

E a chave tem de ser GERENCIADA fora da aplicacao. Cifrar com chave que o
proprio processo guarda nao protege de um dump: o dump leva a chave junto,
ou ela esta no mesmo repositorio — que e exatamente o achado de P-06. A
gerencia e metade do controle, nao um detalhe operacional.

DOIS CAMINHOS PARA O VERDE (D-08), porque as duas formas sao corretas:
  - o CATALOGO declara `encryption` com `key_management` apontando para um
    gerenciador (KMS, Vault, HSM);
  - o CODIGO aplica uma cifra de aplicacao ao campo. Quem cifra e nao
    declarou ja protegeu o dado — o problema restante e de declaracao, e
    disso cuida P-04.

Sem catalogo nao ha o que confrontar: SkipCheck, com a ausencia cobrada por
P-04. Nunca CheckIndeterminado aqui — a pre-condicao declarativa simplesmente
nao existe, e essa e a definicao de N/A declarado.
"""
import ast

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

BASE = "LGPD Art. 46 + Art. 11 (dado sensivel)"
REGUA = "backend-infra"


def _r(ctx, chave):
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def _campos_cifrados_no_codigo(ctx) -> set:
    """Campos que passam por uma cifra de aplicacao — o FATO, pela AST."""
    marcas = _r(ctx, "cifra_de_aplicacao")
    cifrados = set()
    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        for no, nome in scan.chamadas(arvore):
            if not scan.nome_casa(nome, marcas):
                continue
            for arg in list(no.args) + [k.value for k in no.keywords]:
                for sub in ast.walk(arg):
                    if isinstance(sub, ast.Name):
                        cifrados.add(sub.id.lower())
                    elif isinstance(sub, ast.Attribute):
                        cifrados.add(sub.attr.lower())
                    elif isinstance(sub, ast.Constant) and isinstance(
                            sub.value, str):
                        cifrados.add(sub.value.lower())
    return cifrados


def _cifra_declarada(props: dict, chaves_cifra) -> dict | None:
    for chave in chaves_cifra:
        valor = props.get(chave)
        if isinstance(valor, dict):
            return valor
        if valor is True:
            return {}
    return None


def _gerencia(cifra: dict, chaves_gerencia, gerenciadores) -> str | None:
    for chave in chaves_gerencia:
        valor = cifra.get(chave)
        if not valor:
            continue
        baixo = str(valor).lower()
        if any(g in baixo for g in gerenciadores):
            return str(valor)
    return None


@check("P-18", "privacy", "Sensivel sem cifra de aplicacao", base_legal=BASE)
def sensivel_sem_cifra(ctx):
    cat = ctx.catalog()
    if cat is None:
        raise SkipCheck("catalogo de dados ausente — cobrado por P-04; sem "
                        "inventario nao ha campo sensivel a confrontar")

    sensiveis_da_regua = {t.lower() for t in ctx.data["sensitive-fields"]["sensiveis"]}
    chaves_cifra = _r(ctx, "chaves_de_cifra")
    chaves_gerencia = _r(ctx, "chaves_de_gerencia")
    gerenciadores = _r(ctx, "gerenciadores_de_chave")
    cifrados_no_codigo = _campos_cifrados_no_codigo(ctx)
    findings = []

    for tabela, tmeta in sorted((cat.get("tables") or {}).items()):
        for campo, props in sorted(((tmeta or {}).get("fields") or {}).items()):
            props = props or {}
            baixo = str(campo).lower()
            if props.get("class") != "sensitive" and baixo not in sensiveis_da_regua:
                continue
            if baixo in cifrados_no_codigo:
                continue                 # D-08: a cifra EXECUTA sobre o campo

            cifra = _cifra_declarada(props, chaves_cifra)
            if cifra is not None and _gerencia(cifra, chaves_gerencia,
                                               gerenciadores):
                continue                 # D-08: cifra com chave gerenciada

            if cifra is None:
                falta = (
                    "o catalogo nao declara cifra nenhuma para ele, e nao ha "
                    "chamada de cifra de aplicacao sobre o campo no codigo")
                recomendacao = (
                    "Cifrar na APLICACAO, com chave em KMS/Vault/HSM, e "
                    "declarar `encryption: {algorithm, key_management}` no "
                    "catalogo. Criptografia de disco do provedor nao resolve: "
                    "ela protege contra o roubo do disco fisico, e nao contra "
                    "quem ja tem uma conexao ao banco.")
            else:
                falta = (
                    "ha cifra declarada, mas sem gerencia de chave: nenhum "
                    "`key_management` aponta para KMS, Vault ou HSM. Chave que "
                    "a propria aplicacao guarda nao protege de um dump — o "
                    "dump leva a chave junto, que e o achado de P-06")
                recomendacao = (
                    "Mover a chave para um gerenciador externo e declarar "
                    "`key_management` no catalogo. A gerencia e metade do "
                    "controle, nao um detalhe operacional.")

            findings.append(Finding(
                check_id="P-18", pack="privacy", severidade=Severidade.ALTO,
                titulo=f"Campo sensivel {tabela}.{campo} sem cifra de aplicacao "
                       f"com chave gerenciada",
                descricao=(
                    f"O campo e sensivel (Art. 11) e {falta}. Em texto claro no "
                    f"banco, ele esta legivel para o backup, para a replica de "
                    f"leitura, para quem tiver SELECT na tabela e para qualquer "
                    f"restauracao em ambiente inferior (S-14)."),
                recomendacao=recomendacao,
                base_legal=BASE, arquivo=ctx.catalog_path(),
                linha=ctx.linha_no_catalogo("tables", tabela, "fields", campo)))
    return findings
