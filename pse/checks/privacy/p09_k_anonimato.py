"""P-09 — k-anonimato em agregacoes.

DUAS METADES, ambas contra o mesmo risco: uma celula de agregacao com
poucos titulares nao e estatistica, e uma lista nominal com outro nome. Um
relatorio que mostra "1 pessoa no bairro X com a doenca Y" identificou
alguem, por mais agregado que pareca o SQL.

ESTATICA: agregacao com GROUP BY e sem clausula de supressao.
RUNTIME (MODO ATIVO): consulta o endpoint de agregacao declarado e procura
contagem abaixo do piso. E ativa porque a sonda tenta obter justamente o que
o sistema deveria suprimir — na duvida entre passivo e ativo, ativo.

O piso `k` vem de `thresholds.k_anonymity_min`, e a suite valida a faixa: o
consumidor pode aumentar, nunca afrouxar (pse/limites.py).
"""
import re

from pse import limites
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, NaoHabilitado, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo

RX_GROUP_BY = re.compile(r"\bGROUP\s+BY\b", re.I)
RX_SUPRESSAO = re.compile(r"\bHAVING\b[^;]*\bCOUNT\s*\(", re.I)
RX_CONTAGEM = re.compile(r"(count|total|n|qtd|quantidade|frequencia)$", re.I)


def _estatico(ctx, k, findings):
    for p in scan.arquivos(ctx.repo, {".sql", ".py"}):
        texto = scan.codigo_efetivo(scan.ler(p), p.suffix)
        if not RX_GROUP_BY.search(texto) or RX_SUPRESSAO.search(texto):
            continue
        linha = next((i for i, l in enumerate(texto.splitlines(), 1)
                      if RX_GROUP_BY.search(l)), 1)
        findings.append(Finding(
            check_id="P-09", pack="privacy", severidade=Severidade.ALTO,
            titulo="Agregacao sem supressao de celula rara",
            descricao=f"Consulta agrega com GROUP BY e nao filtra celulas "
                      f"pequenas (HAVING COUNT(*) >= {k}). Uma celula com "
                      f"poucos titulares reidentifica: agregado nao e anonimo "
                      f"por definicao, e sim por tamanho.",
            recomendacao=f"Adicionar HAVING COUNT(*) >= {k} e suprimir ou "
                         f"agrupar as celulas abaixo do piso.",
            base_legal="reidentificacao / LGPD Art. 12",
            arquivo=scan.rel(ctx.repo, p), linha=linha))


def _celulas_pequenas(dado, k, achadas):
    if isinstance(dado, dict):
        for chave, v in dado.items():
            if isinstance(v, int) and not isinstance(v, bool) \
                    and RX_CONTAGEM.search(str(chave)) and 0 < v < k:
                achadas.append((str(chave), v))
            else:
                _celulas_pequenas(v, k, achadas)
    elif isinstance(dado, list):
        for v in dado:
            _celulas_pequenas(v, k, achadas)


def _runtime(ctx, k, findings):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "agregacao")

    resposta, trace = cliente.requisitar("GET", rota, token=token_a,
                                         identidade="titular_a")
    achadas = []
    _celulas_pequenas(resposta.json(), k, achadas)
    if not achadas:
        return
    amostra = ", ".join(f"{c}={v}" for c, v in achadas[:3])
    findings.append(Finding(
        check_id="P-09", pack="privacy", severidade=Severidade.ALTO,
        titulo="Agregacao exposta devolve celula abaixo do piso de k",
        descricao=f"A resposta traz {len(achadas)} contagem(ns) menor(es) que "
                  f"k={k} ({amostra}). Quem consulta o relatorio consegue "
                  f"isolar individuos a partir do agregado.",
        recomendacao=f"Suprimir no servidor toda celula com menos de {k} "
                     f"titulares, devolvendo faixa ou omissao explicita.",
        base_legal="reidentificacao / LGPD Art. 12",
        arquivo=rota, linha=1, trace=trace))


@check("P-09", "privacy", "k-anonimato em agregacoes", base_legal="reidentificacao")
def k_anonimato(ctx):
    k = limites.valor(ctx.config, "k_anonymity_min")
    findings = []
    _estatico(ctx, k, findings)
    try:
        _runtime(ctx, k, findings)
    except NaoHabilitado as e:
        ctx.relatorio("cobertura_parcial", {
            **ctx.relatorios.get("cobertura_parcial", {}),
            "P-09": f"metade runtime nao executada: {e}"})
    return findings
