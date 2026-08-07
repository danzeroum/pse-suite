"""Prova de mutacao — Gap 4, o inverso canonico de cada check.

Um check que nunca foi visto reprovando nada e uma hipotese, nao uma trava.
Cada check bloqueante declara no catalogo a **violacao minima que deve
produzir vermelho**; a release so sai se todas reproduzirem, e check
implementado sem mutacao declarada **reprova a si mesmo**.

Separacao deliberada entre dado e motor (aprovacao §4b): a declaracao vive
no catalogo — e estavel, revisavel e sobrevive a troca de motor. Este
executor e **interino**, marcado como tal: se o `mutation-engine`
compartilhado da CP-A se materializar, ele consome as mesmas declaracoes e
este arquivo e deletado sem tocar em nenhum catalogo.
"""
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

from pse import catalogo
from pse.engine.context import Contexto
from pse.engine.registry import CHECKS
from pse.engine.runner import _carregar_checks
from pse.model import CheckIndeterminado, NaoHabilitado, SkipCheck

INTERINO = True   # ver docstring: motor local ate a CP-A ser confirmada


def _materializar(destino: Path, arquivos: dict):
    for nome, conteudo in (arquivos or {}).items():
        alvo = destino / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(conteudo, encoding="utf-8")


BASE_URL_MUT = "https://alvo-de-mutacao.invalido"
TOKEN_ENV = "PSE_TOKEN_MUTACAO"


class TransporteFalso:
    """Responde da lista declarada, em ordem; repete a ultima quando acaba.

    O healthcheck e respondido 200 automaticamente: a mutacao descreve o
    DEFEITO do alvo, nao a plumbing de estar de pe. E a contagem de chamadas
    fica exposta, porque e ela que prova que nada foi enviado cedo demais.
    """

    def __init__(self, respostas, healthcheck="/health"):
        self.respostas = list(respostas or [])
        self.healthcheck = healthcheck
        self.chamadas = []
        self._i = 0

    def enviar(self, metodo, url, headers, corpo, timeout):
        from pse.trabalho_a.cliente import Resposta
        self.chamadas.append((metodo, url))
        if url.endswith(self.healthcheck):
            return Resposta(200, "{}", {})
        if not self.respostas:
            return Resposta(404, "{}", {})
        r = self.respostas[min(self._i, len(self.respostas) - 1)]
        self._i += 1
        return Resposta(r.get("status", 200), r.get("corpo", ""), {})


def _config_runtime(rt: dict) -> dict:
    """Sintetiza o alvo e a atestacao valida declarados por `autorizacao_valida`.

    A mutacao prova o CHECK, nao a atestacao — esta tem testes proprios. Por
    isso o prazo e computado no futuro em vez de escrito no YAML: uma data
    fixa faria a suite inteira reprovar sozinha ao vencer.
    """
    from pse.trabalho_a.autorizacao import fingerprint_alvo
    alvo = {
        "base_url": BASE_URL_MUT,
        "environment": "staging",
        "healthcheck": "/health",
        "identities": {"titular_a": {"token_env": TOKEN_ENV},
                       "titular_b": {"token_env": TOKEN_ENV}},
        "endpoints": dict(rt.get("endpoints") or {}),
        "resources_titular_b": list(rt.get("recursos_b") or []),
    }
    if rt.get("autorizacao_valida"):
        alvo["authorization"] = {
            "attested_by": "mutacao@pse-suite",
            "scope": ["pse_passive", "pse_active"],
            "target_fingerprint": fingerprint_alvo(BASE_URL_MUT),
            "expires": (date.today() + timedelta(days=365)).isoformat(),
            "synthetic_identities": True,
        }
    return {"target": alvo}


def _observador_declarado(nav: dict):
    """Constroi um NetworkLog a partir da mutacao declarada no catalogo.

    A mutacao canonica de um check de NAVEGADOR nao pode depender de um
    navegador: a autoprova roda em `pse --self-test`, que e o comando que o
    consumidor executa para conferir se a suite ainda morde — e ele nao pode
    exigir Playwright instalado para responder.

    O que se prova aqui e a REGRA do check (o que separa achado de
    nao-achado), com a observacao declarada em YAML como todo o resto. Que o
    motor de fato observa um alvo real e outra prova, e ela vive em
    `tests/test_navegador.py`, contra o alvo de fixture. Duas perguntas
    diferentes, duas provas diferentes — juntar as duas faria a autoprova
    depender de binario de navegador sem ganhar nada.
    """
    from pse.navegador.rede import (CookieObservado, NetworkLog,
                                    RequisicaoObservada)
    log = NetworkLog(
        url=nav.get("url", "https://alvo-de-mutacao.invalido/"),
        requisicoes=tuple(RequisicaoObservada(r.get("url", ""), r.get("tipo", ""))
                          for r in (nav.get("requisicoes") or [])),
        cookies=tuple(CookieObservado(
            name=c.get("name", ""), httpOnly=bool(c.get("httpOnly")),
            secure=bool(c.get("secure")), sameSite=str(c.get("sameSite") or ""))
            for c in (nav.get("cookies") or [])),
        html=nav.get("html", ""), engine="mutacao")

    def observar(url, engine=None, user_agent=None, data=None, **_):
        return log
    return observar


def provar(check_id: str) -> dict:
    """Aplica a mutacao canonica do check e exige que ele a encontre."""
    _carregar_checks()
    meta_cat = catalogo.meta(check_id)
    mut = meta_cat.get("canonical_mutation")

    if not mut:
        return {"check": check_id, "ok": False,
                "motivo": "check implementado SEM mutacao canonica declarada — "
                          "um check que nunca foi visto reprovando nada nao e "
                          "uma trava, e por isso reprova a si mesmo"}

    registrado = CHECKS.get(check_id)
    if not registrado:
        return {"check": check_id, "ok": False,
                "motivo": "declarado como implementado mas nao registrado"}

    esperada = mut.get("espera_severidade")
    rt = mut.get("runtime")
    nav = mut.get("navegador")
    with tempfile.TemporaryDirectory(prefix="pse-mut-") as tmp:
        alvo = Path(tmp)
        _materializar(alvo, mut.get("arquivos"))
        if nav:
            # Check de navegador: alvo e atestacao sinteticos (o contrato tem
            # provas proprias), observacao vinda do YAML.
            config = _config_runtime({"autorizacao_valida": True})
            transporte = TransporteFalso([])
            os.environ.setdefault(TOKEN_ENV, "token-sintetico-de-mutacao")
            ctx = Contexto(alvo, config, modo="pse_passive",
                           transporte=transporte,
                           observador=_observador_declarado(nav))
        elif rt:
            config = _config_runtime(rt)
            transporte = TransporteFalso(rt.get("respostas"))
            os.environ.setdefault(TOKEN_ENV, "token-sintetico-de-mutacao")
            ctx = Contexto(alvo, config, modo=rt.get("modo", "pse_active"),
                           transporte=transporte)
        else:
            ctx = Contexto(alvo, dict(mut.get("config") or {}))
        try:
            achados = registrado["fn"](ctx) or []
        except SkipCheck as e:
            return {"check": check_id, "ok": False,
                    "motivo": f"a mutacao nao chegou a ser avaliada (pulado): {e}"}
        except NaoHabilitado as e:
            return {"check": check_id, "ok": False,
                    "motivo": f"a mutacao nao habilitou o check: {e}"}
        except CheckIndeterminado as e:
            return {"check": check_id, "ok": False,
                    "motivo": f"a mutacao deixou o check indeterminado: {e}"}
        except Exception as e:  # noqa: BLE001
            return {"check": check_id, "ok": False,
                    "motivo": f"erro ao avaliar a mutacao: {type(e).__name__}: {e}"}

    meus = [f for f in achados if f.check_id == check_id]
    if not meus:
        return {"check": check_id, "ok": False,
                "motivo": f"a mutacao canonica NAO produziu vermelho "
                          f"({mut.get('descricao')}) — o check parou de morder"}

    severidades = {f.severidade.value for f in meus}
    if esperada and esperada not in severidades:
        return {"check": check_id, "ok": False,
                "motivo": f"mutacao produziu {sorted(severidades)}, "
                          f"esperado {esperada}"}

    return {"check": check_id, "ok": True,
            "motivo": f"reprovou como esperado ({esperada}): {mut.get('descricao')}",
            "achados": len(meus)}


def provar_todas() -> dict:
    """Toda a autoprova de mutacao. Nenhum check implementado escapa."""
    resultados = [provar(cid) for cid in catalogo.implementados()]
    falhas = [r for r in resultados if not r["ok"]]
    return {
        "ok": not falhas,
        "interino": INTERINO,
        "total": len(resultados),
        "falhas": falhas,
        "provados": [r["check"] for r in resultados if r["ok"]],
    }
