"""S-20 — credencial servida ao navegador. Par dinamico de P-06.

P-06 encontra a chave no REPOSITORIO. Este encontra a chave que chegou ao
NAVEGADOR — e a diferenca importa porque o caminho entre os dois e cheio de
lugares que o repositorio nao mostra: a variavel injetada no build, o
`window.__CONFIG__` que o servidor renderiza no template, o `config.json`
que o deploy escreve, o bundle de um pacote que embutiu a propria chave.

E a distincao muda a urgencia. Uma chave no repositorio esta exposta a quem
tem acesso ao repositorio. Uma chave no bundle esta **publicada**: qualquer
visitante le, e ja leu. Nao ha o que "esconder" — a unica correcao e
ROTACIONAR primeiro e remover depois, e nessa ordem.

ESCOPO: primeira parte. Uma chave num bundle de terceiro e problema do
terceiro e o controlador nao tem como remove-la; uma chave no `app.js` do
proprio alvo e dele, e e acionavel hoje.

CONTRATO INVIOLAVEL: o valor NUNCA aparece. `analise.segredos_em` devolve o
NOME do formato, e o valor casado nao sai da funcao — republica-lo no laudo
reencenaria o vazamento num artefato que circula por CI e anexo de PR. A
minimizacao acontece antes do sanitizador, e o sanitizador roda por cima
mesmo assim: duas defesas independentes, porque quem confia numa so acaba
sem nenhuma.

NAO AVALIADO NUNCA E LIMPO. Corpo acima do teto entra no laudo como
recurso nao varrido. Se NENHUM candidato pode ser lido, o check fica
indeterminado: teto de memoria nao e atestado de conformidade.
"""
from pse.engine.registry import check
from pse.navegador import analise
from pse.model import CheckIndeterminado, Finding, Severidade
from pse.trabalho_a.base import exigir_observacao

BASE = "LGPD Art. 46 (seguranca)"
REGUA = "servido-ao-cliente"


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


def _candidatos(ctx, log) -> list:
    tipos = [t.lower() for t in _r(ctx, "tipos_varridos_por_segredo")]
    sufixos = tuple(str(s).lower() for s in _r(ctx, "sufixos_varridos_por_segredo"))
    saida = []
    for r in log.recursos:
        if not r.da_origem or r.status >= 400:
            continue
        caminho = r.url.split("?")[0].lower()
        if caminho.endswith(sufixos) or any(t in (r.tipo or "").lower()
                                            for t in tipos):
            saida.append(r)
    return saida


@check("S-20", "security", "Credencial servida ao cliente", base_legal=BASE)
def segredo_servido(ctx):
    from pse.navegador.analise import segredos_em

    log = exigir_observacao(ctx, "passive")   # 5 degraus + navegador
    analise.relatar_observacao(ctx, log)

    padroes = _r(ctx, "padroes_de_segredo")
    candidatos = _candidatos(ctx, log)
    if not candidatos:
        return []

    nao_lidos = [f"{r.url} ({r.motivo_nao_lido})" for r in candidatos
                 if not r.avaliavel]
    lidos = [r for r in candidatos if r.avaliavel]
    if not lidos:
        raise CheckIndeterminado(
            f"nenhum dos {len(candidatos)} recurso(s) de origem pode ser "
            f"varrido: {nao_lidos[:3]}. Nao avaliado nao e limpo — teto de "
            f"memoria nao e atestado de conformidade")
    if nao_lidos:
        ctx.relatorio("recursos_nao_varridos", {
            "recursos": nao_lidos[:10],
            "nota": "Ausencia de achado NESTES recursos nao e ausencia de "
                    "segredo: eles nao foram lidos.",
        })

    findings = []
    for recurso in lidos:
        for nome, severidade in segredos_em(recurso.texto(), padroes):
            findings.append(Finding(
                check_id="S-20", pack="security",
                severidade=Severidade[severidade],
                titulo=f"Credencial `{nome}` servida ao cliente",
                descricao=(
                    f"Um recurso do PROPRIO alvo carrega uma credencial no "
                    f"formato {nome}. Isto nao esta escondido no codigo: esta "
                    f"PUBLICADO — qualquer visitante le o bundle, e ja leu. "
                    f"P-06 encontra a chave no repositorio; esta chegou ao "
                    f"navegador, e pode ter vindo do build, do template ou de "
                    f"um pacote que embutiu a propria. O VALOR nao aparece "
                    f"aqui de proposito: republica-lo reencenaria o "
                    f"vazamento."),
                recomendacao=(
                    "ROTACIONAR primeiro, remover depois — nessa ordem. A "
                    "chave ja foi servida a todos os visitantes, entao "
                    "apaga-la do codigo nao a invalida. Depois, mover a "
                    "chamada para o servidor: o que o navegador precisa e de "
                    "um endpoint seu, nao da credencial do fornecedor."),
                base_legal=BASE, arquivo=recurso.url, linha=None,
                trace={"formato": nome, "recurso": recurso.url,
                       "observacao": log.sanitizado()}))
    return findings
