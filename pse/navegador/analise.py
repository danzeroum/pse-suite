"""Leitura dos corpos servidos — segredo, EXIF, sourcemap. Sem rede.

Adaptado de danzeroum/qa-suite (`webqa/dominio.py`, `webqa/sanitize.py`).
Funcoes PURAS: recebem bytes, devolvem rotulos. Nenhuma delas emite
requisicao, e nenhuma delas devolve o VALOR do que encontrou.

E a linha que separa esta bateria de um scanner: aqui so se le o que o
servidor JA entregou ao visitante. Buscar o `.map` que o bundle referencia,
ou pedir um arquivo que a pagina nao linkou, seria sondagem — Fase 3, atras
do gate ativo. O check aponta o caminho e para ai.

MINIMIZACAO ANTES DA SANITIZACAO. `metadados_exif` devolve o rotulo `gps`,
nunca a coordenada; `segredos_em` devolve o NOME do padrao, nunca a chave.
Nao existe valor a mascarar, e o sanitizador do `Finding` ainda roda por
cima. As duas defesas sao independentes de proposito: quem confia numa so
acaba sem nenhuma.
"""
import re
import struct

# Tags EXIF. Numeros do formato, nao vocabulario curado — nao ha o que
# curar num identificador definido pela especificacao TIFF/EXIF.
_EXIF_GPS = 0x8825
_EXIF_AUTORIA = (0x013B, 0x8298, 0x010F, 0x0110, 0x0131)   # Artist, Copyright, Make, Model, Software

_SOURCEMAP = re.compile(rb"//[#@]\s*sourceMappingURL\s*=\s*(\S+)")


def _compilar(padroes) -> list:
    """[(nome, regex, severidade)] a partir da regua declarada em YAML."""
    saida = []
    for item in padroes or []:
        try:
            saida.append((str(item["nome"]), re.compile(item["padrao"]),
                          str(item.get("severidade", "ALTO")).upper()))
        except (KeyError, re.error):
            continue          # padrao quebrado nao derruba a varredura inteira
    return saida


def segredos_em(texto: str, padroes) -> list:
    """[(nome_do_padrao, severidade)] — nunca o valor casado.

    O contrato inviolavel desta camada: uma credencial servida ao navegador
    JA e publica (qualquer visitante le o bundle), e republica-la no laudo
    reencenaria a exposicao num artefato que circula por CI e anexo de PR.
    Por isso o que sai daqui e o NOME do formato, e nada mais.
    """
    if not texto:
        return []
    return [(nome, sev) for nome, rx, sev in _compilar(padroes)
            if rx.search(texto)]


def _tags_da_ifd(tiff: bytes, deslocamento: int, ordem: str) -> list:
    tags = []
    try:
        (quantas,) = struct.unpack_from(ordem + "H", tiff, deslocamento)
    except struct.error:
        return tags
    for i in range(quantas):
        entrada = deslocamento + 2 + i * 12
        try:
            tags.append(struct.unpack_from(ordem + "H", tiff, entrada)[0])
        except struct.error:
            break
    return tags


def metadados_exif(dados: bytes) -> set:
    """`{"gps", "autoria"}` conforme o que o JPEG carrega. SEM valores.

    Percorre os segmentos JPEG ate o APP1 com cabecalho Exif e le a IFD0.
    Qualquer inconsistencia devolve conjunto vazio: arquivo quebrado nao e
    acusacao, e um parser que chuta numa bateria regulatoria e pior que
    parser nenhum.
    """
    achados = set()
    if not dados or not dados.startswith(b"\xff\xd8"):
        return achados
    pos = 2
    while pos + 4 <= len(dados):
        if dados[pos] != 0xFF:
            break
        marcador = dados[pos + 1]
        if marcador == 0xDA:          # dados comprimidos: nao ha EXIF depois
            break
        try:
            (tamanho,) = struct.unpack_from(">H", dados, pos + 2)
        except struct.error:
            break
        corpo = dados[pos + 4: pos + 2 + tamanho]
        if marcador == 0xE1 and corpo.startswith(b"Exif\x00\x00"):
            tiff = corpo[6:]
            if len(tiff) >= 8 and tiff[:2] in (b"II", b"MM"):
                ordem = "<" if tiff[:2] == b"II" else ">"
                try:
                    (ifd0,) = struct.unpack_from(ordem + "I", tiff, 4)
                except struct.error:
                    break
                tags = _tags_da_ifd(tiff, ifd0, ordem)
                if _EXIF_GPS in tags:
                    achados.add("gps")
                if any(t in tags for t in _EXIF_AUTORIA):
                    achados.add("autoria")
            break
        pos += 2 + tamanho
    return achados


def sourcemap_referenciado(dados: bytes) -> str:
    """URL do sourcemap declarado no bundle, "" se nao houver.

    So LE a referencia. Baixar o `.map` e requisicao nova — logo Fase 3,
    logo atras do gate ativo. Um sourcemap costuma trazer o codigo-fonte
    inteiro, e ir busca-lo sem autorizacao e exatamente a linha que o
    desenho nao cruza.
    """
    if not dados:
        return ""
    achado = _SOURCEMAP.search(dados)
    return achado.group(1).decode("ascii", errors="replace") if achado else ""


def cabecalhos_faltantes(recurso, exigidos: dict) -> list:
    """[(cabecalho, explicacao)] do que falta neste recurso.

    Um cabecalho declarado com valor vazio conta como ausente: `CSP: ` nao
    restringe nada, e tratar a presenca da chave como conformidade premiaria
    a configuracao que so parece existir.
    """
    faltando = []
    for nome, explicacao in (exigidos or {}).items():
        if not recurso.cabecalho(nome).strip():
            faltando.append((nome, explicacao))
    return faltando


def jpeg_com_exif_gps(com_gps: bool = True) -> bytes:
    """JPEG minimo, com ou sem IFD de GPS. Para DECLARAR a violacao.

    Existe porque a mutacao canonica de P-24 precisa de um JPEG com EXIF, e
    isso nao cabe em YAML como texto. A declaracao no catalogo continua sendo
    dado (`corpo_jpeg_com_gps: true`) e o executor monta os bytes — a mesma
    separacao entre dado e motor que rege o resto da mutacao.

    Montado byte a byte de proposito: depender de uma biblioteca de imagem
    faria a suite carregar Pillow so para se autoprovar, e a pergunta aqui e
    sobre o PARSER — que le bytes.

    Fica ao lado do parser porque e o par dele: se um mudar de formato sem o
    outro, o teste que os cruza reprova na hora.
    """
    if not com_gps:
        return b"\xff\xd8\xff\xdb\x00\x04\x00\x00\xff\xd9"
    entradas = (struct.pack("<H", 1)
                + struct.pack("<HHII", _EXIF_GPS, 4, 1, 26)
                + struct.pack("<I", 0))
    tiff = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8) + entradas
    app1 = b"Exif\x00\x00" + tiff
    return (b"\xff\xd8"
            + b"\xff\xe1" + struct.pack(">H", len(app1) + 2) + app1
            + b"\xff\xdb\x00\x04\x00\x00"
            + b"\xff\xd9")


def relatar_observacao(ctx, log):
    """Anexa `observacao_de_rede` ao laudo JA QUALIFICADO.

    Existe para que a qualificacao — qual superficie foi observada, e se
    quem serviu era um dev server — nao dependa de cada um dos sete checks
    dinamicos lembrar de passar a regua. Esquecer num deles produziria um
    laudo que diz a verdade em seis relatorios e cala no setimo, e qual
    apareceria dependeria da ordem de execucao.
    """
    marcas = (ctx.data.get("servido-ao-cliente") or {}).get(
        "marcas_de_dev_server") or ()
    ctx.relatorio("observacao_de_rede", log.sanitizado(marcas))
