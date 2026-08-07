"""P-13 — controle de consentimento que nasce ligado.

"Privacy by default" traduzido para a interface e uma frase so: o toggle
nasce DESLIGADO. Um checkbox de consentimento pre-marcado inverte o onus —
o titular passa a ter de recusar algo que nunca aceitou, e silencio vira
aceite. O Art. 8o §1o e explicito em exigir manifestacao inequivoca; um
default ligado nao manifesta nada, so registra inercia.

ANCORA NO FATO: a violacao e o VALOR INICIAL LITERAL sem handler de mudanca.
O material de fundacao propoe grep por "consent" — que casaria um comentario
`// consent default on` e perderia um `<input checked />` escrito em tres
linhas. Aqui a pergunta e feita a AST: este elemento tem `checked` literal?
tem handler? qual e o rotulo que o titular le ao lado dele?

D-08 — o padrao CORRETO nao pode ser punido. Um toggle que nasce ligado
porque reflete escolha ja registrada (`checked={consentimento.marketing}`,
com `onChange`) e exatamente o que se quer; puni-lo com CRITICO ensinaria o
time de frontend a ignorar o pack no primeiro dia.
"""
from pse.engine import scan
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.engine import jsast as _ast

BASE_LEGAL = "LGPD Art. 7o V e Art. 8o §1o (consentimento inequivoco)"

# Atributos que ligam o controle. `checked` sem valor em JSX e literal true.
LIGAM = ("checked", "defaultchecked", "defaultvalue", "value", "selected",
         "defaultselected")
LITERAIS_LIGADOS = ("", "{true}", "true", '"true"', "{1}")
CONTROLES = ("input", "toggle", "switch", "checkbox", "consent")


def _termos(ctx, grupo) -> set:
    return {t.lower() for t in ctx.data["frontend-terms"][grupo]}


def _e_controle(tag: str, attrs: dict) -> bool:
    baixo = tag.lower()
    if any(c in baixo for c in CONTROLES):
        return True
    tipo = (attrs.get("type") or "").strip("\"'{}").lower()
    return tipo in ("checkbox", "radio")


def _fala_de_consentimento(attrs: dict, rotulo: str, termos: set) -> bool:
    """O rotulo que o titular LE conta: nao e mencao, e o proprio controle."""
    alvo = " ".join([*attrs.keys(), *(v or "" for v in attrs.values()), rotulo])
    return any(t in alvo.lower() for t in termos)


def _nasce_ligado(attrs: dict) -> str | None:
    for nome, valor in attrs.items():
        if nome.lower() not in LIGAM:
            continue
        bruto = (valor or "").strip()
        if bruto.replace(" ", "").lower() in LITERAIS_LIGADOS:
            return nome
    return None


def _tem_handler(attrs: dict, handlers: set) -> bool:
    return any(n.lower() in handlers for n in attrs)


@check("P-13", "privacy", "Consentimento pre-marcado", base_legal=BASE_LEGAL)
def consentimento_pre_marcado(ctx):
    consent = _termos(ctx, "consentimento")
    handlers = _termos(ctx, "handlers_de_mudanca")
    findings = []

    # Arquivo ilegivel nao derruba os demais: ver `_ast.por_arquivo`.
    for p, texto, raiz in _ast.por_arquivo(ctx, findings):
        fonte = texto.encode("utf-8")

        for elem in _ast.elementos_jsx(raiz):
            attrs = _ast.atributos(elem, fonte)
            tag = _ast.tag_de(elem, fonte)
            if not _e_controle(tag, attrs):
                continue
            rotulo = _ast.texto_visivel(_ast.elemento_pai(elem), fonte)
            if not _fala_de_consentimento(attrs, rotulo, consent):
                continue
            ligado = _nasce_ligado(attrs)
            if not ligado:
                continue                       # nasce desligado — conforme
            if _tem_handler(attrs, handlers):
                continue                       # a escolha e do usuario
            linha = _ast.linha_de(elem)
            findings.append(Finding(
                check_id="P-13", pack="privacy", severidade=Severidade.CRITICO,
                titulo="Controle de consentimento nasce marcado",
                descricao=f"<{tag}> tem `{ligado}` com valor literal ligado e "
                          f"nenhum handler de mudanca. O titular passa a ter de "
                          f"RECUSAR algo que nunca aceitou, e silencio vira "
                          f"aceite — o oposto da manifestacao inequivoca que o "
                          f"Art. 8o §1o exige. Privacy by default, na interface, "
                          f"e uma frase so: o toggle nasce desligado.",
                recomendacao="Nascer desligado. Se o controle precisa refletir "
                             "escolha ja feita, ligar por estado "
                             "(checked={consentimento.x}) com onChange — nunca "
                             "por literal.",
                base_legal=BASE_LEGAL,
                arquivo=scan.rel(ctx.repo, p), linha=linha,
                snippet=_ast.texto_de(elem, fonte)[:200]))
    return findings
