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

LEITURA_DA_DENSIDADE = {
    "frontend":
        "Unico dominio cujos checks foram desenhados OLHANDO para ele. Os "
        "tres nasceram do estrato.",
    "api":
        "Todos classificados a posteriori. Nenhum nasceu da pergunta 'o que e "
        "proprio de uma API?' — vieram do Trabalho A e foram etiquetados depois.",
    "backend":
        "A posteriori. Sao os estaticos do inventario, reclassificados.",
    "data":
        "A posteriori, mas o mais coerente dos quatro herdados: catalogo, "
        "retencao, k-anonimato e lineage sao genuinamente do estrato de dados.",
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

    L += ["## Densidade por dominio", "",
          "O numero sozinho engana: o que interessa e se o check NASCEU do "
          "estrato ou", "foi etiquetado depois. So o frontend passou pela "
          "primeira porta.", ""]
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
