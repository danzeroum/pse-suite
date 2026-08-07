"""S-14 — o dump de producao pousando num ambiente inferior.

E o vazamento que nao passa por API nenhuma. Nao ha rota, nao ha token de
titular, nao ha log de acesso: o dado sai pela porta de tras, com credencial
de operacao, e vai parar num banco onde metade do time tem SELECT e a senha
esta num .env que ninguem rotaciona. Todo o pack de borda — S-01, S-02,
S-03, P-05 — nao alcanca um metro disto.

E e comum porque parece produtividade: "staging com dado real" e o pedido
mais razoavel que um QA pode fazer. A resposta certa nao e recusar o dado
real, e descaracteriza-lo no caminho.

O FATO: uma linha que EXECUTA um restaurador de dump tendo, ao mesmo tempo,
marca de producao e marca de ambiente inferior. `psql staging < prod.sql`
atravessa a fronteira; `pg_dump prod > prod.sql` e so um backup e nao vira
achado; `psql dev < seed_dev.sql` nao tem origem de producao e tampouco.

D-01: comentario nao conta, dos dois lados. O restore comentado nao vira
achado, e `# anonymize aplicado no gateway` nao desliga o achado real —
`scan.codigo_efetivo` apaga o comentario antes de qualquer heuristica.

D-08: se um passo de pseudonimizacao EXECUTA no mesmo script, ate a linha
do restore, o dump que chega ao ambiente inferior nao carrega mais o
titular — e nao ha achado.

LIMITE DECLARADO: a descaracterizacao e reconhecida quando aparece no mesmo
arquivo, antes do restore. Um pipeline partido em dois arquivos (o Makefile
que chama o scrub, o workflow que chama o Makefile) nao e seguido. E uma
lacuna conhecida, e preferi declara-la a fingir um rastreio entre arquivos
que este check nao faz.
"""
from pathlib import Path

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

BASE = "LGPD Art. 46 (seguranca) + Art. 6o VIII (prevencao)"
REGUA = "backend-infra"
EXTENSOES = {".sh", ".bash", ".zsh", ".sql", ".yml", ".yaml", ".py", ".mk",
             "Makefile", "makefile"}


def _r(ctx, chave):
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def _tem(linha: str, marcas) -> str | None:
    for m in marcas:
        if m in linha:
            return m
    return None


@check("S-14", "security", "Dump de producao em ambiente inferior", base_legal=BASE)
def dump_de_producao(ctx):
    restauradores = _r(ctx, "restauradores_de_dump")
    producao = _r(ctx, "marcas_de_producao")
    inferiores = _r(ctx, "marcas_de_nao_producao")
    pseudo = _r(ctx, "pseudonimizacao")
    findings = []

    for p in scan.arquivos(ctx.repo, EXTENSOES):
        texto = scan.ler(p)
        # O comentario e apagado ANTES de qualquer heuristica (D-01). Sem
        # isto, `# psql staging < prod.sql (antigo)` viraria achado e
        # `# anonymize no gateway` desligaria o achado real.
        efetivo = scan.codigo_efetivo(texto, Path(p).suffix or ".sh")
        linhas_efetivas = efetivo.splitlines()
        originais = texto.splitlines()

        for i, linha in enumerate(linhas_efetivas, 1):
            baixo = linha.lower()
            ferramenta = _tem(baixo, restauradores)
            if not ferramenta:
                continue
            origem = _tem(baixo, producao)
            destino = _tem(baixo, inferiores)
            if not (origem and destino):
                continue
            # A descaracterizacao tem de ter rodado ANTES: um scrub depois
            # do restore nao impede o dado de existir no ambiente inferior.
            antes = "\n".join(linhas_efetivas[:i]).lower()
            if _tem(antes, pseudo):
                continue
            findings.append(Finding(
                check_id="S-14", pack="security", severidade=Severidade.ALTO,
                titulo=f"Dump de producao restaurado em ambiente '{destino}' "
                       f"sem descaracterizar",
                descricao=(
                    f"A linha executa `{ferramenta}` com origem marcada como "
                    f"'{origem}' e destino '{destino}', e nenhum passo de "
                    f"pseudonimizacao roda antes. E o vazamento que nao passa "
                    f"por API nenhuma: sem rota, sem token de titular e sem "
                    f"log de acesso, o dado real vai parar num ambiente onde o "
                    f"controle de acesso e outro e a credencial raramente "
                    f"rotaciona. O pack de borda inteiro nao alcanca isto."),
                recomendacao=(
                    "Inserir um passo irreversivel de descaracterizacao entre "
                    "o dump e o restore — mascaramento, substituicao sintetica "
                    "ou tokenizacao sem tabela de volta. 'Staging com dado "
                    "real' e um pedido legitimo; a resposta e descaracterizar "
                    "no caminho, nao recusar o dado."),
                base_legal=BASE,
                arquivo=scan.rel(ctx.repo, p), linha=i,
                snippet=(originais[i - 1].strip()[:200]
                         if i <= len(originais) else None)))
    return findings
