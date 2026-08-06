"""E-11 — dado pessoal cru entrando em prompt de modelo de linguagem.

E-05 e E-06 olham o VIES do modelo; nenhum dos dois olha o que ENTRA nele.
Um prompt e uma transferencia a terceiro como qualquer outra, com dois
agravantes: costuma sair pela borda mais nova e menos revisada do sistema, e
o destino pode reter o conteudo para treino. Dai o Art. 42 junto do 46 — quem
manda responde solidariamente pelo que o operador faz com o dado.

ANCORA NO FATO (D-01): so suprime o achado uma CHAMADA de redacao que
executa. `# TODO: redact` nao redige nada.

CUIDADO HERDADO DO D-08: a logica de argumentos e a mesma de P-01, importada
e nao reescrita. Redacao correta nao pode virar CRITICO — falso-positivo em
CRITICO ensina o operador a ignorar o laudo, e laudo ignorado nao protege
ninguem. Por isso o teste que prova que `redact(prompt)` NAO dispara vale
mais que o que prova que a violacao dispara.

A regua manda: fornecedores de LLM saem de `third-party-endpoints.yaml`
(categoria llm) e os termos de PII de `pii-patterns.yaml`. Nenhuma lista
mora neste arquivo.
"""
from pse.checks.privacy.p01_pii_em_logs import (_argumentos, _nome_pii,
                                                _valor_pii_literal)
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade
from . import _llm

BASE_LEGAL = "LGPD Art. 46 + Art. 42 (responsabilidade solidaria)"


def _termos(ctx) -> set:
    return {t.lower() for grupo in ctx.data["pii-patterns"].values() for t in grupo}


@check("E-11", "ethics", "PII em prompt de LLM", base_legal=BASE_LEGAL)
def pii_em_prompt(ctx):
    termos = _termos(ctx)
    findings = []
    for p in scan.arquivos(ctx.repo, {".py"}):
        arvore = scan.arvore(p)          # SyntaxError -> CheckIndeterminado
        texto = scan.ler(p)
        modulo_llm = _llm.modulo_fala_com_llm(
            scan.codigo_efetivo(texto, ".py", sem_literais=True), ctx)
        linhas = texto.splitlines()

        for no, nome in scan.chamadas(arvore):
            if not _llm.e_chamada_llm(nome, ctx, modulo_llm):
                continue
            motivo = None
            for arg in _argumentos(no):
                if _valor_pii_literal(arg):
                    motivo = "valor de dado pessoal escrito no proprio prompt"
                    break
                ident = _nome_pii(arg, termos)
                if ident:
                    motivo = f"'{ident}' e interpolado no prompt sem redacao"
                    break
            if not motivo:
                continue
            i = no.lineno
            findings.append(Finding(
                check_id="E-11", pack="ethics", severidade=Severidade.CRITICO,
                titulo="Prompt de LLM recebe dado pessoal sem redacao",
                descricao=f"A chamada `{nome}` envia dado pessoal a um modelo de "
                          f"linguagem ({motivo}). O prompt sai do perimetro para "
                          f"um operador que pode registra-lo, reproduzi-lo em "
                          f"outra resposta ou usa-lo para treino — e o "
                          f"controlador responde solidariamente por isso.",
                recomendacao="Redigir/pseudonimizar antes de montar o prompt "
                             "(funcao que EXECUTA, nao comentario); declarar o "
                             "fornecedor no manifesto com DPA e politica de "
                             "retencao zero para prompts.",
                base_legal=BASE_LEGAL,
                arquivo=scan.rel(ctx.repo, p), linha=i,
                snippet=linhas[i - 1].strip()[:200] if i <= len(linhas) else None))
    return findings
