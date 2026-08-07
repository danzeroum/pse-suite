"""S-21 — o bundle que aponta para o proprio codigo-fonte.

`//# sourceMappingURL=app.js.map` no bundle entrega o caminho do
codigo-fonte original. Um sourcemap costuma trazer a arvore inteira: nomes
de variavel, comentarios, rotas internas, a estrutura que o minificador
existia para apagar.

O `.map` NAO E BAIXADO, e isso e a decisao central deste check. Confirmar
se ele esta publicado exigiria uma requisicao que o navegador nao fez — ou
seja, sondagem, ou seja, Fase 3, atras do gate ativo. Este check aponta o
caminho e para ai.

E por isso a severidade e MEDIO, e nao ALTO: o que se sabe e que a
REFERENCIA existe. Se o `.map` esta de fato publicado depende do servidor, e
a suite nao vai perguntar. Cobrar em ALTO uma condicao que nao foi
verificada seria a suite fingindo certeza — o mesmo defeito que ela cobra
dos outros. Quando a Fase 3 existir, a confirmacao pode elevar o peso.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a.base import exigir_observacao

BASE = "LGPD Art. 46 (seguranca)"
REGUA = "servido-ao-cliente"


@check("S-21", "security", "Sourcemap referenciado em producao", base_legal=BASE)
def sourcemap_em_producao(ctx):
    from pse.navegador.analise import sourcemap_referenciado

    log = exigir_observacao(ctx, "passive")   # 5 degraus + navegador
    ctx.relatorio("observacao_de_rede", log.sanitizado())

    sufixos = tuple(str(s).lower() for s in ctx.data[REGUA]["sufixos_de_bundle"])
    tipos = [t.lower() for t in ctx.data[REGUA]["tipos_de_bundle"]]

    referencias = []
    for recurso in log.recursos:
        if not recurso.da_origem or recurso.status >= 400 or not recurso.avaliavel:
            continue
        caminho = recurso.url.split("?")[0].lower()
        if not (caminho.endswith(sufixos)
                or any(t in (recurso.tipo or "").lower() for t in tipos)):
            continue
        mapa = sourcemap_referenciado(recurso.corpo)
        if mapa:
            referencias.append({"bundle": recurso.url, "sourcemap": mapa})

    if not referencias:
        return []

    return [Finding(
        check_id="S-21", pack="security", severidade=Severidade.MEDIO,
        titulo=f"{len(referencias)} bundle(s) referenciando sourcemap",
        descricao=(
            "O bundle declara `sourceMappingURL`, que entrega o caminho do "
            "codigo-fonte original — nomes de variavel, comentarios, rotas "
            "internas, tudo que o minificador existia para apagar. "
            "O `.map` NAO foi baixado: confirmar se esta publicado exigiria "
            "uma requisicao que o navegador nao fez, e isso e sondagem "
            "(Fase 3, atras do gate ativo). Por isso MEDIO e nao ALTO — o que "
            "se sabe e que a REFERENCIA existe, e cobrar em ALTO uma condicao "
            "nao verificada seria a suite fingindo certeza."),
        recomendacao=(
            "Nao publicar sourcemap em producao, ou publica-lo apenas para o "
            "servico de erros, atras de autenticacao. Se o `.map` nao estiver "
            "no servidor, remova tambem a referencia: ela e um mapa do que "
            "procurar."),
        base_legal=BASE, arquivo=referencias[0]["bundle"], linha=None,
        trace={"referencias": referencias[:10],
               "observacao": log.sanitizado()})]
