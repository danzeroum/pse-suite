"""S-18 — o terceiro que a PAGINA contactou, contra o que o manifesto declara.

Par dinamico de S-04, e a diferenca entre os dois e o buraco inteiro que
esta camada existe para cobrir.

S-04 le o manifesto e o codigo: sabe dos terceiros que alguem ESCREVEU. Mas
todo host que a pagina contacta recebe, no minimo, o IP e o User-Agent do
visitante — dado pessoal (Art. 5o I) tratado por um operador que precisa
estar mapeado (Art. 37) e contratado (Art. 39). E os hosts que chegam ali
sem passar pelo codigo do repositorio sao a maioria dos casos reais:

  * a tag gerenciada que alguem adicionou pelo painel;
  * o `<script>` que uma dependencia injeta em runtime;
  * o CDN que o proprio terceiro chama a partir do script dele — o terceiro
    do terceiro, que nenhum manifesto costuma listar;
  * a fonte externa que veio junto com um tema.

Nenhum desses aparece num `grep` do repositorio. Todos aparecem no
NetworkLog.

D-08: host declarado no manifesto NAO dispara — e o comportamento que o
check quer produzir. Subdominio de host declarado tambem nao: quem declarou
`terceiro.example.net` declarou o controlador, e `cdn.terceiro.example.net`
e o mesmo controlador.

SEM MANIFESTO nao ha o que confrontar: SkipCheck, com a ausencia cobrada
por S-04. Nunca indeterminado — a pre-condicao declarativa simplesmente nao
existe, e essa e a definicao de N/A declarado.
"""
from pse.engine.registry import check
from pse.navegador import analise
from pse.model import Finding, Severidade, SkipCheck
from pse.navegador.rede import host_casa, host_de
from pse.trabalho_a.base import exigir_observacao

BASE = "LGPD Art. 37 e 39 (registro e operador) + Art. 42"


@check("S-18", "security", "Terceiro observado fora do manifesto", base_legal=BASE)
def terceiro_observado(ctx):
    log = exigir_observacao(ctx, "passive")   # 5 degraus + navegador
    analise.relatar_observacao(ctx, log)

    manifesto = ctx.manifest_terceiros()
    if manifesto is None:
        raise SkipCheck(
            "manifesto de terceiros ausente — cobrado por S-04; sem "
            "declaracao nao ha o que confrontar com o que foi observado")

    declarados = []
    for item in manifesto.get("integrations") or []:
        declarados += [str(h).lower() for h in (item.get("hosts") or [])]
    ignorar = [str(h).lower() for h in
               (ctx.data["third-party-endpoints"].get("ignorar") or [])]

    origem = host_de(log.url)
    inventario, nao_declarados = {}, {}
    for req in log.requisicoes:
        host = host_de(req.url)
        if not host or (origem and host_casa(host, origem)):
            continue
        inventario[host] = inventario.get(host, 0) + 1
        if any(host_casa(host, d) for d in declarados + ignorar):
            continue
        nao_declarados[host] = nao_declarados.get(host, 0) + 1

    # O inventario inteiro vai para o laudo mesmo sem achado: e insumo de
    # ROPA/DPA (Art. 37), e o consumidor precisa saber o que ja esta certo,
    # nao so o que esta errado.
    ctx.relatorio("terceiros_observados", {
        "origem": origem,
        "hosts": [{"host": h, "requisicoes": n}
                  for h, n in sorted(inventario.items(),
                                     key=lambda kv: (-kv[1], kv[0]))],
        "nota": "Cada host recebe IP e User-Agent do visitante. Inventario "
                "observado, insumo de registro de operacoes — nao veredito.",
    })

    if not nao_declarados:
        return []

    hosts = sorted(nao_declarados)
    return [Finding(
        check_id="S-18", pack="security", severidade=Severidade.ALTO,
        titulo=f"{len(hosts)} terceiro(s) contactados e nao declarados",
        descricao=(
            f"A pagina contactou {hosts} e nenhum consta do manifesto. Todo "
            f"host contactado recebe o IP e o User-Agent do visitante — "
            f"tratamento por operador que precisa estar mapeado (Art. 37) e "
            f"contratado (Art. 39). S-04 le o manifesto e o codigo, entao so "
            f"alcanca o terceiro que alguem ESCREVEU; estes chegaram por "
            f"outro caminho — tag gerenciada pelo painel, script injetado por "
            f"dependencia, ou o terceiro que o proprio terceiro chama."),
        recomendacao=(
            "Declarar cada host no manifesto com DPA, residencia e campos de "
            "egresso — ou remove-lo. Host que aparece na observacao e nao no "
            "manifesto e operador sem contrato: o registro de operacoes esta "
            "incompleto pelo tamanho exato desta lista."),
        base_legal=BASE, arquivo=ctx.manifesto_path(), linha=1,
        trace={"nao_declarados": [{"host": h, "requisicoes": n}
                                  for h, n in sorted(nao_declarados.items())],
               "observacao": log.sanitizado()})]
