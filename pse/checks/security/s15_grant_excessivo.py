"""S-15 — a role do banco: minimizacao decidida uma vez, herdada para sempre.

`GRANT SELECT ON ALL TABLES IN SCHEMA public` e uma frase curta que anula,
de uma vez, toda a minimizacao que o resto do sistema tenta fazer. E pior
que um endpoint permissivo por um motivo estrutural: o endpoint alguem
revisa quando muda; o grant e escrito numa migracao, no primeiro mes, e
nunca mais e olhado — e vale automaticamente para toda tabela criada
depois dele, inclusive as que ainda nao existem.

TRES VETORES, do mais amplo ao mais especifico:

  1. ALVO AMPLO — `ON ALL TABLES`. Concede sobre o que ainda vai existir.
  2. PRIVILEGIO AMPLO — `GRANT ALL PRIVILEGES`. Inclui DELETE e TRUNCATE
     numa role que costuma existir so para ler.
  3. TABELA COM PII SEM COLUNA — `GRANT SELECT ON clientes` entrega o CPF a
     quem so precisava da cidade. Este vetor cruza com o catalogo: sem
     inventario nao da para saber que a tabela carrega dado pessoal, e a
     ausencia de catalogo e cobrada por P-04, nao aqui.

D-08: `GRANT SELECT (id, cidade) ON clientes` — concessao por coluna — e a
minimizacao feita no lugar certo, e nao dispara nada. E o comportamento que
o check existe para produzir.

D-01: `scan.codigo_efetivo` apaga `-- comentario` e `/* bloco */` antes de
qualquer leitura. GRANT comentado nao concede nada e nao vira achado.
"""
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

BASE = "LGPD Art. 46 + Art. 6o III (minimizacao)"
REGUA = "backend-infra"

# `GRANT <privilegios> ON <alvo> TO <role>` — em uma linha ou varias.
RX_GRANT = re.compile(
    r"\bgrant\b(?P<priv>.*?)\bon\b(?P<alvo>.*?)\bto\b(?P<role>[^;]*)",
    re.IGNORECASE | re.DOTALL)
# A concessao por coluna: `SELECT (id, cidade)`.
RX_COLUNAS = re.compile(r"\([^)]*\)")


def _r(ctx, chave):
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def _tabelas_com_pii(ctx) -> set:
    cat = ctx.catalog()
    if cat is None:
        return set()                     # ausencia de catalogo e cobrada por P-04
    saida = set()
    for tabela, tmeta in (cat.get("tables") or {}).items():
        campos = ((tmeta or {}).get("fields") or {})
        if any((props or {}).get("class") in ("personal", "sensitive")
               for props in campos.values()):
            saida.add(str(tabela).lower())
    return saida


def _linha_de(texto: str, pos: int) -> int:
    return texto.count("\n", 0, pos) + 1


@check("S-15", "security", "Role de banco com privilegio excessivo", base_legal=BASE)
def grant_excessivo(ctx):
    privilegios_amplos = _r(ctx, "privilegios_amplos")
    alvos_amplos = _r(ctx, "alvos_amplos")
    com_pii = _tabelas_com_pii(ctx)
    findings = []

    for p in scan.arquivos(ctx.repo, {".sql"}):
        texto = scan.ler(p)
        efetivo = scan.codigo_efetivo(texto, ".sql")   # D-01
        originais = texto.splitlines()
        rel = scan.rel(ctx.repo, p)

        for m in RX_GRANT.finditer(efetivo):
            priv = m.group("priv").lower()
            alvo = m.group("alvo").lower()
            role = m.group("role").strip()
            por_coluna = bool(RX_COLUNAS.search(m.group("priv")))
            linha = _linha_de(efetivo, m.start())

            motivo = None
            if any(a in alvo for a in alvos_amplos):
                motivo = (
                    f"o alvo e amplo (`{next(a for a in alvos_amplos if a in alvo)}`): "
                    f"a concessao vale para toda tabela do schema, INCLUSIVE as "
                    f"que ainda nao existem — e ninguem vai revisitar esta "
                    f"migracao quando a proxima tabela de PII for criada")
            elif not por_coluna and any(
                    re.search(rf"\b{re.escape(a)}\b", priv)
                    for a in privilegios_amplos):
                motivo = (
                    "o privilegio e amplo (`ALL`): inclui escrita, DELETE e "
                    "TRUNCATE numa role que costuma existir apenas para ler")
            elif not por_coluna:
                tabela = next((t for t in com_pii
                               if re.search(rf"\b{re.escape(t)}\b", alvo)), None)
                if tabela:
                    motivo = (
                        f"a tabela `{tabela}` carrega dado pessoal segundo o "
                        f"catalogo, e a concessao e sobre a linha inteira — "
                        f"quem so precisava da cidade recebe tambem o "
                        f"identificador do titular")
            if not motivo:
                continue

            findings.append(Finding(
                check_id="S-15", pack="security", severidade=Severidade.ALTO,
                titulo=f"Concessao excessiva para a role `{role}`",
                descricao=(
                    f"Neste GRANT, {motivo}. Um grant e uma decisao de "
                    f"minimizacao tomada uma vez e herdada para sempre: "
                    f"diferente de um endpoint permissivo, ele nao volta a "
                    f"ser revisado quando o sistema muda."),
                recomendacao=(
                    "Conceder por COLUNA e por finalidade — "
                    "`GRANT SELECT (id, cidade) ON clientes TO app_readonly` — "
                    "e criar uma role por finalidade em vez de uma role "
                    "generica de leitura. Se a role precisa mesmo do schema "
                    "inteiro, ela e administrativa e nao deveria ser a "
                    "credencial da aplicacao."),
                base_legal=BASE, arquivo=rel, linha=linha,
                snippet=(originais[linha - 1].strip()[:200]
                         if linha <= len(originais) else None)))
    return findings
