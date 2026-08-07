"""E-13 — host que sai de dentro de uma dependencia (o terceiro-do-terceiro).

S-04 varre o codigo de primeira parte e ignora `node_modules`/`site-packages`
POR CONSTRUCAO — sem isso qualquer laudo viraria ruido. O efeito colateral e
um buraco inteiro: a dependencia que um dia adicionou telemetria nunca
aparece no manifesto, porque ninguem escreveu aquela URL. O consumidor
assinou DPA com quem ele conhece, e o dado sai para quem ele nunca viu.

E-13 e o unico check que entra deliberadamente nesses diretorios, e faz uma
pergunta so: **este host esta declarado no manifesto?** Nao julga a
dependencia, nao classifica o trafego — cobra a declaracao, e nomeia o
pacote que trouxe o host para que a investigacao comece em algum lugar.

Art. 42 e o coracao aqui: perante o titular, quem escolheu a dependencia
responde pelo que ela faz.

Limites explicitos: `node_modules` pode ter centenas de milhares de arquivos.
O teto e da suite, e quando ele e atingido isso vai para o laudo como
cobertura parcial — truncamento silencioso leria como "varri tudo".
"""
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

BASE_LEGAL = "LGPD Art. 39 + Art. 42 (responsabilidade solidaria)"

DIRS_DEPENDENCIA = ("node_modules", "site-packages", "vendor", "bower_components")
EXTS = scan.ECMASCRIPT | {".mjs", ".cjs", ".py", ".json"}
RX_HOST = re.compile(r"https?://([a-z0-9][a-z0-9.-]*\.[a-z]{2,})", re.I)

TETO_ARQUIVOS = 4000
TAMANHO_MAX = 512_000


def _raizes(repo):
    for p in sorted(repo.rglob("*")):
        if p.is_dir() and p.name in DIRS_DEPENDENCIA:
            yield p


def _pacote(raiz, arquivo) -> str:
    """Nome do pacote que contem o arquivo — quem trouxe o host."""
    rel = arquivo.relative_to(raiz).parts
    if not rel:
        return raiz.name
    if rel[0].startswith("@") and len(rel) > 1:      # escopo npm
        return f"{rel[0]}/{rel[1]}"
    return rel[0]


def _varrer(repo):
    """(host, arquivo_relativo, linha, pacote) e se o teto foi atingido."""
    achados, vistos, lidos = [], set(), 0
    truncou = False
    for raiz in _raizes(repo):
        for arq in sorted(raiz.rglob("*")):
            if not arq.is_file() or arq.suffix not in EXTS:
                continue
            if lidos >= TETO_ARQUIVOS:
                truncou = True
                break
            try:
                if arq.stat().st_size > TAMANHO_MAX:
                    continue
            except OSError:
                continue
            lidos += 1
            for i, linha in enumerate(scan.ler(arq).splitlines(), 1):
                for m in RX_HOST.finditer(linha):
                    host = m.group(1).lower().rstrip(".")
                    if host in vistos:
                        continue
                    vistos.add(host)
                    achados.append((host, scan.rel(repo, arq), i,
                                    _pacote(raiz, arq)))
        if truncou:
            break
    return achados, truncou, lidos


@check("E-13", "ethics", "Dependencia com host nao declarado", base_legal=BASE_LEGAL)
def dependencia_exfiltra(ctx):
    manifesto = ctx.manifest_terceiros()
    if manifesto is None:
        raise SkipCheck("manifesto de terceiros ausente — sem ele todo host de "
                        "dependencia seria achado, e ruido nao e evidencia "
                        "(a ausencia do manifesto e cobrada por S-04)")

    registrados = set()
    for item in manifesto.get("integrations", []):
        registrados.update(h.lower() for h in (item.get("hosts") or []))

    dados = ctx.data["third-party-endpoints"]
    ignorar = {h.lower() for h in dados.get("ignorar", [])}
    ignorar |= {h.lower() for h in dados.get("ignorar_em_dependencias", [])}
    conhecidos = dados.get("categorias", {})

    achados, truncou, lidos = _varrer(ctx.repo)
    if truncou:
        ctx.relatorio("cobertura_parcial", {
            **ctx.relatorios.get("cobertura_parcial", {}),
            "E-13": f"varredura interrompida no teto de {TETO_ARQUIVOS} arquivos "
                    f"de dependencia; hosts alem desse ponto nao foram avaliados"})

    findings = []
    for host, arquivo, linha, pacote in achados:
        if host in registrados or host in ignorar:
            continue
        if any(host.endswith("." + ig) for ig in ignorar):
            continue
        categoria = next((c for c, hosts in conhecidos.items() if host in hosts), None)
        extra = f" Categoria conhecida da regua: {categoria}." if categoria else ""
        findings.append(Finding(
            check_id="E-13", pack="ethics", severidade=Severidade.ALTO,
            titulo=f"Host de dependencia fora do manifesto: {host}",
            descricao=f"O pacote '{pacote}' embute chamadas para {host}, que nao "
                      f"consta no manifesto de terceiros. Nenhuma linha do codigo "
                      f"de primeira parte cita esse host — por isso S-04 nao o ve. "
                      f"O titular nao distingue voce do seu fornecedor: perante "
                      f"ele, quem escolheu a dependencia responde pelo que ela "
                      f"faz.{extra}",
            recomendacao=f"Registrar o destino no manifesto (com DPA, residencia "
                         f"e base de transferencia), fixar a versao de '{pacote}' "
                         f"ou substituir a dependencia; bloquear o egresso na "
                         f"borda enquanto isso nao acontece.",
            base_legal=BASE_LEGAL,
            arquivo=arquivo, linha=linha))
    return findings
