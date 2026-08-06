"""P-10 — portabilidade: exportacao existe, responde e vem integra.

MODO ATIVO. O pacote de exportacao E o conjunto dos dados do titular, entao
este e o unico check cujo trace **omite a resposta por completo**: mascarar
nao serviria, porque o problema nao e um campo, e o volume. Arquivar 8 KB do
pacote em `harness/runs/` seria vazar num lugar exatamente o que o check
prova que o titular tem direito de receber em outro.

O que sobra no trace: status, tamanho e a lista de CHAVES presentes — o
suficiente para o revisor entender o veredito sem ler um dado.
"""
from pse.engine.registry import check
from pse.model import Finding, Severidade
from pse.trabalho_a import autorizacao
from pse.trabalho_a.base import exigir_alvo

INTEGRIDADE = ("hash", "sha256", "checksum", "digest", "assinatura", "signature")
ESTRUTURA = ("dados", "data", "registros", "records", "campos", "tabelas",
             "gerado_em", "generated_at", "formato", "format")


@check("P-10", "privacy", "Portabilidade", base_legal="LGPD Art. 18 V")
def portabilidade(ctx):
    cliente, _ = exigir_alvo(ctx, "active")
    token_a = autorizacao.token(ctx.config, "titular_a")
    rota = autorizacao.endpoint(ctx.config, "exportacao")

    resposta, trace = cliente.requisitar("GET", rota, token=token_a,
                                         identidade="titular_a",
                                         sem_corpo_no_trace=True)

    if resposta.status >= 400:
        return [Finding(
            check_id="P-10", pack="privacy", severidade=Severidade.ALTO,
            titulo="Endpoint de portabilidade nao responde",
            descricao=f"GET em {rota} respondeu {resposta.status}. O direito a "
                      f"portabilidade (Art. 18 V) nao tem por onde ser exercido.",
            recomendacao="Expor exportacao autenticada, em formato "
                         "interoperavel, com prova de integridade.",
            base_legal="LGPD Art. 18 V", arquivo=rota, linha=1, trace=trace)]

    dado = resposta.json()
    if not isinstance(dado, dict):
        return [Finding(
            check_id="P-10", pack="privacy", severidade=Severidade.ALTO,
            titulo="Exportacao sem estrutura interoperavel",
            descricao=f"A exportacao respondeu {resposta.status} mas o corpo nao "
                      f"e um objeto estruturado. Portabilidade exige formato que "
                      f"outro controlador consiga importar.",
            recomendacao="Devolver JSON/CSV documentado, com metadados de "
                         "geracao e prova de integridade.",
            base_legal="LGPD Art. 18 V", arquivo=rota, linha=1, trace=trace)]

    # As CHAVES entram no trace; os valores nao. E o que permite auditar o
    # veredito sem republicar o pacote.
    chaves = sorted(str(k).lower() for k in dado)
    trace["resposta"]["chaves_presentes"] = chaves

    faltando = []
    if not any(k in c for c in chaves for k in INTEGRIDADE):
        faltando.append("prova de integridade (hash/checksum/assinatura)")
    if not any(k in c for c in chaves for k in ESTRUTURA):
        faltando.append("estrutura declarada (dados/registros/formato)")
    if not faltando:
        return []
    return [Finding(
        check_id="P-10", pack="privacy", severidade=Severidade.ALTO,
        titulo="Exportacao sem integridade ou sem estrutura declarada",
        descricao=f"O pacote exportado nao traz: {', '.join(faltando)}. "
                  f"Sem hash, o titular nao consegue provar que recebeu o que "
                  f"foi gerado; sem estrutura, nenhum outro controlador importa.",
        recomendacao="Incluir sha256 do pacote, formato e data de geracao nos "
                     "metadados da exportacao.",
        base_legal="LGPD Art. 18 V", arquivo=rota, linha=1, trace=trace)]
