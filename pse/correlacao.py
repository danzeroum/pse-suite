"""Correlacao estatico x dinamico — a mesma falha vista em duas camadas.

Com o Trabalho A e o B no MESMO laudo, um par aparece naturalmente: P-14 le
o codigo e ve `"?email=" + user.email`; P-23 carrega a pagina e ve `?email=`
na URL entregue. Nao sao dois defeitos. E UM defeito, com duas provas — uma
de que ele foi escrito, outra de que ele chegou ao titular.

POR QUE CORRELACIONAR E NAO DEDUPLICAR. Apagar um dos dois perderia
informacao que so o par carrega:

  * os DOIS presentes  — o defeito foi escrito E esta no ar. A prioridade
    e outra, e a correcao tem endereco: o `arquivo:linha` do estatico.
  * so o ESTATICO      — esta no codigo e nao apareceu na pagina observada.
    Pode ser caminho nao exercitado, feature desligada, rota nao visitada.
    Em P-06 x S-20 muda ate a URGENCIA: chave no repositorio esta exposta a
    quem tem o repositorio; chave no bundle esta PUBLICADA, e a correcao e
    rotacionar antes de remover.
  * so o DINAMICO      — esta no ar e NAO esta no codigo que a suite le.
    E o caso mais interessante dos tres: veio de template do servidor, de
    tag gerenciada, de dependencia. E o exato buraco que a camada dinamica
    existe para cobrir, e deduplicar o esconderia.

O bloco `correlacoes` do laudo diz qual dos tres cenarios e cada par. Os
findings seguem inteiros, com seu proprio endereco e severidade: quem le o
laudo por check nao perde nada, e quem le por defeito ganha o mapa.
"""

# (estatico, dinamico) -> o que os une. Declarado, nao inferido: parear por
# semelhanca de titulo casaria checks que so parecem parecidos.
PARES = {
    ("P-14", "P-23"): {
        "falha": "dado pessoal em transito na URL ou no armazenamento do cliente",
        "estatico": "P-14 le o codigo do front e ve o identificador sendo "
                    "posto na URL ou no localStorage",
        "dinamico": "P-23 carrega a pagina e ve o parametro na URL que o alvo "
                    "de fato entregou",
        "so_dinamico": "o vazamento nao veio do codigo que a suite le — "
                       "template do servidor, build ou componente de terceiro",
        "so_estatico": "o codigo tem o defeito e a pagina observada nao o "
                       "exercitou: rota nao visitada ou feature desligada",
    },
    ("S-04", "S-18"): {
        "falha": "terceiro tratando dado do titular sem estar declarado",
        "estatico": "S-04 le o manifesto e o codigo e ve o host que alguem "
                    "ESCREVEU",
        "dinamico": "S-18 ve o host que a pagina de fato contactou",
        "so_dinamico": "o host chegou por caminho que o repositorio nao "
                       "mostra — tag gerenciada pelo painel, script injetado "
                       "por dependencia, ou o terceiro que o proprio terceiro "
                       "chama",
        "so_estatico": "o manifesto ou o codigo citam o terceiro e a pagina "
                       "observada nao o contactou: rota nao visitada, feature "
                       "desligada, ou integracao ja removida do runtime",
    },
    ("P-06", "S-20"): {
        "falha": "credencial fora do cofre",
        "estatico": "P-06 encontra a chave no repositorio",
        "dinamico": "S-20 encontra a chave que chegou ao NAVEGADOR — logo, "
                    "publicada a todos os visitantes",
        "so_dinamico": "a chave nao esta no repositorio: veio do build, do "
                       "template renderizado pelo servidor, do arquivo que o "
                       "deploy escreve, ou de um pacote que embutiu a propria",
        "so_estatico": "a chave esta no codigo e nao foi servida na pagina "
                       "observada — continua exposta a quem tem o "
                       "repositorio, e a urgencia e outra",
    },
    ("S-09", "S-17"): {
        "falha": "credencial de sessao exposta no cliente",
        "estatico": "S-09 ve o token sendo guardado pelo codigo do front",
        "dinamico": "S-17 ve o cookie de sessao que o servidor emitiu sem "
                    "HttpOnly, Secure ou SameSite",
        "so_dinamico": "o cookie nao e escrito pelo front — vem de "
                       "middleware, proxy reverso ou gateway, nenhum deles no "
                       "repositorio que S-09 varre",
        "so_estatico": "o front guarda credencial e o cookie de sessao "
                       "observado esta correto: sao duas exposicoes "
                       "independentes, e so uma apareceu",
    },
}


def correlacionar(findings) -> list:
    """[{par, falha, cenario, ...}] para cada par com ao menos um lado presente.

    Nao altera nem remove finding nenhum: e um indice sobre o que ja esta no
    laudo. Um leitor que ignore este bloco continua vendo exatamente o que
    veria antes de ele existir.
    """
    from pse.sanitize import sanitizar_finding

    por_check: dict = {}
    for f in findings:
        por_check.setdefault(f.check_id, []).append(f)

    saida = []
    for (estatico, dinamico), texto in sorted(PARES.items()):
        do_estatico = por_check.get(estatico, [])
        do_dinamico = por_check.get(dinamico, [])
        if not do_estatico and not do_dinamico:
            continue

        if do_estatico and do_dinamico:
            cenario = "confirmado_nas_duas_camadas"
            leitura = (
                f"{texto['falha']}: {texto['estatico']}, e {texto['dinamico']}. "
                f"E UM defeito com DUAS provas — foi escrito e esta no ar. "
                f"Corrija pelo endereco do estatico; a observacao dinamica e "
                f"o criterio de pronto.")
        elif do_dinamico:
            cenario = "so_na_camada_dinamica"
            leitura = (
                f"{texto['falha']}: observado no alvo e AUSENTE no codigo "
                f"auditado — {texto['so_dinamico']}. E o caso que a camada "
                f"dinamica existe para pegar, e nenhuma leitura de "
                f"repositorio o encontraria.")
        else:
            cenario = "so_na_camada_estatica"
            leitura = (
                f"{texto['falha']}: presente no codigo e nao observado no "
                f"alvo — {texto['so_estatico']}. Nao e falso positivo do "
                f"estatico: e defeito que a observacao nao exercitou.")

        saida.append({
            "par": [estatico, dinamico],
            "falha": texto["falha"],
            "cenario": cenario,
            "leitura": leitura,
            # Passa pelo MESMO sanitizador dos findings: este bloco copia
            # `arquivo`, e no dinamico `arquivo` e uma URL — onde o
            # endereco E o conteudo. Sem isto, a correlacao seria a porta
            # dos fundos por onde a PII sairia sanitizada em um lugar e
            # crua no outro.
            "achados_estaticos": [
                {"check_id": f.check_id,
                 "arquivo": sanitizar_finding(f.to_dict())["arquivo"],
                 "linha": f.linha}
                for f in do_estatico],
            "achados_dinamicos": [
                {"check_id": f.check_id,
                 "arquivo": sanitizar_finding(f.to_dict())["arquivo"]}
                for f in do_dinamico],
        })
    return saida
