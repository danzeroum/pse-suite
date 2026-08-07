"""Domínio reservado — a régua deixando de dizer duas coisas opostas.

Compartilhado por P-01 e S-03 porque a pergunta é a mesma e a resposta tinha
de ser a mesma: `test@example.com` não pode ser ignorado por S-04 e virar
CRÍTICO em P-01.

A INCOERÊNCIA FOI MEDIDA, não suposta. `example.com` já estava na lista
`ignorar` de `third-party-endpoints.yaml` desde sempre, e S-04 a consultava.
P-01 não a consultava, e acusou `test@example.com` num script de seed — três
CRÍTICOs contra alvo real. A mesma régua dizia coisas opostas sobre o mesmo
domínio, dependendo de qual check a lia.

A RFC 2606 e a RFC 6761 reservam `example.com/.org/.net` e os TLDs `.test`,
`.example`, `.invalid` e `.localhost` justamente para que ninguém precise
inventar domínio em documentação, seed e teste. Acusar quem seguiu a RFC é
punir o caso correto — D-08, o defeito que a suíte cobra dos outros.

O QUE ISTO NÃO AFROUXA, e é o limite inteiro: vale só para **valor literal**
de e-mail. `user.email` chegando de uma variável segue disparando em P-01, e
é esse o vetor que importa — o de um e-mail de titular real indo para o log.
Um domínio reservado não pode pertencer a titular nenhum: é isso que torna a
exceção segura, e não a conveniência de silenciar o achado.
"""
REGUA = "third-party-endpoints"


def _listas(ctx) -> tuple:
    regua = ctx.data[REGUA]
    ignorar = {str(d).lower() for d in regua.get("ignorar", [])}
    tlds = tuple(str(t).lower() for t in regua.get("tld_reservados", []))
    return ignorar, tlds


def dominio_reservado(ctx, dominio: str) -> bool:
    """O domínio está na régua, ou termina num TLD reservado?

    Subdomínio conta: `mail.example.com` é tão reservado quanto
    `example.com`, e listar cada subdomínio possível seria uma lista que
    nunca fecha.
    """
    d = str(dominio or "").strip().lower().rstrip(".")
    if not d:
        return False
    ignorar, tlds = _listas(ctx)
    if d in ignorar or any(d.endswith("." + ig) for ig in ignorar):
        return True
    return any(d == t.lstrip(".") or d.endswith(t) for t in tlds)


def email_reservado(ctx, valor: str) -> bool:
    """`test@example.com` sim; `joao@bancoreal.com.br` não.

    Recebe o e-mail inteiro e julga só o domínio: a parte local não diz nada
    sobre a existência do titular.
    """
    texto = str(valor or "")
    if "@" not in texto:
        return False
    return dominio_reservado(ctx, texto.rsplit("@", 1)[-1])


def so_emails_reservados(ctx, texto: str) -> bool:
    """Todo e-mail deste texto é de domínio reservado?

    A pergunta é *todo*, e o `all` é deliberado. Um payload que traz
    `suporte@example.com` **e** `joao@bancoreal.com.br` continua sendo
    achado: basta um e-mail de domínio vivo para o vazamento existir.
    """
    from pse.sanitize import RX_EMAIL
    achados = RX_EMAIL.findall(str(texto or ""))
    if not achados:
        return False
    return all(dominio_reservado(ctx, dominio) for _, dominio in achados)
