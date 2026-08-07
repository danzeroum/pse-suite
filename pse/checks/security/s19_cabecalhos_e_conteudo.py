"""S-19 — o que o servidor DECLAROU na resposta, e o que trafegou em claro.

Adaptado de `checks/seguranca/test_headers_e_conteudo.py` da qa-suite.
Passivo inteiro: opera sobre o que o navegador ja baixou, sem uma requisicao
nova sequer.

DOIS VETORES, com pesos distintos e de proposito:

  1. CABECALHO AUSENTE no documento de origem. CSP, nosniff e
     Referrer-Policy sao decisao do controlador e ele manda no servidor —
     e acionavel hoje. Vira achado.
  2. MIXED CONTENT: asset `http://` numa pagina `https://`. Sem atenuante:
     o conteudo trafegou em claro e pode ter sido adulterado no caminho,
     anulando o TLS da pagina inteira.

O QUE NAO VIRA ACHADO, e por que a decisao veio junto do porte:

  * Cabecalho ausente em asset de TERCEIRO. E maturidade do fornecedor, e o
    controlador do alvo muitas vezes nao manda no servidor dele. Entra no
    laudo como observacao — o que ele pode fazer e trocar de fornecedor ou
    hospedar localmente, e o relatorio diz isso.
  * `Strict-Transport-Security` e `X-Frame-Options`. Dependem de decisao de
    arquitetura: um site que precisa ser embutido legitimamente nao pode
    negar frame. Sinal, nao violacao.

Mixed content so e avaliado quando o alvo e https: num alvo http NADA e
mixed content, e cobrar ali seria inventar violacao. URL protocol-relative
(`//host/x.js`) herda o esquema da pagina e nunca e mixed content — e
justamente o caso em que a verificacao ingenua por "comeca com http" erra.
"""
from pse.engine.registry import check
from pse.navegador import analise
from pse.model import Finding, Severidade
from pse.navegador.analise import cabecalhos_faltantes
from pse.trabalho_a.base import exigir_observacao

BASE = "LGPD Art. 46 (seguranca) + Art. 6o VIII (prevencao)"
REGUA = "servido-ao-cliente"


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _documento(log):
    """A resposta da propria navegacao — o documento, nao os assets."""
    for r in log.recursos:
        if r.da_origem and r.status < 400 and "html" in (r.tipo or "").lower():
            return r
    return None


@check("S-19", "security", "Cabecalhos de seguranca e mixed content",
       base_legal=BASE)
def cabecalhos_e_conteudo(ctx):
    log = exigir_observacao(ctx, "passive")   # 5 degraus + navegador
    analise.relatar_observacao(ctx, log)

    findings = []
    exigidos = _r(ctx, "cabecalhos_exigidos")
    informativos = _r(ctx, "cabecalhos_informativos")
    executaveis = [t.lower() for t in _r(ctx, "tipos_executaveis")]

    # ------------------------------------------- 1. cabecalhos do documento
    doc = _documento(log)
    if doc is not None:
        faltando = cabecalhos_faltantes(doc, exigidos)
        if faltando:
            nomes = [n for n, _ in faltando]
            findings.append(Finding(
                check_id="S-19", pack="security", severidade=Severidade.ALTO,
                titulo=f"Documento sem {', '.join(nomes)}",
                descricao=(
                    "O servidor entregou o documento sem estes cabecalhos. " +
                    " ".join(f"{n}: {motivo}." for n, motivo in faltando) +
                    " Sao decisao do controlador, que manda no proprio "
                    "servidor — e acionavel hoje, diferente do cabecalho de um "
                    "asset de terceiro."),
                recomendacao=(
                    "Emitir os tres na resposta do documento. Comece a CSP em "
                    "modo `Report-Only` para levantar o que quebra, e so "
                    "depois promova a bloqueante: uma CSP que quebra o produto "
                    "e removida na semana seguinte, e ai nao ha CSP nenhuma."),
                base_legal=BASE, arquivo=log.url, linha=None,
                trace={"faltando": nomes, "observacao": log.sanitizado()}))

        ausentes_informativos = [n for n, _ in
                                 cabecalhos_faltantes(doc, informativos)]
        if ausentes_informativos:
            ctx.relatorio("cabecalhos_informativos_ausentes", {
                "cabecalhos": ausentes_informativos,
                "nota": "Sinal, nao violacao: dependem de decisao de "
                        "arquitetura (um alvo que precisa ser embutido nao "
                        "pode negar frame).",
            })

    # ------------------------------------------- 2. mixed content
    if log.url.lower().startswith("https://"):
        em_claro = [r.url for r in log.recursos if r.esquema == "http"]
        if em_claro:
            findings.append(Finding(
                check_id="S-19", pack="security", severidade=Severidade.ALTO,
                titulo=f"{len(em_claro)} recurso(s) carregados por http:// "
                       f"numa pagina https://",
                descricao=(
                    "Mixed content, sem atenuante: o conteudo trafegou em "
                    "claro e pode ter sido adulterado em transito, anulando o "
                    "TLS da pagina inteira. Nao adianta a pagina ser https se "
                    "o script que ela executa chegou por http."),
                recomendacao=("Servir todo asset por https, ou usar URL "
                              "relativa ao esquema. Se o fornecedor nao "
                              "oferece https, ele nao pode ser carregado numa "
                              "pagina que trata dado pessoal."),
                base_legal=BASE, arquivo=log.url, linha=None,
                trace={"recursos": em_claro[:10],
                       "observacao": log.sanitizado()}))

    # --------------------------- 3. asset de terceiro pelado: OBSERVACAO
    pelados = [r.url for r in log.recursos
               if not r.da_origem and r.status < 400
               and any(t in (r.tipo or "").lower() for t in executaveis)
               and not r.cabecalho("x-content-type-options").strip()]
    if pelados:
        ctx.relatorio("assets_de_terceiro_sem_nosniff", {
            "recursos": pelados[:10],
            "nota": "Nao vira achado: e maturidade do FORNECEDOR, e o "
                    "controlador do alvo nao manda no servidor dele. O que "
                    "ele pode fazer e trocar de fornecedor ou hospedar "
                    "localmente.",
        })
    return findings
