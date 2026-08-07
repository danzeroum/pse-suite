"""P-19 — o Art. 18 VI num registro que nao apaga.

Kafka, event sourcing, outbox, ledger, changelog: todos compartilham a
propriedade que os torna uteis — sao APPEND-ONLY. Escrever e barato,
reprocessar e possivel, a ordem e garantida. E apagar **nao e uma operacao
que exista**. Retencao por tempo expira o particionamento, nao o titular;
compaction preserva a ultima versao da chave, que continua sendo o dado.

Entao o pedido de eliminacao chega, o time apaga a linha do Postgres,
responde ao titular que foi eliminado — e o CPF continua em todo replay do
topico, em toda replica, em todo consumidor que materializou a projecao.
P-03 pega o soft-delete no banco relacional; este pega o registro onde nem
soft-delete existe.

A UNICA ESTRATEGIA QUE FUNCIONA e crypto-shredding: o evento vai cifrado
com uma chave por titular, e eliminar o titular destroi a chave. O evento
imutavel continua la e vira ruido — que e exatamente o que a lei pede,
porque dado que ninguem consegue ler nao e mais dado pessoal.

O FATO (AST): uma chamada de producao de evento cujo payload carrega nome
de campo de PII, num modulo que fala com um barramento. A ausencia de
crypto-shredding e verificada no REPOSITORIO inteiro — a rotina de
destruicao de chave costuma morar longe do produtor, e exigi-la no mesmo
arquivo produziria falso-positivo em toda arquitetura bem separada.

D-01: `# crypto_shred previsto para o Q3` nao destroi chave nenhuma. A
supressao le apenas codigo efetivo, sem comentario e sem literal.

D-08: payload cifrado por titular, ou repositorio com rotina de destruicao
de chave, nao dispara.
"""
import ast

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

BASE = "LGPD Art. 18 VI (eliminacao) + Art. 16"
REGUA = "backend-infra"


def _r(ctx, chave):
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def _pii(ctx) -> set:
    campos = {t.lower() for grupo in ctx.data["pii-patterns"].values() for t in grupo}
    campos |= {t.lower() for t in ctx.data["sensitive-fields"]["sensiveis"]}
    cat = ctx.catalog()
    for tmeta in ((cat or {}).get("tables") or {}).values():
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            if (props or {}).get("class") in ("personal", "sensitive"):
                campos.add(str(campo).lower())
    return campos


def _modulo_fala_com_barramento(texto: str, barramentos) -> bool:
    """Sem literal e sem comentario: a mencao ao Kafka num docstring nao
    torna o modulo um produtor."""
    efetivo = scan.codigo_efetivo(texto, ".py", sem_literais=True).lower()
    return any(b in efetivo for b in barramentos)


def _e_producao_de_evento(nome: str, produtores, barramentos,
                          modulo_barramento: bool) -> bool:
    partes = nome.lower().split(".")
    verbo = partes[-1]
    if verbo not in produtores:
        return False
    # O verbo sozinho e ambiguo (`send` de e-mail, `publish` de post). Exige
    # que o receptor seja um barramento — ou que o modulo inteiro seja um.
    receptor = ".".join(partes[:-1])
    if any(b in receptor for b in barramentos):
        return True
    return modulo_barramento


def _pii_no_payload(no, pii: set) -> list:
    achados = set()
    for arg in list(no.args) + [k.value for k in no.keywords]:
        for sub in ast.walk(arg):
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if sub.value.lower() in pii:
                    achados.add(sub.value.lower())
            elif isinstance(sub, ast.Attribute) and sub.attr.lower() in pii:
                achados.add(sub.attr.lower())
            elif isinstance(sub, ast.Name) and sub.id.lower() in pii:
                achados.add(sub.id.lower())
    return sorted(achados)


def _ha_crypto_shredding(ctx, marcas) -> bool:
    """Procurada no REPOSITORIO inteiro: a rotina de destruicao de chave
    quase nunca mora ao lado do produtor, e exigi-la no mesmo arquivo
    reprovaria toda arquitetura bem separada."""
    for p in scan.arquivos(ctx.repo, {".py"}):
        efetivo = scan.codigo_efetivo(scan.ler(p), ".py", sem_literais=True).lower()
        if any(m in efetivo for m in marcas):
            return True
    return False


@check("P-19", "privacy", "Evento com PII sem crypto-shredding", base_legal=BASE)
def evento_sem_crypto_shredding(ctx):
    produtores = set(_r(ctx, "produtores_de_evento"))
    barramentos = _r(ctx, "barramentos_de_evento")
    shredding = _r(ctx, "crypto_shredding")
    cifras = _r(ctx, "cifra_de_aplicacao")
    pii = _pii(ctx)

    candidatos, houve_produtor = [], False
    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        texto = scan.ler(p)
        modulo = _modulo_fala_com_barramento(texto, barramentos)
        for no, nome in scan.chamadas(arvore):
            if not _e_producao_de_evento(nome, produtores, barramentos, modulo):
                continue
            houve_produtor = True
            # D-08: payload que ja vai cifrado por titular.
            if any(scan.nome_casa(scan.nome_chamado(sub), cifras)
                   for sub in ast.walk(no) if isinstance(sub, ast.Call)):
                continue
            campos = _pii_no_payload(no, pii)
            if campos:
                candidatos.append((p, no, nome, campos, texto))

    if not houve_produtor:
        raise SkipCheck(
            "nenhuma producao de evento em barramento append-only no codigo — "
            "nao ha registro imutavel a confrontar com o direito de eliminacao")
    if not candidatos:
        return []
    if _ha_crypto_shredding(ctx, shredding):
        return []                        # D-08: a estrategia existe no repo

    findings = []
    for p, no, nome, campos, texto in candidatos:
        linhas = texto.splitlines()
        i = no.lineno
        findings.append(Finding(
            check_id="P-19", pack="privacy", severidade=Severidade.ALTO,
            titulo=f"Evento em `{nome}` carrega {campos} sem crypto-shredding",
            descricao=(
                f"O payload publicado num registro append-only carrega "
                f"{campos}, e o repositorio nao tem nenhuma rotina de "
                f"destruicao de chave por titular. Apagar e uma operacao que "
                f"NAO EXISTE neste tipo de registro: retencao por tempo expira "
                f"particao, nao titular, e compaction preserva a ultima versao "
                f"da chave — que continua sendo o dado. Quando o pedido de "
                f"eliminacao chegar, a linha some do banco relacional e o dado "
                f"continua em todo replay do topico e em toda projecao "
                f"materializada por consumidor."),
            recomendacao=(
                "Crypto-shredding: publicar o evento cifrado com uma chave por "
                "titular e, na eliminacao, destruir a chave. O evento imutavel "
                "permanece e vira ruido — que e o que a lei pede, porque dado "
                "que ninguem consegue ler deixa de ser dado pessoal. "
                "Alternativa: publicar so um identificador opaco e manter a "
                "PII num armazenamento que apague de verdade."),
            base_legal=BASE,
            arquivo=scan.rel(ctx.repo, p), linha=i,
            snippet=linhas[i - 1].strip()[:200] if i <= len(linhas) else None))
    return findings
