"""Gerador do mapa pilar x dominio.

    python -m pse.matriz > docs/matriz-dominio.md

O documento e derivado do catalogo, nunca escrito a mao — pelo mesmo motivo
que `docs/pse-coverage.md` do plano §5.4 e gerado: um mapa mantido a mao
diverge do territorio no primeiro check novo, e um mapa errado e pior que
mapa nenhum porque parece confiavel. Ha teste que reprova se o arquivo
versionado divergir do catalogo.

As LEITURAS das celulas vazias e das densidades sao editoriais e ficam
declaradas aqui, nao inferidas: dizer "falta check" ou "nao se aplica" e
julgamento, e julgamento tem de estar assinado em algum lugar.
"""
from collections import defaultdict

from pse import catalogo

PILARES = ("privacy", "security", "ethics")

# Julgamento sobre cada celula vazia. Vazio nao e defeito por definicao — e
# pergunta; o que nao pode e ficar sem resposta.
LEITURA_DOS_BURACOS = {
    ("ethics", "frontend"):
        "**Falta check.** O material de fundacao tem farto insumo aqui — dark "
        "pattern, recusar mais dificil que aceitar, desinformacao de interface. "
        "Ficou fora do pacote fundador de proposito: exige julgamento, e AST "
        "sozinha nao decide se um botao e coercitivo.",
}

# Buracos que a matriz expos e que ja foram fechados. Ficam registrados: e a
# historia que mostra o mapa cumprindo a funcao — apagar seria perder a prova
# de que a celula vazia virou pergunta, e a pergunta virou check.
BURACOS_FECHADOS = {
    ("security", "ai"):
        "Estava vazio. Fechado por **S-10** (injecao de prompt: instrucao "
        "concatenada, caractere invisivel, token flooding) e **S-11** (saida do "
        "modelo em sink perigoso). Nasceram olhando o estrato.",
    ("privacy", "ai"):
        "Existia so de rabo de olho, via ethics. Fechado por **P-15** (dado "
        "pessoal como feature de treino sem finalidade declarada) e **P-16** "
        "(dataset de treino sem governanca).",
}

# Risco investigado e deliberadamente NAO transformado em check. Distinto de
# um buraco de celula: aqui ha check POSSIVEL em tese, e a decisao foi que
# ele nao seria verificavel de verdade neste artefato. Fica assinado porque
# "nao implementei" e "nao existe risco" sao coisas opostas, e so a segunda
# seria mentira.
FORA_DE_ESCOPO_ESTATICO = {
    ("data", "zona_bruta"):
        "**P-21 — zona bruta de data lake com acesso irrestrito. Investigado, "
        "NAO implementado.** Tres razoes, nesta ordem. (1) A identificacao da "
        "zona bruta viria do NOME do bucket (`raw`, `bronze`, `landing`): isso "
        "e mencao, nao fato, e o D-01 proibe exatamente esse atalho — num "
        "check cuja consequencia seria bloquear CI. (2) Uma policy sem "
        "`Condition` no Terraform nao e violacao por si: a restricao pode "
        "viver numa SCP, num permission boundary, num grant de Lake Formation "
        "ou no provedor de identidade, todos FORA do repositorio. O check "
        "acusaria setup correto — o D-08 ao contrario. (3) A suite nao tem "
        "parser de HCL, e adicionar um para avaliar uma forma de politica que "
        "nao se consegue decidir seria construir a aparencia de cobertura. "
        "**O que faria P-21 nascer:** um artefato de policy-as-code versionado "
        "que declare finalidade e expiracao por zona — ai ha declaracao a "
        "confrontar com fato, que e como todos os outros funcionam. Buraco "
        "honesto e melhor que check que nao verifica nada real.",
}

LEITURA_DA_DENSIDADE = {
    "frontend":
        "Primeiro dominio cujos checks foram desenhados OLHANDO para ele "
        "(P-13, P-14, S-09 nasceram do estrato) e o UNICO auditado nas duas "
        "camadas: **oito dos onze sao DINAMICOS** — carregam a pagina num "
        "navegador e observam o que so o navegador ve. Fase 1 (P-22, S-17, "
        "P-23) olha requisicao, cookie e URL; Fase 2 (S-18, S-19, S-20, "
        "P-24, S-21) le o CORPO servido: terceiro contactado, cabecalho, "
        "credencial no bundle, EXIF e sourcemap. E aqui que contrato e "
        "observacao se encontram, e por isso e aqui que moram os quatro "
        "pares de correlacao estatico x dinamico.",
    "api":
        "**S-12, P-17 e S-13 nasceram do estrato** — do contrato, do filtro de "
        "busca e do payload de erro. Os demais continuam sendo classificacao a "
        "posteriori: vieram do Trabalho A e do inventario e foram etiquetados "
        "depois. Era a leitura critica que a propria matriz fazia deste "
        "dominio, e ela deixou de valer para o pacote fundador.",
    "backend":
        "**S-14, S-15, P-18, P-19 e S-16 nasceram do estrato** — do dump que "
        "viaja entre ambientes, da role do banco, da coluna cifrada, do topico "
        "imutavel e da regiao onde o byte pousa. Nenhum desses vetores tem "
        "equivalente em outro dominio. Os demais seguem sendo os estaticos do "
        "inventario, reclassificados.",
    "data":
        "Aqui a densidade nunca foi heranca preguicosa: `data` e o estrato "
        "ONDE A SUITE NASCEU — catalogo, retencao, k-anonimato e lineage "
        "vieram olhando para ele. Sobrou um buraco, e **P-20 o fecha**: hash "
        "deterministico sem chave tratado como anonimizacao, o risco que "
        "engana por parecer resolvido. S-15, P-18 e P-19 aparecem nesta "
        "coluna por inspecionarem artefato de dados (catalogo, schema, log de "
        "eventos), mas nasceram olhando o BACKEND — sao multi-dominio, nao "
        "fundadores daqui.",
    "ai":
        "Os quatro mais novos (S-10, S-11, P-15, P-16) nasceram do estrato; os "
        "demais foram etiquetados a posteriori. Primeiro dominio herdado a "
        "receber checks proprios.",
}


def _celulas():
    celula, por_dominio = defaultdict(list), defaultdict(list)
    for cid in sorted(catalogo.CATALOGO):
        pack = catalogo.CATALOGO[cid]["pack"]
        for d in catalogo.dominios(cid):
            celula[(pack, d)].append(cid)
            por_dominio[d].append(cid)
    return celula, por_dominio


def gerar() -> str:
    doms = list(catalogo.DOMINIOS)
    celula, por_dominio = _celulas()
    total = len(catalogo.CATALOGO)
    L = [f"# Matriz pilar x dominio — os {total} checks", ""]
    L += ["> **Gerado**, nunca escrito a mao: "
          "`python -m pse.matriz > docs/matriz-dominio.md`.",
          "> Ha teste que reprova se este arquivo divergir do catalogo — um mapa",
          "> errado e pior que mapa nenhum, porque parece confiavel.", ""]
    L += ["Duas dimensoes ortogonais. O **pilar** responde *que valor esta em "
          "jogo*;", "o **dominio**, *onde ele se manifesta no sistema*. O prefixo "
          "do ID codifica", "o pilar — a unica das duas que e univalorada; o "
          "dominio e lista, porque", "um check pode examinar mais de um estrato.", ""]

    L += ["## Grade", ""]
    L.append("| | " + " | ".join(doms) + " | total no pilar |")
    L.append("|---|" + "---|" * (len(doms) + 1))
    for p in PILARES:
        linha = [f"**{p}**"]
        for d in doms:
            ids = celula[(p, d)]
            linha.append(" ".join(ids) if ids else "**—**")
        linha.append(str(len([c for c in catalogo.CATALOGO
                              if catalogo.CATALOGO[c]["pack"] == p])))
        L.append("| " + " | ".join(linha) + " |")
    L.append("| **total no dominio** | " +
             " | ".join(str(len(por_dominio[d])) for d in doms) +
             f" | {total} |")
    soma = sum(len(por_dominio[d]) for d in doms)
    L += ["", f"A soma da ultima linha ({soma}) e maior que {total} porque um "
          "check aparece em", "mais de uma coluna quando examina mais de um "
          "estrato. Nao e erro de contagem:", "e a multiplicidade do dominio, "
          "que e exatamente a razao de ele nao caber", "no prefixo do ID.", ""]

    vazias = [(p, d) for p in PILARES for d in doms if not celula[(p, d)]]
    L += ["## Buracos", "",
          "Celula vazia nao e defeito por definicao — e pergunta. O que nao "
          "pode e ficar", "sem resposta: cada uma abaixo precisa de um *nao se "
          "aplica* ou de um", "*falta check*, assinado.", ""]
    L += ["| Pilar x dominio | Leitura |", "|---|---|"]
    for p, d in vazias:
        L.append(f"| `{p}` x `{d}` | "
                 f"{LEITURA_DOS_BURACOS.get((p, d), '**Sem leitura declarada.**')} |")
    L.append("")
    if BURACOS_FECHADOS:
        L += ["### Buracos ja fechados", "",
              "Ficam registrados: e a historia que mostra o mapa cumprindo a "
              "funcao — a", "celula vazia virou pergunta, e a pergunta virou "
              "check.", "",
              "| Pilar x dominio | Como foi fechado |", "|---|---|"]
        for (p, d), texto in sorted(BURACOS_FECHADOS.items()):
            L.append(f"| `{p}` x `{d}` | {texto} |")
        L.append("")

    if FORA_DE_ESCOPO_ESTATICO:
        L += ["### Risco investigado e fora de escopo estatico", "",
              "Distinto de celula vazia: aqui ha check POSSIVEL em tese, e a "
              "decisao foi", "que ele nao seria verificavel de verdade neste "
              "artefato. Fica assinado", "porque *nao implementei* e *nao "
              "existe risco* sao coisas opostas — e so a", "segunda seria "
              "mentira.", "",
              "| Dominio x risco | Decisao |", "|---|---|"]
        for (d, risco), texto in sorted(FORA_DE_ESCOPO_ESTATICO.items()):
            L.append(f"| `{d}` x `{risco}` | {texto} |")
        L.append("")

    L += ["## Densidade por dominio", "",
          "O numero sozinho engana: o que interessa e se o check NASCEU do "
          "estrato ou", "foi etiquetado depois. Densidade por heranca nao e "
          "cobertura — e um numero", "que engana quem le o mapa.", ""]
    L += ["| Dominio | Checks | Leitura |", "|---|---|---|"]
    for d in doms:
        L.append(f"| `{d}` | {len(por_dominio[d])} | "
                 f"{LEITURA_DA_DENSIDADE.get(d, '—')} |")
    L.append("")

    L += [f"## Os {total}, um por linha", "",
          "| Check | Pilar | Dominio(s) | Titulo |", "|---|---|---|---|"]
    for cid in sorted(catalogo.CATALOGO, key=lambda c: (c[0], c)):
        m = catalogo.CATALOGO[cid]
        L.append(f"| `{cid}` | {m['pack']} | "
                 f"{', '.join(catalogo.dominios(cid))} | {m['titulo']} |")
    L += ["", "Todo check tem ao menos um dominio, e todo prefixo corresponde "
          "ao pilar —", "as duas coisas sao verificadas em `tests/test_dominio.py`."]
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    print(gerar(), end="")
