"""S-04 — host externo no codigo que o manifesto de terceiros nao declara.

Le tambem `.html`: `index.html` e o unico arquivo que o navegador carrega
sempre, e e onde mora `<link href="https://fonts.googleapis.com/...">`.
Enquanto HTML era "irrelevante", esse egresso so aparecia na camada
dinamica — a estatica passava batido.

CRITICO quando o terceiro esta declarado mas sem DPA assinado: o operador
existe, o contrato nao. ALTO quando o host nao esta no manifesto: pode ser
terceiro nao declarado ou host de exemplo, e o grau maximo exige certeza.
"""
import re
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

RX_HOST = re.compile(r"https?://([a-z0-9][a-z0-9.-]*\.[a-z]{2,})", re.I)
EXTS = scan.ECMASCRIPT | {".py", ".go", ".java", ".yaml", ".yml", ".env",
                          ".html", ".htm"}


def _categoria(host, conhecidos):
    for cat, hosts in conhecidos.items():
        if host in hosts:
            return cat
    return None


@check("S-04", "security", "Terceiro no codigo sem manifesto/DPA", base_legal="LGPD Art. 39")
def manifesto_terceiros(ctx):
    ignorar = set(ctx.data["third-party-endpoints"].get("ignorar", []))
    conhecidos = ctx.data["third-party-endpoints"].get("categorias", {})
    manifesto = ctx.manifest_terceiros()
    registrados = set()
    findings = []

    if manifesto:
        for item in manifesto.get("integrations", []):
            registrados.update(item.get("hosts", []))
            if item.get("required", True) and not item.get("dpa_signed"):
                findings.append(Finding(
                    check_id="S-04", pack="security", severidade=Severidade.CRITICO,
                    titulo=f"Integracao '{item.get('name')}' sem DPA assinado",
                    descricao="Terceiro obrigatorio declarado no manifesto sem DPA "
                              "— deploy nao pode prosseguir.",
                    recomendacao="Assinar e homologar o DPA antes do proximo deploy; "
                                 "registrar dpa_path no manifesto.",
                    base_legal="LGPD Art. 39",
                    arquivo=ctx.manifesto_path(),
                    linha=ctx.linha_da_integracao(item.get("name"))))

    detectados = {}
    for p in scan.arquivos(ctx.repo, EXTS):
        # D-01, e a lacuna foi encontrada pelo PRIMEIRO ALVO REAL. Ate aqui
        # S-04 lia o texto cru, entao `// https://vite.dev/config/` — um
        # link de documentacao num comentario — virava "host de terceiro nao
        # registrado". Nenhuma fixture tinha URL em comentario, e o defeito
        # atravessou o projeto inteiro dentro do check MAIS ANTIGO da suite.
        #
        # `codigo_efetivo` apaga comentario e PRESERVA literal de string, que
        # e o certo aqui: `fetch("https://api.terceiro.com")` e egresso de
        # verdade, e o literal E o fato. So a mencao sai.
        texto = scan.ler(p)
        efetivo = scan.codigo_efetivo(texto, p.suffix or ".py")
        for i, linha in enumerate(efetivo.splitlines(), 1):
            for m in RX_HOST.finditer(linha):
                host = m.group(1).lower()
                if host in ignorar or any(host.endswith("." + ig) for ig in ignorar):
                    continue
                detectados.setdefault(host, (scan.rel(ctx.repo, p), i))

    for host, (arq, linha) in sorted(detectados.items()):
        if host in registrados:
            continue
        cat = _categoria(host, conhecidos)
        extra = f" (categoria conhecida: {cat})" if cat else ""
        findings.append(Finding(
            check_id="S-04", pack="security", severidade=Severidade.ALTO,
            titulo=f"Host externo nao registrado no manifesto: {host}",
            descricao=f"Endpoint de terceiro{extra} usado no codigo sem entrada "
                      "em .privacy/third-party-manifest.yml.",
            recomendacao="Registrar a integracao com DPA, residencia de dados e "
                         "base de transferencia — ou remover a chamada.",
            base_legal="LGPD Art. 39", arquivo=arq, linha=linha))
    return findings
