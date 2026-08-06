"""Reconhecimento de chamada a modelo de linguagem, derivado da REGUA.

A lista de fornecedores nao mora aqui: ela e computada a partir de
`data/third-party-endpoints.yaml` (categoria `llm`). Se amanha um fornecedor
entra na regua, E-00 e E-11 passam a reconhece-lo sem que ninguem toque em
codigo — e se alguem remover a categoria, o teste-guarda da regua reprova.
E a mesma razao pela qual a regua nao e copiavel pelo consumidor.
"""
import re

# Metodos que INVOCAM um modelo. Nao e "qualquer chamada num arquivo que
# menciona IA": e o verbo que faz o texto sair da maquina.
INVOCACOES = {
    "complete", "completion", "completions", "create", "chat", "generate",
    "generate_content", "invoke", "predict_text", "prompt", "ask", "run",
    "send_message", "messages", "responses", "stream",
}
# Objetos que, num modulo que ja demonstrou falar com LLM, denunciam a chamada.
OBJETOS = {"llm", "client", "cliente", "model", "modelo", "chat", "ai",
           "gpt", "assistant", "agent", "openai", "anthropic"}

_GENERICOS = {"api", "com", "net", "org", "br", "www", "googleapis",
              "generativelanguage", "cloud", "services"}


def fornecedores(ctx) -> set:
    """Tokens de fornecedor extraidos dos hosts da categoria `llm` da regua."""
    hosts = (ctx.data["third-party-endpoints"].get("categorias") or {}).get("llm", [])
    tokens = set()
    for host in hosts:
        for rotulo in str(host).lower().split("."):
            if rotulo and rotulo not in _GENERICOS and len(rotulo) > 2:
                tokens.add(rotulo)
    return tokens


def hosts_llm(ctx) -> list:
    return list((ctx.data["third-party-endpoints"].get("categorias") or {}).get("llm", []))


def modulo_fala_com_llm(texto_efetivo: str, ctx) -> bool:
    """O modulo demonstra, em codigo que executa, que conversa com um LLM."""
    baixo = texto_efetivo.lower()
    if any(h.lower() in baixo for h in hosts_llm(ctx)):
        return True
    forn = fornecedores(ctx)
    return any(re.search(rf"^\s*(?:import|from)\s+\w*{re.escape(f)}", baixo, re.M)
               for f in forn)


def e_chamada_llm(nome: str, ctx, modulo_llm: bool) -> bool:
    """`nome` e o alvo resolvido da chamada (ex.: 'llm.complete')."""
    if not nome:
        return False
    partes = [p.lower() for p in nome.split(".")]
    if partes[-1] not in INVOCACOES:
        return False
    tokens = set(partes)
    if "llm" in tokens or tokens & fornecedores(ctx):
        return True
    # Sem token de fornecedor no nome, exige que o MODULO ja tenha provado
    # falar com LLM — senao `db.create()` viraria chamada de modelo.
    return modulo_llm and bool(tokens & OBJETOS)
