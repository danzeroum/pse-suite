"""Gap 4 — prova de mutacao: todo check bloqueante tem inverso canonico.

Um check que nunca foi visto reprovando nada e uma hipotese, nao uma trava.
Cada check declara no catalogo a violacao minima que deve produzir vermelho;
check implementado sem mutacao declarada **reprova a si mesmo**.
"""
import pytest

from pse import catalogo, mutacao


@pytest.mark.mordida
@pytest.mark.parametrize("check_id", catalogo.implementados())
def test_mutacao_canonica_reprova(check_id):
    r = mutacao.provar(check_id)
    assert r["ok"], r["motivo"]


@pytest.mark.mordida
def test_todo_check_implementado_declara_mutacao():
    sem = [cid for cid in catalogo.implementados()
           if not catalogo.meta(cid).get("canonical_mutation")]
    assert not sem, (
        f"check(s) implementado(s) sem mutacao canonica: {sem}. "
        f"Sem inverso declarado, o check reprova a si mesmo.")


@pytest.mark.mordida
def test_check_sem_mutacao_reprova_a_si_mesmo(monkeypatch):
    """A trava contra a trava: se alguem registrar um check e esquecer a
    mutacao, a autoprova tem de acusar — nao passar batido."""
    monkeypatch.setitem(catalogo.CATALOGO, "P-01",
                        {**catalogo.meta("P-01"), "canonical_mutation": None})
    r = mutacao.provar("P-01")
    assert not r["ok"]
    assert "SEM mutacao canonica" in r["motivo"]


@pytest.mark.mordida
def test_mutacao_detecta_check_que_parou_de_morder(monkeypatch):
    """Se o check for neutralizado, a mutacao tem de acusar pelo nome."""
    from pse.engine.registry import CHECKS
    from pse.engine.runner import _carregar_checks
    _carregar_checks()
    monkeypatch.setitem(CHECKS, "P-06",
                        {**CHECKS["P-06"], "fn": lambda ctx: []})
    r = mutacao.provar("P-06")
    assert not r["ok"]
    assert "parou de morder" in r["motivo"]


@pytest.mark.mordida
def test_autoprova_completa_inclui_as_mutacoes():
    from pse.selftest import autoprova
    r = autoprova()
    assert r["ok"], r["motivo"]
    assert r["mutacoes"]["ok"]
    assert r["mutacoes"]["total"] == len(catalogo.implementados())
    # O motor local e interino por decisao (aprovacao §4b): a declaracao
    # sobrevive a troca de motor, o executor nao precisa sobreviver.
    assert r["mutacoes"]["interino"] is True
