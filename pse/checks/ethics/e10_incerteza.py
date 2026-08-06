"""E-10 — decisao pontual sem incerteza quantificada.

ESTATICO. Um escore devolvido como numero unico esconde a diferenca entre
"reprovado com folga" e "reprovado por um ponto, com o modelo em duvida".
E e exatamente no segundo caso que a revisao humana deveria ser acionada —
mas nao ha como aciona-la sem a incerteza.

ANCORA NO FATO: procura a CHAMADA de inferencia e pergunta se a mesma
funcao produz alguma medida de incerteza. Mencao em comentario nao mede
nada, e severidade MEDIA por decisao do plano §3: e boa pratica ausente,
nao violacao legal — nao pode bloquear.
"""
import ast
import re

from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

RX_INFERENCIA = re.compile(r"^(predict|infer|score|pontuar|classificar)$", re.I)
RX_INCERTEZA = re.compile(
    r"predict_proba|proba|confian|confidence|incerteza|uncertainty|intervalo"
    r"|interval|desvio|std|variance|entropy|entropia|margem", re.I)


def _mede_incerteza(fn) -> bool:
    for sub in ast.walk(fn):
        if isinstance(sub, ast.Call) and RX_INCERTEZA.search(scan.nome_chamado(sub)):
            return True
        if isinstance(sub, ast.Name) and RX_INCERTEZA.search(sub.id):
            return True
        if isinstance(sub, ast.Attribute) and RX_INCERTEZA.search(sub.attr):
            return True
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str) \
                and RX_INCERTEZA.search(sub.value):
            return True
    return False


@check("E-10", "ethics", "Incerteza quantificada", base_legal="robustez")
def incerteza(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)        # SyntaxError -> CheckIndeterminado
        for no in ast.walk(arvore):
            if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            infere = any(RX_INFERENCIA.match(nome.split(".")[-1])
                         for _, nome in scan.chamadas(no))
            if not infere or _mede_incerteza(no):
                continue
            findings.append(Finding(
                check_id="E-10", pack="ethics", severidade=Severidade.MEDIO,
                titulo=f"Decisao de '{no.name}' sem incerteza quantificada",
                descricao="A funcao produz uma inferencia pontual e nao calcula "
                          "nenhuma medida de confianca. Sem isso, decisao "
                          "limitrofe e decisao folgada sao indistinguiveis — e "
                          "e a limitrofe que precisa de revisao humana.",
                recomendacao="Devolver probabilidade/intervalo junto do escore e "
                             "rotear os casos de baixa confianca para analise.",
                base_legal="robustez / EbD-AI",
                arquivo=scan.rel(ctx.repo, p), linha=no.lineno,
                snippet=f"def {no.name}(...)"))
            break                       # um por arquivo — politica de ruido
    return findings
