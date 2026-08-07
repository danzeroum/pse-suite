"""O que os quatro checks com alcance a Rust compartilham.

Quatro checks — S-06, P-18, P-19, S-16 — ganharam alcance textual a `.rs`.
Nenhum virou check novo, e nenhum ganhou parser: o que eles ganharam esta
inteiro em `pse/engine/rustscan.py`, e o vocabulario em `pse/data/rust.yaml`.

O QUE MORA AQUI E SO O QUE OS QUATRO PRECISAM IGUALMENTE:

  * carregar a regua sem que nenhum `.py` de check tenha lista propria (D-13);
  * iterar os `.rs` do alvo;
  * a REGRA DE AMBIGUIDADE, que e uma so e vale para os quatro.

A regra de ambiguidade e a parte que mais importa. Sem arvore, o casamento
textual e mais fragil, e a tentacao e resolver a duvida para um dos lados —
achado (falso-positivo, que ensina o time a ignorar o pack) ou verde (falso
negativo, que e o defeito que esta suite inteira existe para nao cometer).
A saida e a terceira: quando o valor decisivo vem de uma macro de tempo de
compilacao, o check nao decide. Ele diz que nao decidiu, nomeia o arquivo,
a linha e a macro, e bloqueia — indeterminado, exit 20.
"""
from pse.engine import rustscan, scan
from pse.model import CheckIndeterminado

REGUA = "rust"
EXT = {".rs"}


def r(ctx, chave):
    return list(ctx.data[REGUA][chave])


def r_baixo(ctx, chave):
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def arquivos(ctx):
    """Os `.rs` do alvo, com o texto ja lido.

    Devolve o texto BRUTO. Cada chamador decide se quer literal (deteccao
    de segredo, onde o literal e o fato) ou nao (supressao, onde a mencao
    dentro de uma string nao prova controle nenhum).
    """
    for p in scan.arquivos(ctx.repo, EXT):
        yield p, scan.ler(p)


def recusar_se_ambiguo(ctx, check_id: str, arquivo, linha: int, valor: str,
                       o_que: str):
    """Levanta `CheckIndeterminado` se o valor decisivo nao e resolvivel.

    `env!("API_KEY")` grava o valor no BINARIO em tempo de compilacao — nao
    le o ambiente em execucao. Se o valor e um segredo, o binario carrega
    um segredo, e o texto do `.rs` nao diz qual. Nao da para chamar de
    achado nem de limpo.

    Bloquear e a resposta certa e nao um exagero: o alcance textual so vale
    enquanto for honesto sobre o que ele nao alcanca, e um `env!` decidido
    para qualquer um dos lados seria a suite inventando um fato.
    """
    macro = rustscan.macro_nao_resolvivel(valor, r(ctx, "macros_nao_resolviveis"))
    if not macro:
        return
    raise CheckIndeterminado(
        f"{scan.rel(ctx.repo, arquivo)}:{linha} — {o_que} vem de `{macro}!`, "
        f"uma macro de tempo de COMPILACAO: o valor e gravado no binario e o "
        f"texto do `.rs` nao diz qual e. Pode ou nao ser o vetor, e o alcance "
        f"textual a Rust nao tem como decidir. Resolver com `std::env::var` "
        f"(leitura em execucao) torna o caso decidivel; `{macro}!` nao.")


def e_placeholder(ctx, valor: str) -> bool:
    """D-08 ao contrario seria punir o exemplo que o time deixou de proposito."""
    baixo = str(valor).lower()
    return any(p.lower() in baixo for p in r(ctx, "placeholders"))


def sondar(ctx, marcas) -> bool:
    """O vetor descrito por estas marcas EXISTE em algum `.rs` do alvo?

    E o que faz `nao_aplicavel` ser MEDIDO em vez de alegado. Alegar
    nao-aplicabilidade e a forma mais confortavel de inflar cobertura, e
    seria exatamente o que o mapa foi criado para impedir.

    Le sem literal e sem comentario: `// TODO: chamar o modelo` nao prova
    que ha inferencia no motor, e `"kafka"` numa mensagem de erro nao prova
    que ha barramento. O que conta e o identificador que executa.

    A sonda so pode empurrar para NAO-APLICAVEL. Presenca de marca NAO e
    achado: significa que o vetor existe e que o check segue cego nele.
    """
    for _, texto in arquivos(ctx):
        if rustscan.contem_token(rustscan.efetivo(texto, sem_literais=True),
                                 marcas):
            return True
    return False
