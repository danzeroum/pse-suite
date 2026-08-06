"""S-05 — payload minimo de egresso: o que sai para cada terceiro.

ESTATICO. S-04 pergunta QUEM esta registrado; S-05 pergunta O QUE vai para
cada um. Sao coisas diferentes: um DPA assinado com um analytics nao
autoriza mandar CPF para ele.

Exige que cada integracao do manifesto declare `egress_fields` e cruza a
lista com a regua curada — campo sensivel ou identificador direto saindo
para terceiro e achado, mesmo com DPA em ordem. Integracao sem
`egress_fields` declarados tambem e achado: egresso nao declarado e egresso
desconhecido, e nao se minimiza o que nao se sabe que sai.

ESCOPO DESTA VERSAO: a metade estatica. A observacao por proxy em ambiente
de teste, que o plano §3 tambem preve, exige um proxy declarado no contrato
de Trabalho A — que ainda nao existe. Ausencia conhecida e declarada, no
mesmo padrao ratificado para o webhook de S-03.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade, SkipCheck

IDENTIFICADORES_DIRETOS = {"cpf", "rg", "cnh", "passaporte", "cns",
                           "titulo_eleitor", "email", "telefone", "celular",
                           "endereco", "nome_completo"}


@check("S-05", "security", "Payload minimo de egresso", base_legal="LGPD Art. 6o III")
def egresso(ctx):
    manifesto = ctx.manifest_terceiros()
    if manifesto is None:
        raise SkipCheck("manifesto de terceiros ausente — cobrado por S-04")

    sensiveis = {t.lower() for t in ctx.data["sensitive-fields"]["sensiveis"]}
    ctx.relatorio("cobertura_parcial", {
        **ctx.relatorios.get("cobertura_parcial", {}),
        "S-05": "metade estatica apenas; observacao por proxy de egresso exige "
                "receptor declarado no contrato de Trabalho A (ausencia conhecida)"})

    findings = []
    for item in manifesto.get("integrations", []):
        nome = item.get("name")
        linha = ctx.linha_da_integracao(nome)
        campos = item.get("egress_fields")

        if campos is None:
            findings.append(Finding(
                check_id="S-05", pack="security", severidade=Severidade.ALTO,
                titulo=f"Integracao '{nome}' sem payload de egresso declarado",
                descricao="O manifesto registra o terceiro mas nao diz que "
                          "campos saem para ele. Egresso nao declarado e "
                          "egresso desconhecido — nao se minimiza o que "
                          "ninguem sabe que sai.",
                recomendacao="Declarar `egress_fields` por integracao e revisar "
                             "campo a campo contra a finalidade contratada.",
                base_legal="LGPD Art. 6o III",
                arquivo=ctx.manifesto_path(), linha=linha))
            continue

        proibidos = sorted({c for c in map(str.lower, campos)
                            if c in sensiveis or c in IDENTIFICADORES_DIRETOS})
        if not proibidos:
            continue
        justificados = {c.lower() for c in (item.get("egress_justificados") or [])}
        restantes = [c for c in proibidos if c not in justificados]
        if not restantes:
            continue
        findings.append(Finding(
            check_id="S-05", pack="security", severidade=Severidade.ALTO,
            titulo=f"Integracao '{nome}' envia dado identificavel a terceiro",
            descricao=f"Campos no egresso: {restantes}. DPA assinado autoriza o "
                      f"tratamento, nao dispensa a minimizacao: cada campo que "
                      f"sai precisa ser necessario a finalidade contratada.",
            recomendacao="Remover, pseudonimizar ou agregar os campos; se algum "
                         "for indispensavel, declara-lo em `egress_justificados` "
                         "com a finalidade que o exige.",
            base_legal="LGPD Art. 6o III",
            arquivo=ctx.manifesto_path(), linha=linha))
    return findings
