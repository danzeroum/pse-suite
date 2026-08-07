"""Teste de aceite: a suite rodada contra um ALVO REAL, com baseline.

NOTA DE PROCEDENCIA, porque a honestidade sobre o proprio estado e a mesma
que se cobra do laudo: a rodada anterior descreveu esta infraestrutura como
"ja pronta". Ela nao estava — aquele bloco foi substituido antes de ser
executado, e este arquivo nasce agora.

O QUE UM ACEITE PROVA, E O QUE ELE NAO PROVA. A fixture prova que o CHECK
esta correto: dado um alvo sintetico com a violacao plantada, ele reprova.
O aceite prova outra coisa — que a REGUA reproduz um sistema de verdade,
com o volume, a bagunca e os falsos positivos que so codigo real tem. Um
sem o outro deixa metade sem prova, e a metade que falta e sempre a que
morde primeiro em producao.

COMO FUNCIONA. Um aceite e um arquivo declarativo em `aceites/` que diz:
qual alvo, que recorte, e o que se espera. A comparacao e por FAIXA, nunca
por numero exato: exigir "exatamente 5 achados de S-04" transformaria cada
commit do alvo numa quebra do aceite, e um aceite que quebra toda semana e
desligado no primeiro mes.

O QUE O BASELINE FIXA:
  * checks que TEM de executar (nao ficar pulados ou indeterminados);
  * checks que TEM de achar algo, e o piso de quantos;
  * checks que NAO PODEM achar nada;
  * o veredito e a faixa de exit code;
  * as linguagens que precisam estar dentro do alcance.

ALVO AUSENTE NAO E APROVACAO. Se o repositorio do alvo nao esta disponivel,
o aceite fica PENDENTE — com data e motivo — e nunca verde. E a mesma regra
que rege check sem alvo: nao ter olhado e diferente de ter olhado e nao
achado nada.
"""
import json
from pathlib import Path

import yaml

DIRETORIO = Path(__file__).resolve().parent.parent / "aceites"


def carregar(nome: str) -> dict:
    arq = DIRETORIO / f"{nome}.yaml"
    if not arq.exists():
        raise FileNotFoundError(f"aceite `{nome}` nao declarado em {DIRETORIO}")
    return yaml.safe_load(arq.read_text(encoding="utf-8")) or {}


def declarados() -> list:
    if not DIRETORIO.exists():
        return []
    return sorted(p.stem for p in DIRETORIO.glob("*.yaml"))


def alvo_disponivel(aceite: dict) -> tuple:
    """(disponivel, motivo). O motivo entra no skip — datado e especifico.

    Nunca devolve True por otimismo: se o caminho nao existe, o aceite nao
    roda, e o relatorio diz exatamente o que falta para ele rodar.
    """
    caminho = aceite.get("alvo", {}).get("caminho")
    if not caminho:
        return False, ("o aceite nao declara `alvo.caminho` — sem alvo nao ha "
                       "o que auditar, e a suite nao descobre alvo")
    p = Path(caminho)
    if not p.exists():
        return False, (
            f"alvo `{caminho}` nao esta disponivel neste ambiente. "
            f"{aceite.get('alvo', {}).get('como_obter', '')} "
            f"PENDENTE desde {aceite.get('pendente_desde', 'data nao declarada')}"
        ).strip()
    return True, ""


def comparar(laudo: dict, baseline: dict) -> list:
    """[] se o laudo satisfaz o baseline; senao, as divergencias.

    Divergencia e texto para humano, nao codigo de erro: quem le um aceite
    quebrado precisa saber o que mudou no alvo, nao qual assert falhou.
    """
    divergencias = []
    executados = set(laudo.get("checks_executados") or [])
    indeterminados = {c["id"] for c in laudo.get("checks_indeterminados") or []}
    pulados = {c["id"] for c in laudo.get("checks_pulados") or []}

    por_check = {}
    for f in laudo.get("findings") or []:
        por_check[f["check_id"]] = por_check.get(f["check_id"], 0) + 1

    for cid in baseline.get("devem_executar") or []:
        if cid not in executados:
            onde = ("indeterminado" if cid in indeterminados
                    else "pulado" if cid in pulados else "ausente")
            divergencias.append(
                f"{cid} deveria EXECUTAR e esta {onde} — o aceite existe para "
                f"pegar exatamente isto: um check que para de rodar contra o "
                f"alvo real sem ninguem notar")

    for cid, piso in (baseline.get("devem_achar") or {}).items():
        achou = por_check.get(cid, 0)
        if achou < int(piso):
            divergencias.append(
                f"{cid} achou {achou}, piso do baseline e {piso}. Ou o alvo "
                f"corrigiu o defeito (atualize o baseline, com a nota do "
                f"porque) ou o check parou de morder")

    for cid in baseline.get("nao_podem_achar") or []:
        if por_check.get(cid):
            divergencias.append(
                f"{cid} achou {por_check[cid]} e o baseline diz ZERO — "
                f"provavel falso positivo introduzido, que e o defeito mais "
                f"caro desta suite")

    esperado = baseline.get("veredito")
    if esperado and laudo.get("veredito") != esperado:
        divergencias.append(
            f"veredito {laudo.get('veredito')!r}, baseline esperava "
            f"{esperado!r}")

    faixa = baseline.get("exit_code_em") or []
    if faixa and laudo.get("exit_code") not in faixa:
        divergencias.append(
            f"exit_code {laudo.get('exit_code')} fora da faixa {faixa}")

    dentro = {x["linguagem"] for x in (laudo.get("alcance") or {}).get("lidos") or []}
    for lingua in baseline.get("linguagens_no_alcance") or []:
        if lingua not in dentro:
            divergencias.append(
                f"linguagem `{lingua}` deveria estar no alcance e nao esta — "
                f"a suite deixou de ler um estrato inteiro do alvo")

    fora = {x["linguagem"] for x in
            (laudo.get("alcance") or {}).get("fora_de_alcance") or []}
    for lingua in baseline.get("linguagens_fora_do_alcance") or []:
        if lingua not in fora:
            divergencias.append(
                f"`{lingua}` deveria constar como FORA de alcance e nao "
                f"consta. Se a suite ganhou parser para ela, atualize o "
                f"baseline; se o alvo parou de usa-la, idem. O que nao pode e "
                f"a lacuna sumir do laudo em silencio")

    # Alcance parcial: a linguagem nao e lida, e mesmo assim um conjunto
    # NOMEADO de checks a alcanca. O baseline fixa quais — porque o valor
    # desta linha e justamente que ela nao possa crescer em silencio: um
    # quinto check entrando faria o laudo afirmar cobertura que ninguem
    # revisou, e um saindo faria a cobertura encolher sem diff.
    parcial = {x["linguagem"]: set(x.get("checks") or []) for x in
               (laudo.get("alcance") or {}).get("alcance_parcial") or []}
    for lingua, checks in (baseline.get("alcance_parcial") or {}).items():
        if lingua not in parcial:
            divergencias.append(
                f"`{lingua}` deveria constar em alcance PARCIAL e nao consta — "
                f"o alcance textual aos vetores dela desapareceu")
        elif parcial[lingua] != set(checks):
            divergencias.append(
                f"os checks com alcance a `{lingua}` mudaram: baseline "
                f"{sorted(checks)}, laudo {sorted(parcial[lingua])}. Check que "
                f"entra ou sai muda o que o laudo afirma ter olhado")
    return divergencias


def executar_aceite(aceite: dict) -> dict:
    """Roda a suite contra o alvo declarado e devolve o laudo."""
    from pse.evidence import montar_laudo
    from pse.engine.runner import executar

    alvo = aceite["alvo"]
    recorte = aceite.get("recorte") or {}
    packs = set(recorte.get("pilares") or {"privacy", "security", "ethics"})
    doms = recorte.get("dominios")

    config = dict(aceite.get("config") or {})
    resultado = executar(Path(alvo["caminho"]), packs, config,
                         modo=recorte.get("modo", "pse_inventory"), doms=doms)
    return montar_laudo(Path(alvo["caminho"]), resultado, packs)


def relatorio(nome: str) -> dict:
    """Estado de um aceite: rodou, pendente, ou divergente — com o motivo."""
    aceite = carregar(nome)
    disponivel, motivo = alvo_disponivel(aceite)
    if not disponivel:
        return {"aceite": nome, "estado": "pendente", "motivo": motivo}
    laudo = executar_aceite(aceite)
    divergencias = comparar(laudo, aceite.get("baseline") or {})
    return {
        "aceite": nome,
        "estado": "conforme" if not divergencias else "divergente",
        "divergencias": divergencias,
        "exit_code": laudo.get("exit_code"),
        "veredito": laudo.get("veredito"),
        "alcance": laudo.get("alcance"),
    }


if __name__ == "__main__":                       # pragma: no cover
    for nome in declarados():
        print(json.dumps(relatorio(nome), indent=2, ensure_ascii=False))
