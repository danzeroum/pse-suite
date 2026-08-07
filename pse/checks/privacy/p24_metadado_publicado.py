"""P-24 — o que o arquivo publicado revela alem do que servia para servir.

DIVERGENCIA DECLARADA. A tarefa agrupou "metadados/GPS em imagem, sourcemap
em producao" sob `security`. Separei em dois checks e pus ESTE em `privacy`,
aplicando a regra do proprio projeto: o pilar responde QUE VALOR esta em
jogo. Coordenada de GPS numa foto publicada e localizacao de pessoa — dado
pessoal por consequencia direta (Art. 5o I). Sourcemap e codigo-fonte, e
ficou em S-21, no pilar de seguranca. Se a leitura estiver errada, o
conserto e um campo `pack` no catalogo.

Coordenada revela onde a foto foi tirada; em foto de pessoa, revela onde a
pessoa estava. E o vazamento que ninguem pretendeu: o time subiu um avatar,
nao uma localizacao — e o EXIF viajou junto porque ninguem o removeu.

SO A PRESENCA E REPORTADA. `analise.metadados_exif` devolve o rotulo `gps`,
nunca a coordenada. Nao existe valor a mascarar, e o sanitizador do Finding
roda por cima mesmo assim — duas defesas independentes de proposito.

GPS e ACHADO; autoria e OBSERVACAO. Autor e ferramenta identificam quem
produziu e com que, o que ajuda no reconhecimento de alvo, mas nao localiza
ninguem: e higiene de publicacao, nao violacao. Misturar os dois no mesmo
peso ensinaria o time a tratar os dois como ruido.

Le apenas o que o navegador JA baixou. Ir buscar um arquivo que a pagina
nao referenciou seria sondagem — Fase 3, atras do gate.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a.base import exigir_observacao

BASE = "LGPD Art. 5o I + Art. 6o III (minimizacao)"
REGUA = "servido-ao-cliente"


def _r(ctx, chave):
    return ctx.data[REGUA][chave]


@check("P-24", "privacy", "Metadado em arquivo publicado", base_legal=BASE)
def metadado_publicado(ctx):
    from pse.navegador.analise import metadados_exif

    log = exigir_observacao(ctx, "passive")   # 5 degraus + navegador
    ctx.relatorio("observacao_de_rede", log.sanitizado())

    sufixos = tuple(str(s).lower() for s in _r(ctx, "sufixos_com_metadado"))
    tipos = [t.lower() for t in _r(ctx, "tipos_com_metadado")]
    explicacao = _r(ctx, "metadados_publicados")

    findings, com_autoria, nao_lidos = [], [], []
    for recurso in log.recursos:
        if recurso.status >= 400:
            continue
        caminho = recurso.url.split("?")[0].lower()
        if not (caminho.endswith(sufixos)
                or any(t in (recurso.tipo or "").lower() for t in tipos)):
            continue
        if not recurso.avaliavel:
            nao_lidos.append(f"{recurso.url} ({recurso.motivo_nao_lido})")
            continue

        achados = metadados_exif(recurso.corpo)
        if "gps" in achados:
            findings.append(Finding(
                check_id="P-24", pack="privacy", severidade=Severidade.ALTO,
                titulo=f"Imagem publicada com coordenada de GPS no EXIF",
                descricao=(
                    f"O arquivo servido carrega IFD de GPS. "
                    f"{explicacao.get('gps', '')}. A coordenada NAO e lida "
                    f"nem reproduzida aqui: so a presenca e reportada, porque "
                    f"republicar o valor reencenaria a exposicao. E o "
                    f"vazamento que ninguem pretendeu — o time subiu um "
                    f"avatar, nao uma localizacao, e o EXIF viajou junto."),
                recomendacao=(
                    "Remover o EXIF no pipeline de publicacao, para TODA "
                    "imagem — nao caso a caso. O upload de titular e o pior "
                    "caso: a foto vem do celular dele, com a coordenada de "
                    "onde ele estava."),
                base_legal=BASE, arquivo=recurso.url, linha=None,
                trace={"metadados": sorted(achados), "recurso": recurso.url}))
        if achados - {"gps"}:
            com_autoria.append(f"{recurso.url} ({', '.join(sorted(achados - {'gps'}))})")

    if com_autoria:
        ctx.relatorio("metadado_de_autoria_publicado", {
            "recursos": com_autoria[:10],
            "nota": explicacao.get("autoria", ""),
        })
    if nao_lidos:
        ctx.relatorio("imagens_nao_varridas", {
            "recursos": nao_lidos[:10],
            "nota": "Nao avaliado nao e limpo: estes arquivos nao foram lidos.",
        })
    return findings
