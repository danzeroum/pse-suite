"""P-04 — catalogo vivo de dados.

Duas coisas que o plano §3 pede e que faltavam (D-10):

  1. **validacao contra o schema da suite** (`catalog-1.0.json`), e nao
     contra uma lista Python solta dentro do check — um schema versionado e
     o que o consumidor consegue ler para saber o que se espera dele;
  2. **laudo de cobertura do catalogo**: quantos campos existem, quantos
     estao completos, quantos sao sensiveis. Sem isso o consumidor so sabe
     o que esta errado, nunca o quanto ja esta certo.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.schemas_validate import erros_de

OBRIGATORIOS = ["class", "owner", "purpose", "legal_basis", "retention_years"]


def _cobertura(cat, sensiveis) -> dict:
    total = completos = marcados_sensiveis = 0
    for tmeta in (cat.get("tables") or {}).values():
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            props = props or {}
            total += 1
            if all(k in props for k in OBRIGATORIOS):
                completos += 1
            if props.get("class") == "sensitive" or campo in sensiveis:
                marcados_sensiveis += 1
    return {
        "campos_catalogados": total,
        "campos_completos": completos,
        "campos_incompletos": total - completos,
        "campos_sensiveis": marcados_sensiveis,
        "percentual_completo": round(100 * completos / total, 1) if total else 0.0,
        "tabelas": len(cat.get("tables") or {}),
    }


@check("P-04", "privacy", "Catalogo vivo de dados", base_legal="LGPD Art. 37")
def catalogo(ctx):
    cat = ctx.catalog()
    caminho = ctx.catalog_path()
    if cat is None:
        ctx.relatorio("cobertura_catalogo", {"presente": False})
        return [Finding(
            check_id="P-04", pack="privacy", severidade=Severidade.ALTO,
            titulo="Catalogo de dados ausente",
            descricao="Sem inventario (campo -> classe, dono, finalidade, base "
                      "legal, retencao) nenhum outro controle de privacidade opera.",
            recomendacao=f"Criar {caminho} conforme pse/schemas/catalog-1.0.json.",
            base_legal="LGPD Art. 37", arquivo=caminho, linha=1)]

    sensiveis = set(ctx.data["sensitive-fields"]["sensiveis"])
    relatorio = _cobertura(cat, sensiveis)
    relatorio["presente"] = True
    ctx.relatorio("cobertura_catalogo", relatorio)

    findings = []

    # 1. Coerencia semantica — a mensagem mais acionavel, entao vem primeiro:
    #    campo da lista curada de sensiveis tem de estar classificado como tal,
    #    e campo sem metadado obrigatorio tem de ser nomeado.
    for tabela, tmeta in (cat.get("tables") or {}).items():
        for campo, props in ((tmeta or {}).get("fields") or {}).items():
            props = props or {}
            if props.get("status") == "prohibited":
                continue
            linha = ctx.linha_no_catalogo("tables", tabela, "fields", campo)
            faltando = [k for k in OBRIGATORIOS if k not in props]
            if faltando:
                findings.append(Finding(
                    check_id="P-04", pack="privacy", severidade=Severidade.MEDIO,
                    titulo=f"Campo {tabela}.{campo} com metadados incompletos",
                    descricao=f"Metadados ausentes no catalogo: {', '.join(faltando)}.",
                    recomendacao="Completar classe, dono, finalidade, base legal e retencao.",
                    base_legal="LGPD Art. 37", arquivo=caminho, linha=linha))
            if campo in sensiveis and props.get("class") != "sensitive":
                findings.append(Finding(
                    check_id="P-04", pack="privacy", severidade=Severidade.ALTO,
                    titulo=f"Campo {tabela}.{campo} sensivel classificado como "
                           f"'{props.get('class')}'",
                    descricao="Campo consta na lista curada de dados sensiveis "
                              "(Art. 5o II) mas nao esta classificado como sensitive.",
                    recomendacao="Reclassificar como sensitive e revisar base legal.",
                    base_legal="LGPD Art. 5o II", arquivo=caminho, linha=linha))

    # 2. Conformidade estrutural com o schema versionado da suite — so para
    #    o que o loop semantico NAO cobriu. Os dois caminhos apontam o mesmo
    #    defeito de angulos diferentes, e reportar duas vezes o mesmo campo e
    #    o ruido que ensina o operador a ignorar o laudo (D-09).
    cobertas = {f.linha for f in findings}
    for erro in erros_de("catalog-1.0.json", cat):
        chaves = [p for p in erro.path if isinstance(p, str)]
        linha = ctx.linha_no_catalogo(*chaves) if chaves else 1
        if linha in cobertas:
            continue
        cobertas.add(linha)
        caminho_erro = "/".join(map(str, erro.path)) or "<raiz>"
        findings.append(Finding(
            check_id="P-04", pack="privacy", severidade=Severidade.MEDIO,
            titulo=f"Catalogo fora do schema em '{caminho_erro}'",
            descricao=f"{erro.message} (schema catalog-1.0).",
            recomendacao="Ajustar o catalogo ao schema publicado pela suite "
                         "em pse/schemas/catalog-1.0.json.",
            base_legal="LGPD Art. 37", arquivo=caminho, linha=linha))
    return findings
