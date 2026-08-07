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

ALCANCE A RUST (textual, ancorado, sem parser), e ele faz DUAS coisas
distintas:

  SUPRESSAO (D-08). Uma chamada de cifra num `.rs` sobre o campo conta
  igual a uma em Python. Sem isso, um consumidor cujo motor Rust cifra de
  verdade seria punido por o catalogo nao declarar — punir quem protegeu.

  DETECCAO DO VAO. O caso que so o Rust revela: o catalogo declara
  `encryption` com `key_management` — entao o braco declarativo fica quieto
  — e o motor grava o campo EM CLARO mesmo assim. Declaracao e fato
  divergindo e a coisa que esta suite inteira existe para achar, e aqui ela
  so aparece porque o `.rs` passou a ser lido.

  O braco Rust NAO duplica o achado declarativo: ele so fala de campo que o
  catalogo ja deu por cifrado. Dois achados para o mesmo campo seriam ruido,
  e ruido ensina o time a ignorar o pack.
"""
import ast

from pse.checks import _rust
from pse.engine import rustscan, scan
from pse.engine.registry import check
from pse.model import CheckIndeterminado, Finding, Severidade, SkipCheck

BASE = "LGPD Art. 46 + Art. 11 (dado sensivel)"
REGUA = "backend-infra"


def _r(ctx, chave):
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def _cifras_de_rust(ctx) -> list:
    return _r(ctx, "cifra_de_aplicacao") + _rust.r_baixo(ctx, "cifra_de_aplicacao")


def _campos_cifrados_em_rust(ctx, candidatos: set) -> set:
    """Campos que aparecem no span de argumento de uma chamada de cifra.

    Sem arvore nao se sabe QUAL argumento e o campo — entao a pergunta e
    feita ao contrario: dos campos que o catalogo declarou, quais aparecem
    dentro de uma chamada de cifra? Restringir aos candidatos e o que
    impede o span de virar um saco de palavras.
    """
    marcas = _cifras_de_rust(ctx)
    cifrados = set()
    for _, texto in _rust.arquivos(ctx):
        for ch in rustscan.chamadas(texto):
            if not scan.nome_casa_tokens(ch.nome.replace("::", "."), marcas):
                continue
            cifrados |= set(rustscan.tokens_presentes(ch.args, candidatos))
    return cifrados


def _e_escrita(ctx, nome: str, args: str) -> bool:
    """Este span PERSISTE alguma coisa, ou so le?

    P-18 pergunta se um campo sensivel e GRAVADO sem cifra. Um `SELECT` nao
    grava nada, e acusa-lo seria um achado que o time nao consegue corrigir.

    A ORDEM E O QUE FAZ ISTO FUNCIONAR, e a triagem do btv provou por que:
    `sqlx::query_scalar("INSERT INTO users (..., email, ...)")` tem NOME de
    leitura e faz ESCRITA. Uma lista de nomes proibidos, sozinha, produziria
    falso-NEGATIVO no site que mais importa. Entao o SQL vence o nome.
    """
    baixo = " ".join(str(args).lower().split())
    if any(d in baixo for d in _rust.r_baixo(ctx, "ddl_de_credencial_de_banco")):
        return False                 # credencial de BANCO: assunto de S-15
    if any(v in baixo for v in _rust.r_baixo(ctx, "verbos_sql_de_escrita")):
        return True                  # o SQL manda, mesmo com nome de leitura
    if any(v in baixo for v in _rust.r_baixo(ctx, "verbos_sql_de_leitura")):
        return False
    return not scan.nome_casa_tokens(
        nome.replace("::", "."), _rust.r_baixo(ctx, "leituras_de_persistencia"))


def _escritas_em_rust(ctx, candidatos: set) -> dict:
    """{campo: (arquivo, chamada)} — onde um campo do catalogo e persistido.

    A ancora e a chamada de persistencia; o campo e procurado no span de
    argumento dela, e so entre os campos que o catalogo ja declarou. Uma
    chamada que aplique cifra no proprio span nao conta como escrita em
    claro. E leitura nao conta como escrita — ver `_e_escrita`.
    """
    persistencia = _rust.r_baixo(ctx, "persistencia") + \
        [str(t).lower() for t in ctx.data[REGUA]["chamadas_de_persistencia"]] + \
        ["execute", "query", "bind", "insert", "save", "put_item", "fetch_one",
         "query_as", "create"]
    cifras = _cifras_de_rust(ctx)
    saida, ambiguos = {}, {}
    for p, texto in _rust.arquivos(ctx):
        linhas = texto.splitlines()
        for ch in rustscan.chamadas(texto):
            if not scan.nome_casa_tokens(ch.nome.replace("::", "."), persistencia):
                continue
            if rustscan.contem_token(ch.args, cifras):
                continue
            if not _e_escrita(ctx, ch.nome, ch.args):
                continue
            # O campo aparece no SQL, mas o VALOR ligado e opaco?
            #
            # `query("INSERT INTO t (cpf) ...").bind(&blob)` — o nome da
            # coluna esta no literal e o valor vem de `blob`, que saiu de
            # uma funcao que a regua nao reconhece como cifra. Pode ser um
            # embrulho de cifra da casa (`to_ciphertext`) ou pode ser o
            # campo cru renomeado. Sem arvore nao ha como saber, e a regua
            # nao e editavel pelo consumidor — entao inventar achado puniria
            # quem cifrou, e inventar verde absolveria quem nao cifrou.
            #
            # Terceira saida, a mesma de `env!` em S-06: indeterminado com
            # motivo. Quando o campo aparece FORA do literal (`.bind(&t.cpf)`),
            # nao ha ambiguidade — o valor cru esta ali, e vira achado.
            fora_do_literal = set(rustscan.tokens_presentes(
                rustscan.efetivo(ch.args, sem_literais=True), candidatos))
            for campo in rustscan.tokens_presentes(ch.args, candidatos):
                if campo in fora_do_literal:
                    saida.setdefault(campo, (p, ch, linhas))
                else:
                    ambiguos.setdefault(campo, (p, ch))
    if ambiguos and not saida:
        campo, (p, ch) = sorted(ambiguos.items())[0]
        raise CheckIndeterminado(
            f"{scan.rel(ctx.repo, p)}:{ch.linha} — `{ch.nome}` grava a coluna "
            f"`{campo}` mas o valor ligado nao e o campo cru: ele vem de um "
            f"identificador que a regua nao reconhece como cifra. Pode ser um "
            f"embrulho de cifra da casa ou o campo renomeado, e o alcance "
            f"textual a Rust nao tem como decidir. Aplicar uma cifra "
            f"reconhecida (`aes_gcm`, `chacha20poly1305`, `ring::aead`) — ou "
            f"ligar o campo cru, se for esse o caso — torna o site decidivel.")
    return saida


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
    campos_do_catalogo = {
        str(campo).lower()
        for tmeta in (cat.get("tables") or {}).values()
        for campo in ((tmeta or {}).get("fields") or {})}
    # D-08 em Rust, e ele vale para o catalogo INTEIRO, nao so para o vao:
    # um consumidor cujo motor cifra de verdade nao pode ser punido por o
    # catalogo nao declarar. Punir quem protegeu e o pior sinal que uma
    # suite pode mandar.
    cifrados_no_codigo = _campos_cifrados_no_codigo(ctx) | \
        _campos_cifrados_em_rust(ctx, campos_do_catalogo)
    findings, declarados_cifrados = [], {}

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
                # D-08: cifra com chave gerenciada. O braco declarativo esta
                # satisfeito — e e exatamente aqui que o braco Rust entra,
                # para perguntar se o motor cumpre o que o catalogo promete.
                declarados_cifrados[baixo] = (tabela, campo)
                continue

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

    return findings + _o_vao_entre_declaracao_e_motor(
        ctx, declarados_cifrados, cifrados_no_codigo)


def _o_vao_entre_declaracao_e_motor(ctx, declarados: dict,
                                    cifrados_no_codigo: set) -> list:
    """Catalogo promete cifra; o motor Rust grava em claro.

    So olha campos que o braco declarativo ja deu por resolvidos, e so
    reclama se NENHUMA cifra — em Python ou em Rust — toca o campo. Precisao
    sobre recall: havendo cifra em qualquer lugar, o alcance textual nao tem
    como provar que aquela escrita especifica escapou dela.
    """
    if not declarados:
        return []
    candidatos = set(declarados) - set(cifrados_no_codigo)
    if not candidatos:
        return []

    findings = []
    for campo, (p, ch, linhas) in sorted(
            _escritas_em_rust(ctx, candidatos).items()):
        tabela, nome = declarados[campo]
        findings.append(Finding(
            check_id="P-18", pack="privacy", severidade=Severidade.ALTO,
            titulo=f"Campo sensivel {tabela}.{nome} declarado cifrado e "
                   f"gravado em claro por `{ch.nome}` (Rust)",
            descricao=(
                f"O catalogo declara `encryption` com `key_management` para "
                f"{tabela}.{nome}, e o motor persiste o campo sem que nenhuma "
                f"cifra de aplicacao toque nele — nem no `.rs`, nem no Python. "
                f"Declaracao e fato divergindo e pior que ausencia de "
                f"declaracao: quem le o catalogo confia numa protecao que nao "
                f"executa. Alcance TEXTUAL: o campo foi lido do span de "
                f"argumento da chamada, sem arvore."),
            recomendacao=(
                "Aplicar a cifra no caminho de escrita do motor (`aes_gcm`, "
                "`chacha20poly1305`, `ring::aead`) com a chave vinda do "
                "gerenciador que o catalogo ja declara — ou corrigir o "
                "catalogo, se a promessa nao for para valer."),
            base_legal=BASE, arquivo=scan.rel(ctx.repo, p), linha=ch.linha,
            snippet=(linhas[ch.linha - 1].strip()[:200]
                     if ch.linha <= len(linhas) else None)))
    return findings
