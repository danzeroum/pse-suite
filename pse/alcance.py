"""Cobertura honesta: o que a suite NAO consegue ler, dito em voz alta.

O primeiro alvo real (danzeroum/btv) tornou o problema impossivel de ignorar.
O repositorio tem 137 arquivos Rust, e a PSE nao tem parser de Rust — entao
ela leu zero deles e o laudo saiu **sem uma palavra sobre isso**. Um leitor
razoavel do laudo concluiria que o backend Rust foi auditado e estava limpo.

Nao estava auditado. Nao estava nada.

Isso e a mesma familia de defeito que a suite cobra dos outros, e que ja
apareceu duas vezes aqui: `working tree verde` nao provava reprodutibilidade,
`NetworkLog fabricado verde` nao provava observacao. Agora: **`nenhum achado
em .rs` nao prova codigo Rust limpo** — prova que ninguem olhou.

O bloco `alcance` do laudo responde tres perguntas que ate agora ficavam sem
resposta:

  * que linguagens existem no alvo, e em que volume;
  * quais delas a suite SABE ler, e com que ferramenta;
  * quais ela NAO le — nominalmente, com contagem de arquivos.

Nao e finding: nao ha defeito no alvo por ele ser escrito em Rust. E ESTADO,
como `relatorios` — o consumidor precisa saber o tamanho do que nao foi
olhado para decidir se o laudo lhe basta.

Por que nao vira indeterminacao (exit 20): porque nao houve tentativa
frustrada. `CheckIndeterminado` e "tentei e nao consegui decidir"; aqui a
suite nunca teve como tentar, e nao ha check nenhum previsto para Rust. Tratar
ausencia de cobertura como indeterminacao faria todo alvo poliglota bloquear
para sempre, e o gate perderia o sentido. A resposta certa e declarar, nao
bloquear — e um consumidor que exija cobertura de Rust le este bloco e decide.
"""
from collections import Counter

from pse.engine import scan

# Extensao -> (rotulo, ferramenta que a suite usa). O que NAO esta aqui e,
# por definicao, fora de alcance — e a lista de fora fica curta de proposito:
# inventar um rotulo para cada extensao do mundo daria a impressao de que a
# suite conhece linguagens que ela nunca leu.
COM_PARSER = {
    ".py": ("Python", "ast (stdlib)"),
    ".js": ("JavaScript", "tree-sitter"),
    ".jsx": ("JavaScript/JSX", "tree-sitter"),
    ".mjs": ("JavaScript", "tree-sitter"),
    ".cjs": ("JavaScript", "tree-sitter"),
    ".ts": ("TypeScript", "tree-sitter"),
    ".tsx": ("TypeScript/TSX", "tree-sitter"),
    ".yaml": ("YAML", "PyYAML"),
    ".yml": ("YAML", "PyYAML"),
    ".json": ("JSON", "PyYAML"),
    ".sql": ("SQL", "regex sobre codigo efetivo"),
    ".sh": ("shell", "linha a linha sobre codigo efetivo"),
    ".bash": ("shell", "linha a linha sobre codigo efetivo"),
}

# Extensoes que nao sao codigo nem declaracao: nao ter parser para elas nao e
# lacuna de cobertura, e lista-las como tal viraria ruido que esconde a
# lacuna de verdade.
IRRELEVANTES = {
    ".md", ".txt", ".rst", ".adoc", ".csv", ".tsv", ".log",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".pdf",
    ".woff", ".woff2", ".ttf", ".eot", ".otf",
    ".lock", ".sum", ".mod", ".gitignore", ".gitattributes", ".editorconfig",
    ".map", ".min", ".snap", ".pyc", ".so", ".dylib", ".dll", ".bin",
    ".css", ".scss", ".less", ".html", ".htm", ".xml",
}

# TERCEIRA CATEGORIA, e ela existe para nao virar mentira.
#
# `.rs` nao esta em COM_PARSER e nunca vai estar por causa deste bloco: a
# suite NAO le Rust. O que ela ganhou foi alcance a QUATRO VETORES por
# padrao textual ancorado — S-06, P-18, P-19, S-16 —, e nada alem disso.
#
# Poe-lo em COM_PARSER faria o laudo dizer "Rust: lido", e um leitor
# razoavel concluiria que os 57 checks olharam o motor. Deixa-lo em
# SEM_PARSER faria o laudo esconder o alcance que existe, e o consumidor
# que corrigiu uma chave hardcoded no `.rs` nao entenderia de onde veio o
# achado. As duas leituras seriam falsas em direcoes opostas — por isso a
# terceira lista, com os checks NOMEADOS.
ALCANCE_PARCIAL = {
    ".rs": ("Rust", "padrao textual ancorado (sem parser)",
            ["S-06", "P-18", "P-19", "S-16"]),
}

# Linguagens que a suite reconhece pelo nome mas nao le. Existir aqui e o que
# permite o laudo dizer "137 arquivos Rust NAO foram lidos" em vez de
# "137 arquivos .rs" — o consumidor pensa em linguagem, nao em extensao.
SEM_PARSER = {
    ".rs": "Rust", ".go": "Go", ".java": "Java", ".kt": "Kotlin",
    ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".swift": "Swift",
    ".c": "C", ".h": "C/C++", ".cpp": "C++", ".hpp": "C++", ".cc": "C++",
    ".scala": "Scala", ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang",
    ".dart": "Dart", ".lua": "Lua", ".pl": "Perl", ".r": "R", ".m": "Objective-C",
    ".proto": "Protobuf", ".tf": "Terraform", ".hcl": "HCL", ".toml": "TOML",
    ".gradle": "Gradle", ".vue": "Vue", ".svelte": "Svelte",
}


def _extensao(p) -> str:
    return p.suffix.lower()


def medir(repo) -> dict:
    """Inventario de linguagens do alvo, separado por alcance.

    Conta ARQUIVOS, nao linhas: linha exige ler o arquivo inteiro, e o ponto
    aqui e justamente que a suite nao leu. Contar o que nao se leu seria
    incoerente com o que o bloco existe para dizer.
    """
    from pathlib import Path
    lidos, nao_lidos, ignorados = Counter(), Counter(), Counter()
    parciais = Counter()
    for p in sorted(Path(repo).rglob("*")):
        if any(parte in scan.IGNORAR_DIRS for parte in p.parts):
            continue
        if not p.is_file():
            continue
        ext = _extensao(p)
        if ext in COM_PARSER:
            lidos[COM_PARSER[ext][0]] += 1
        elif ext in ALCANCE_PARCIAL:
            parciais[ALCANCE_PARCIAL[ext][0]] += 1
        elif ext in SEM_PARSER:
            nao_lidos[SEM_PARSER[ext]] += 1
        elif ext in IRRELEVANTES or not ext:
            ignorados[ext or "(sem extensao)"] += 1
        else:
            nao_lidos[f"{ext} (linguagem nao reconhecida)"] += 1

    ferramentas = {}
    for ext, (rotulo, ferramenta) in COM_PARSER.items():
        if lidos.get(rotulo):
            ferramentas[rotulo] = ferramenta

    tecnica = {r: (t, checks) for _, (r, t, checks) in ALCANCE_PARCIAL.items()}
    total_fora = sum(nao_lidos.values())
    total_parcial = sum(parciais.values())
    return {
        "lidos": [{"linguagem": k, "arquivos": v, "ferramenta": ferramentas.get(k)}
                  for k, v in lidos.most_common()],
        "alcance_parcial": [
            {"linguagem": k, "arquivos": v,
             "tecnica": tecnica[k][0], "checks": tecnica[k][1],
             "nota": (f"A suite NAO le {k}. Ela alcanca {len(tecnica[k][1])} "
                      f"vetores por {tecnica[k][0]}: {', '.join(tecnica[k][1])}. "
                      f"Ausencia de achado desses quatro significa 'olhei e "
                      f"esta limpo'; ausencia de achado de QUALQUER OUTRO "
                      f"check nestes arquivos nao significa nada — eles nao "
                      f"foram olhados.")}
            for k, v in parciais.most_common()],
        "fora_de_alcance": [{"linguagem": k, "arquivos": v}
                            for k, v in nao_lidos.most_common()],
        "arquivos_fora_de_alcance": total_fora,
        "arquivos_em_alcance_parcial": total_parcial,
        "nota": (
            "AUSENCIA DE ACHADO NAS LINGUAGENS ACIMA NAO E ATESTADO DE "
            "CONFORMIDADE: a suite nao tem parser para elas e nao leu nenhum "
            "desses arquivos. Este bloco existe porque um laudo silencioso "
            "sobre o que nao foi olhado e indistinguivel de um laudo que "
            "olhou e nao achou nada."
            if total_fora else
            "Todo arquivo de codigo ou declaracao do alvo esta em linguagem "
            "que a suite le, ou em linguagem de alcance parcial declarado."),
    }
