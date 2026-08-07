"""P-20 — o "anonimo" que nao e anonimo.

E o buraco mais perigoso do estrato de dados justamente por parecer
resolvido. Um time grava `sha256(cpf)` numa coluna chamada `id_anonimo`,
marca o campo como `class: anonymized` no catalogo, e passa a tratar aquela
tabela como fora do alcance da lei: sem retencao, sem base legal, sem
direito de eliminacao, exportada para o data lake e para o parceiro.

O CPF tem cerca de 10^11 valores validos. Construir o dicionario completo
de SHA-256 sobre esse espaco leva segundos num laptop — o "anonimo" e uma
tabela de-para que qualquer pessoa remonta. E-mail e pior: o espaco util e
uma lista que se compra pronta. O Art. 12 so dispensa o dado que nao possa
ser revertido **por meios razoaveis e disponiveis**, e um `for` sobre onze
digitos e o mais razoavel e disponivel dos meios.

POR QUE NENHUM DOS 48 ANTERIORES PEGA ISTO:
  P-06 audita onde a chave mora — aqui nao HA chave.
  P-18 audita a ausencia de cifra — aqui alguem "cifrou", no sentido
       errado da palavra.
  P-09 audita a agregacao — este dado nao e agregado, e por linha.
  E-12 audita o derivado exportado como anonimo — olha o embedding, nao a
       coluna do warehouse.

O FATO (AST): uma funcao de digest DETERMINISTICO E SEM SEGREDO aplicada a
um campo de PII, cujo resultado alcanca uma escrita ou uma exportacao. As
tres condicoes sao necessarias — hash em memoria que nao e guardado nao e
dado, e hash de conteudo de arquivo nao toca titular nenhum.

D-08, e aqui ele e critico porque o caso correto e o que P-06 VALIDA:
  - `hmac.new(chave_do_vault(...), cpf, sha256)` nao dispara. Punir HMAC
    seria a suite contradizendo a si mesma e dando achado a quem acertou.
  - sal aleatorio por registro (`secrets.token_bytes`, `os.urandom`,
    `uuid4`) nao dispara: sem determinismo nao ha ligacao entre duas
    ocorrencias do mesmo titular, que e exatamente o que o hash nu preserva.
  - `key=`/`salt=` como argumento nomeado nao dispara.
  - KDF (`pbkdf2_hmac`, `scrypt`, `bcrypt`, `argon2`) nao dispara.

FORA DE ESCOPO POR CONSTRUCAO: o grupo `credenciais` da regua de PII.
Hashear senha e o que se DEVE fazer; o defeito ali seria a ausencia de KDF,
que e outro assunto. P-20 e sobre IDENTIFICADOR tratado como anonimo, nao
sobre segredo.

SEVERIDADE CONDICIONAL, mesmo principio ratificado em P-15: campo sensivel
-> CRITICO, pessoal comum -> ALTO. Biometria com hash nu e o pior caso
concebivel — e irreversibilidade de mentira sobre o dado mais irreversivel
que existe, porque a pessoa nao troca de digital depois do vazamento.
"""
import ast

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

BASE = "LGPD Art. 12 (dado anonimizado) + Art. 6o"
BASE_SENSIVEL = "LGPD Art. 11 (dado sensivel exige hipotese propria)"
REGUA = "anonimizacao"


def _r(ctx, chave):
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def _identificadores(ctx) -> set:
    """PII que IDENTIFICA — sem o grupo `credenciais`.

    Hashear senha e correto; incluir `password` aqui faria P-20 acusar
    exatamente a pratica que ele nao tem nada a ver, e o time aprenderia a
    ignorar o check no primeiro dia.
    """
    pii = ctx.data["pii-patterns"]
    campos = set()
    for grupo, termos in pii.items():
        if grupo == "credenciais":
            continue
        campos |= {str(t).lower() for t in termos}
    return campos


def _sensiveis(ctx) -> set:
    return {str(t).lower() for t in ctx.data["sensitive-fields"]["sensiveis"]}


def _classes_do_catalogo(ctx) -> dict:
    """{campo: classe} — a DECLARACAO que o check confronta."""
    cat = ctx.catalog()
    saida = {}
    for tmeta in ((cat or {}).get("tables") or {}).values():
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            saida[str(campo).lower()] = str((props or {}).get("class") or "").lower()
    return saida


def _e_hash_nu(no, ctx) -> str | None:
    """Nome do digest, se a chamada e deterministica E sem segredo."""
    nome = scan.nome_chamado(no)
    ultimo = nome.split(".")[-1].lower()
    if ultimo not in _r(ctx, "hashes_sem_chave"):
        return None
    # `hashlib.new("sha256", x)` sem mais nada continua sendo nu; com `key=`
    # deixa de ser (blake2 aceita chave).
    com_chave = _r(ctx, "argumentos_com_chave")
    if any((k.arg or "").lower() in com_chave for k in no.keywords):
        return None
    return ultimo


def _nomes_aleatorios(escopo, ctx) -> set:
    """Variaveis que receberam aleatoriedade neste escopo.

    O sal quase nunca esta DENTRO da chamada de hash: escreve-se
    `sal = secrets.token_bytes(16)` numa linha e `sha256(sal + cpf)` na
    seguinte. Sem seguir esse salto, o check acusaria justamente o pipeline
    que faz a coisa certa — que e a pior falha possivel para D-08.
    """
    fontes = _r(ctx, "fontes_de_sal")
    nomes = set()
    for no in ast.walk(escopo):
        if not isinstance(no, (ast.Assign, ast.AnnAssign)) or no.value is None:
            continue
        veio_do_acaso = any(
            any(p in fontes for p in scan.nome_chamado(sub).lower().split("."))
            for sub in ast.walk(no.value) if isinstance(sub, ast.Call))
        if not veio_do_acaso:
            continue
        alvos = no.targets if isinstance(no, ast.Assign) else [no.target]
        for alvo in alvos:
            for sub in ast.walk(alvo):
                if isinstance(sub, ast.Name):
                    nomes.add(sub.id)
    return nomes


def _tem_segredo_ou_sal(no, ctx, aleatorios: set) -> bool:
    """A expressao quebra o determinismo ou traz chave?"""
    com_chave = _r(ctx, "construcoes_com_chave")
    sal = _r(ctx, "fontes_de_sal")
    for sub in ast.walk(no):
        if isinstance(sub, ast.Call):
            partes = scan.nome_chamado(sub).lower().split(".")
            if any(p in com_chave for p in partes) or any(p in sal for p in partes):
                return True
        elif isinstance(sub, ast.Name) and sub.id in aleatorios:
            return True
    return False


def _campo_hasheado(no, identificadores: set, sensiveis: set,
                    do_catalogo: dict):
    """Qual campo de PII entra no digest — o argumento, nao o nome da coluna."""
    for sub in ast.walk(no):
        nome = None
        if isinstance(sub, ast.Attribute):
            nome = sub.attr
        elif isinstance(sub, ast.Name):
            nome = sub.id
        elif isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            nome = sub.value
        if not nome:
            continue
        baixo = nome.lower()
        if baixo in sensiveis or do_catalogo.get(baixo) == "sensitive":
            return baixo, True
        if baixo in identificadores or do_catalogo.get(baixo) in ("personal",):
            return baixo, False
    return None, False


def _sinks(ctx) -> set:
    return set(_r(ctx, "verbos_de_persistencia")) | set(_r(ctx, "verbos_de_exportacao"))


def _guardado(escopo, alvo_call, sinks: set) -> tuple:
    """(True, nome_do_sink) se o digest alcanca uma escrita ou exportacao.

    Rastreio curto e honesto, do mesmo feitio de S-11: aninhamento direto e
    UM salto de variavel, dentro do escopo. Nao promete interprocedural.
    """
    # 1. aninhado direto no sink
    for sub, nome in scan.chamadas(escopo):
        if nome.split(".")[-1].lower() not in sinks:
            continue
        for dentro in ast.walk(sub):
            if dentro is alvo_call:
                return True, nome

    # 2. um salto: `h = sha256(...)` ... `db.insert(..., h, ...)`
    nomes = set()
    for no in ast.walk(escopo):
        if not isinstance(no, ast.Assign):
            continue
        if not any(d is alvo_call for d in ast.walk(no.value)):
            continue
        for alvo in no.targets:
            for sub in ast.walk(alvo):
                if isinstance(sub, ast.Name):
                    nomes.add(sub.id)
    if not nomes:
        return False, None
    for sub, nome in scan.chamadas(escopo):
        if nome.split(".")[-1].lower() not in sinks:
            continue
        for dentro in ast.walk(sub):
            if isinstance(dentro, ast.Name) and dentro.id in nomes:
                return True, nome
    return False, None


@check("P-20", "privacy", "Hash sem chave como anonimizacao", base_legal=BASE)
def hash_como_anonimizacao(ctx):
    identificadores = _identificadores(ctx)
    sensiveis = _sensiveis(ctx)
    do_catalogo = _classes_do_catalogo(ctx)
    classes_anonimo = _r(ctx, "classes_de_anonimato")
    sinks = _sinks(ctx)
    declarado_anonimo = {c for c, klass in do_catalogo.items()
                         if klass in classes_anonimo}
    findings, vistos = [], set()

    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        rel = scan.rel(ctx.repo, p)
        linhas = scan.ler(p).splitlines()
        escopos = [n for n in ast.walk(arvore)
                   if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        escopos.append(arvore)

        for escopo in escopos:
            aleatorios = _nomes_aleatorios(escopo, ctx)
            for no, _ in scan.chamadas(escopo):
                digest = _e_hash_nu(no, ctx)
                if not digest:
                    continue
                if _tem_segredo_ou_sal(no, ctx, aleatorios):
                    continue             # D-08: HMAC, KDF ou sal aleatorio
                campo, sensivel = _campo_hasheado(
                    no, identificadores, sensiveis, do_catalogo)
                if not campo:
                    continue             # checksum de conteudo, cache key
                guardado, sink = _guardado(escopo, no, sinks)
                if not guardado:
                    continue             # digest que nao vira dado guardado

                chave = (rel, no.lineno, campo)
                if chave in vistos:
                    continue
                vistos.add(chave)

                # Mesmo principio ratificado em P-15: Art. 11 e trava
                # estrutural, nao gradiente.
                severidade = (Severidade.CRITICO if sensivel
                              else Severidade.ALTO)
                base = f"{BASE} + {BASE_SENSIVEL}" if sensivel else BASE
                extra = ""
                if declarado_anonimo:
                    extra = (f" O catalogo ainda declara "
                             f"{sorted(declarado_anonimo)} como classe de "
                             f"dado ANONIMO — e essa declaracao que retira o "
                             f"dado da retencao, da base legal e do direito "
                             f"de eliminacao.")
                if sensivel:
                    extra += (" O campo e SENSIVEL: irreversibilidade de "
                              "mentira sobre biometria ou saude e o pior caso "
                              "concebivel, porque o titular nao troca de "
                              "digital depois do vazamento.")

                i = no.lineno
                findings.append(Finding(
                    check_id="P-20", pack="privacy", severidade=severidade,
                    titulo=f"`{digest}` sem chave sobre '{campo}' e guardado "
                           f"em `{sink}`",
                    descricao=(
                        f"O digest e DETERMINISTICO e SEM SEGREDO: o mesmo "
                        f"valor de '{campo}' produz o mesmo resultado em "
                        f"qualquer maquina, sempre. Isto nao anonimiza — "
                        f"pseudonimiza sem guardar a chave, que e o pior dos "
                        f"dois mundos. O espaco de um identificador nacional "
                        f"e pequeno o bastante para um dicionario completo ser "
                        f"construido em segundos, e o Art. 12 so dispensa o "
                        f"dado que nao possa ser revertido por meios razoaveis "
                        f"e disponiveis.{extra}"),
                    recomendacao=(
                        "HMAC com chave em cofre (KMS/Vault) — quem nao tem a "
                        "chave nao remonta o de-para, e destruir a chave torna "
                        "a eliminacao real. Ou sal aleatorio por registro, se "
                        "a ligacao entre ocorrencias nao for necessaria. E, "
                        "enquanto houver qualquer forma de reverter, o campo "
                        "continua sendo dado PESSOAL no catalogo: "
                        "pseudonimizado nao e anonimizado."),
                    base_legal=base, arquivo=rel, linha=i,
                    snippet=(linhas[i - 1].strip()[:200]
                             if i <= len(linhas) else None)))
    return findings
