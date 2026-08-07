"""Contexto de credencial — a severidade de P-06 e S-06, e por que ela varia.

Compartilhado pelos dois porque a pergunta e a mesma e a resposta tem de ser
a mesma: um `password = "test-secret"` em `tests/` nao pode ser CRITICO em um
check e CRITICO em outro por motivos diferentes.

O QUE ESTE MODULO NAO FAZ. Ele nao decide se ha credencial — isso continua
sendo o padrao de cada check, e nao mudou. Ele nao suprime achado nenhum:
nao existe caminho de codigo aqui que devolva "ignore isto". A unica saida e
uma severidade, e a mais baixa que ele produz e MEDIO.

POR QUE NAO SUPRIMIR. Ignorar `tests/` seria a trava que o vigiado desliga
movendo o segredo para um arquivo de teste — e segredo real vaza em teste com
frequencia suficiente para que a suposicao contraria seja irresponsavel. O
achado continua no laudo; o que muda e ele parar de dirigir o exit code.

POR QUE REBAIXAR. Medido contra 6 alvos reais: 18 dos 19 CRITICOs de
credencial eram fixtures. Em Central_Inteligencia_Juridica, os TRES que
produziram exit 10 eram todos de teste. Um gate que reprova por
falso-positivo ensina o operador a ignorar a categoria — e e nesse silencio
que o 19o caso, o real, passa junto.

A ANCORA E O FATO (D-01), nas duas metades: o caminho do arquivo e o proprio
literal capturado. Nenhuma delas le comentario. Um `# este e so um teste` ao
lado de uma chave da AWS nao rebaixa nada.
"""
import re

from pse.model import Severidade

REGUA = "credenciais"


def _r(ctx, chave) -> list:
    return [str(t).lower() for t in ctx.data[REGUA][chave]]


def caminho_de_teste(ctx, rel: str) -> bool:
    """O arquivo vive num caminho de teste?

    A POSICAO DA MARCA E O CHECK INTEIRO, e custou o teste que mais importa
    desta rodada para aparecer. Casando `test_` em qualquer lugar do nome,
    `scripts/generate_test_password.py` virava "arquivo de teste" — e esse e
    o 19o caso, o unico REAL dos 19 CRITICOs medidos contra alvos reais.
    Consertar 18 falsos-positivos teria custado o unico verdadeiro, que e
    fazer o oposto do que o conserto existe para fazer.

    Por isso a marca declara onde casa, e a gramatica vive na regua:
    `/x/` diretorio, `^x` prefixo do nome, `x$` sufixo do nome sem extensao,
    e qualquer outra marca casa como pedaco do nome.
    """
    caminho = "/" + str(rel).replace("\\", "/").lower()
    nome = caminho.rsplit("/", 1)[-1]
    radical = nome.rsplit(".", 1)[0] if "." in nome else nome
    for marca in _r(ctx, "caminhos_de_teste"):
        if marca.startswith("/") and marca.endswith("/"):
            if marca in caminho + "/":
                return True
        elif marca.startswith("^"):
            if nome.startswith(marca[1:]):
                return True
        elif marca.endswith("$"):
            if radical.endswith(marca[:-1]):
                return True
        elif marca in nome:
            return True
    return False


_LITERAL = re.compile(r"""["']([^"']{4,})["']""")
_PORTADOR = re.compile(r"\b(?:Bearer|Basic)\s+([A-Za-z0-9._\-]{8,})", re.I)


def valores(snippet: str) -> list:
    """So o VALOR, nunca a linha inteira — e a diferenca decide o check.

    A primeira versao casava contra o snippet completo, e o resultado era
    absurdo: o padrao de P-06 exige a palavra `password` na linha, `password`
    esta entre os valores sinteticos, e portanto TODO achado de P-06 seria
    rebaixado. O nome da variavel nao e o segredo; o literal e.

    `password = "password"` continua rebaixado, porque ai a marca esta onde
    importa. `password = "hunter2ABC"` nao.
    """
    texto = snippet or ""
    achados = [m.group(1) for m in _LITERAL.finditer(texto)]
    achados += [m.group(1) for m in _PORTADOR.finditer(texto)]
    return achados


def valor_sintetico(ctx, snippet: str) -> bool:
    """O literal capturado se declara descartavel?

    `changeme`, `test-secret`, `your_api_key_here`. Vale sozinho, fora de
    `tests/` inclusive: um placeholder num script de exemplo tambem nao
    merece dirigir o gate de ninguem.
    """
    marcas = _r(ctx, "valores_sinteticos")
    return any(marca in v.lower() for v in valores(snippet) for marca in marcas)


def severidade(ctx, rel: str, snippet: str) -> Severidade:
    """CRITICO, ou MEDIO quando o contexto diz que aquilo nao e segredo vivo.

    Nao ha terceiro valor e nao ha `None`: toda credencial detectada sai com
    severidade, e toda severidade que sai daqui vai para o laudo.
    """
    if caminho_de_teste(ctx, rel) or valor_sintetico(ctx, snippet):
        return Severidade.MEDIO
    return Severidade.CRITICO


def motivo(ctx, rel: str, snippet: str) -> str:
    """A frase que explica o rebaixamento — ou o silencio quando nao houve.

    Achado rebaixado sem motivo escrito e pior que achado nao rebaixado: o
    leitor ve MEDIO e nao sabe se a suite julgou o contexto ou se desistiu.
    """
    razoes = []
    if caminho_de_teste(ctx, rel):
        razoes.append("o arquivo esta num caminho de teste")
    if valor_sintetico(ctx, snippet):
        razoes.append("o proprio valor se declara sintetico")
    if not razoes:
        return ""
    return (
        f"SEVERIDADE REBAIXADA PARA MEDIO: {' e '.join(razoes)}. O achado "
        f"continua no laudo e deixa de dirigir o exit code — mas nao foi "
        f"suprimido, porque segredo real vaza em codigo de teste com "
        f"frequencia. Confirme que este valor nao abre nada.")
