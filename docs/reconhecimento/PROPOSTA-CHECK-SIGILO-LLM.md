# Proposta de check — **E-11 · Dado sob sigilo jurídico enviado a LLM externo**

> **ESPECIFICAÇÃO, NÃO IMPLEMENTAÇÃO.** Nenhum código de check foi escrito nesta
> rodada.

**Origem:** o estrato. O vetor foi visto em `juridico-platform@87f4934`
(`defensor/orchestrator.py` → `ai/generate.py` → `api.openai.com`) e em
`Central_Inteligencia_Juridica@2132f1b` (`services/llm_client.py`). Não é uma
regra genérica de "não mande PII para IA" — é o caminho de código que os dois
alvos jurídicos realmente têm.

---

## 1. Nota de mapeamento — o E-11 do enunciado não existe

O enunciado pede "refinamento do E-11, que cobre PII em prompt". **`E-11` não
existe nesta suíte**: ética vai de E-00 a E-10, e nenhum dos onze olha prompt
(ver `ONBOARDING-NOTES.md` §0).

Então não há refinamento a fazer — há um check a **criar**. Proponho ocupar
justamente o ID `E-11`, o próximo livre do pacote, para que a numeração do
enunciado e a da suíte parem de divergir.

O que existe hoje e chega mais perto:

| Check | O que faz | Onde para |
|---|---|---|
| **S-04** | acusa host de terceiro sem manifesto; `api.openai.com` está na régua, categoria `llm` | vê **QUEM** recebe. Nada sobre o conteúdo |
| **S-05** | cobra `egress_fields` declarados por integração | vê **o que foi DECLARADO** que sai. E fica `SkipCheck` sem manifesto — como ficou nos 6 alvos |

O vão entre os dois é literal: **ninguém olha o que entra no prompt.**

---

## 2. O vetor real, nos alvos reais

### 2.1 `juridico-platform` — caminho completo, sem redação em nenhum ponto

`services/defensor/orchestrator.py:78-84`:

```python
prompt = (
    f'Redija a seção "{sec.titulo}" da defesa, no canal {request.canal.value}, '
    f"para um caso do tipo {request.tipo_caso.value}.\n"
    f"Reclamante: {request.reclamante}. Reclamada: {request.reclamada}.\n"
    f"Fatos relatados: {request.descricao}\n"
    "Escreva 1 a 2 parágrafos em linguagem jurídica, sem inventar fatos não informados."
)
texto = generate_text(prompt, system=_LLM_SYSTEM, max_tokens=400)
```

→ `services/shared/ai/generate.py:25` — `generate_text()`. **Módulo inteiro sem
uma única chamada de redação, mascaramento ou guardrail.**
→ `generate.py:56` `_openai()` → `POST {LLM_BASE_URL}/chat/completions`
→ `services/shared/config.py:102` → `os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")`.

**O que sai:** nome do reclamante, nome da reclamada e a **narrativa dos fatos**
de uma peça de defesa. É o núcleo do que pode estar sob sigilo, e sai por default
para um LLM externo.

### 2.2 `Central_Inteligencia_Juridica` — a redação existe, mas não neste caminho

O alvo tem `src/safety/pii.py` com `redact_pii()` (EMAIL, OAB, CNPJ, CPF, PHONE,
CEP) e ele é **chamado de fato**, não citado:

| Arquivo:linha | Onde a redação acontece |
|---|---|
| `src/agents/supervisor_agent.py:164, 420` | trilha de auditoria |
| `src/protocols/safety_protocol.py:57` | protocolo de segurança |
| `src/memory/vector_memory.py:347-348` | memória vetorial (persistência) |
| `src/integrations/adapters/djen_adapter.py:79` | ingestão do DJEN |

**Onde ela não acontece:** `src/services/llm_client.py:35` —
`messages=[{"role": "user", "content": prompt}]`, sem passar por `redact_pii`.

> **Este contraste é a especificação inteira em uma frase:** o alvo protege o que
> **armazena** e não protege o que **envia ao modelo**. Um check de "existe
> redação no repositório?" ficaria verde aqui — e estaria errado. O check tem de
> perguntar se a redação está **neste caminho**.

### 2.3 O conceito de sigilo simplesmente não existe no código

Medido nos dois alvos jurídicos, em todos os `.py`:

```
segredo de justiça | segredo_de_justica | em_segredo | sigilo* | confidencial
  -> 1 ocorrência isolada
```

E na régua da PSE (`pii-patterns.yaml`, `sensitive-fields.yaml`): **zero**.

Note que `pii.py` do alvo tem um padrão chamado `OAB` — mas é o **número de
inscrição do advogado tratado como PII**, não o **sigilo profissional**. São
coisas diferentes, e a segunda não está em lugar nenhum.

---

## 3. A régua nova proposta

Arquivo novo no pacote: **`pse/data/sigilo-juridico.yaml`**.

```yaml
# Regua de sigilo juridico. NUNCA copiada para o consumidor.
#
# Base: CF Art. 5o LX e Art. 93 IX; CPC Art. 189; ECA Art. 143;
# Lei 8.906/94 (EOAB) Art. 7o II e §6o; LGPD Art. 7o §3o e Art. 11.
#
# CUIDADO D-08, e ele vale para o arquivo inteiro: num sistema juridico o
# conteudo LEGITIMAMENTE contem dado de processo. O objetivo NUNCA e proibir
# o tratamento — e detectar dado sob sigilo saindo para terceiro SEM redacao.

# 1. Marcadores de que o dado esta sob segredo.
marcadores_sigilo:
  - segredo_de_justica
  - segredo_justica
  - em_segredo
  - sob_sigilo
  - nivel_sigilo
  - grau_sigilo
  - sigiloso
  - processo_sigiloso
  - justica_gratuita_sigilo
  - tramitacao_sigilosa
  - confidencial

# 2. Campos que carregam conteudo de processo. Presenca isolada NAO e achado
#    (§4.2): so pesa quando entra num prompt sem redacao.
campos_processo:
  - numero_processo
  - num_processo
  - numero_cnj
  - processo_id
  - peticao
  - peca_processual
  - inteiro_teor
  - teor_decisao
  - despacho
  - sentenca
  - acordao
  - parte_autora
  - parte_re
  - reclamante
  - reclamada
  - requerente
  - requerido
  - depoimento
  - laudo_pericial

# 3. Sigilo profissional da advocacia (EOAB Art. 7o, II).
sigilo_profissional:
  - comunicacao_cliente
  - consulta_cliente
  - orientacao_juridica
  - estrategia_processual
  - tese_defesa
  - parecer_reservado

# 4. Materias que tramitam em segredo por forca de lei (CPC Art. 189).
materias_sigilosas:
  - familia
  - divorcio
  - guarda
  - alimentos
  - filiacao
  - adocao
  - interdicao
  - infancia
  - adolescente
  - violencia_domestica
  - arbitragem

# 5. Numero CNJ: NNNNNNN-DD.AAAA.J.TR.OOOO
numero_cnj:
  regex: '\b\d{7}-\d{2}\.\d{4}\.\d\.\d{2}\.\d{4}\b'
  # Os digitos DD sao verificadores (mod 97, base 10) — validar antes de afirmar,
  # pela mesma razao que o PAN exige Luhn: precisao sobre recall.
  validacao: {modulo_97: true}

# 6. Chamadas que provam redacao — o FATO que suprime (D-01/D-08).
redacoes:
  - redact
  - redigir_sigilo
  - anonimiz
  - pseudonimiz
  - mascarar
  - mask
  - scrub
  - sanitiz
  - remove_pii
  - strip_pii
  - desidentific

# 7. Sinks de LLM. Complementa third-party-endpoints.yaml: aqui sao CHAMADAS,
#    la sao hosts.
sinks_llm:
  chamadas:
    - openai.ChatCompletion.create
    - openai.chat.completions.create
    - client.chat.completions.create
    - anthropic.messages.create
    - client.messages.create
    - ollama.chat
    - ollama.generate
    - genai.GenerativeModel.generate_content
    - litellm.completion
    - langchain
    - llm.invoke
    - chain.run
  # Requisicao HTTP crua cujo corpo tem 'messages'/'prompt' e cujo destino
  # e host da categoria `llm` de third-party-endpoints.yaml.
  http_com_prompt: true
  # Hosts locais: NAO sao egresso a terceiro. Rebaixam a severidade (§4.3).
  hosts_locais:
    - ollama
    - localhost
    - 127.0.0.1
    - host.docker.internal
    - llama-cpp
    - vllm
    - text-generation-webui
```

---

## 4. Especificação do check

| Campo | Valor |
|---|---|
| **ID** | `E-11` |
| **Pacote** | `ethics` |
| **Título** | Dado sob sigilo jurídico enviado a LLM sem redação |
| **Base legal** | CPC Art. 189 · EOAB Art. 7º II e §6º · LGPD Art. 7º §3º e Art. 11 · CF Art. 5º LX |
| **Tipo** | `estatico` |
| **Modo** | `inventory` |
| **Severidade** | **CRÍTICO** (marcador de sigilo → LLM externo) · **ALTO** (campo de processo → LLM externo) · **MÉDIO** (→ LLM local) |
| **Status proposto** | `previsto-fase-4` |

### 4.1 O vetor

**Via AST (Python), em três passos, todos ancorados no fato:**

1. **Achar o sink.** Chamada que casa `sinks_llm.chamadas`, ou `requests.post`
   cujo corpo tem chave `messages`/`prompt` para host da categoria `llm`.
2. **Achar o que entra.** Rastrear, **dentro da mesma função**, a variável do
   prompt até sua construção: f-string, concatenação, `.format()`, template. Colher
   os identificadores interpolados.
3. **Perguntar se houve redação.** Alguma chamada de `redacoes` foi aplicada a
   esses identificadores, entre a construção e o envio?

**Achado** = identificador de `marcadores_sigilo` / `campos_processo` /
`sigilo_profissional` / `materias_sigilosas` interpolado no prompt, **sem** chamada
de redação no caminho.

### 4.2 Supressão — o cuidado D-08, e aqui ele é o ponto principal

Este é o check com **maior risco de falso-positivo de toda a suíte**, e a razão é
estrutural: num sistema jurídico, mandar texto de processo para um modelo é
frequentemente **a funcionalidade**, não o defeito. O próprio `pii.py` do alvo diz
isso — *"num sistema jurídico o conteúdo legitimamente contém PII (partes do
processo). Por isso o objetivo NÃO é bloquear, e sim detectar e redigir"*.

O check **NÃO dispara** quando:

1. **há chamada de `redacoes` que executa** sobre o identificador antes do sink.
   `generate_text(redact_pii(prompt))` é conforme. Comentário `# TODO: redigir`
   não suprime nada — é D-01, exatamente como E-04;
2. **o nome do campo aparece só em comentário/docstring** — `scan.codigo_efetivo`
   com `sem_literais=True` para a lógica de supressão;
3. **o sink é local** (`sinks_llm.hosts_locais`) → **não é achado de egresso**;
   rebaixa a MÉDIO (o dado não sai do perímetro, mas segue sem redação em prompt);
4. **o identificador está em `campos_processo` e o prompt não tem nenhum marcador
   de sigilo** → **isoladamente não é CRÍTICO**. Dado de processo público é
   público: publicidade é a regra (CF Art. 93 IX), sigilo é a exceção. Isso vira
   ALTO, e só;
5. **arquivo em `tests/`, `examples/`, `docs/`** → não emitir CRÍTICO. Todos os
   três alvos com LLM têm exemplos didáticos que casariam.

### 4.3 Quando ficar INDETERMINADO — e aqui é obrigatório

**A bifurcação de provedor em runtime.** `generate.py:31`:

```python
provider = settings.LLM_PROVIDER.lower()
if provider == "openai":
    return _openai(prompt, system, max_tokens)
return _ollama(prompt, system, max_tokens)
```

Estaticamente **não dá para saber** se produção roda `openai` (externo) ou
`ollama` (local). Os dois ramos existem, os dois são alcançáveis.

O check **não pode escolher**. Comportamento obrigatório:

> `CheckIndeterminado` — *"há dado de processo indo a um sink de LLM cujo destino
> é decidido em runtime por `LLM_PROVIDER`; a suíte não consegue decidir
> estaticamente se o egresso é externo ou local."*

Bloqueia (exit 20), que é o desfecho correto: nem verde falso, nem CRÍTICO forçado.
E resolve-se por **declaração** — se o consumidor declarar `llm_egress: external`
ou `local` em `pse-config.yaml`, o check decide. Declaração ausente → indeterminado.

Também indeterminado quando:
- o prompt é montado em **outro módulo** e passado por parâmetro → não rastreável;
- `.js`/`.ts` (sem AST) — **o check não roda**, e registra
  `ctx.relatorio("cobertura_parcial", …)`. Isso importa: as libs de LLM em
  TypeScript são comuns, e 300+ `.tsx`/`.jsx` desta rodada já estão fora de alcance.

### 4.4 Aplicado aos alvos reais — veredito esperado

| Alvo | Fato | Veredito esperado |
|---|---|---|
| `juridico-platform` | `orchestrator.py:78-84` interpola `reclamante`, `reclamada`, `descricao` → `generate_text` sem redação | **INDETERMINADO** (§4.3) — vira **ALTO** com `llm_egress: external` declarado; **MÉDIO** com `local` |
| `juridico-platform` | `config.py:102` default `api.openai.com` | já coberto por **S-04** — não duplicar (D-09: cada check responde por uma coisa) |
| `Central` | `llm_client.py:35` `messages=[…]` sem `redact_pii`, sink Ollama local | **MÉDIO** — sink local, sem redação |
| `Central` | `supervisor_agent.py:164`, `vector_memory.py:347` com `redact_pii()` | **não dispara** — redação que executa (D-08) |
| `Central` | `examples/patterns/*.py` com LLM | **não dispara em CRÍTICO** — regra 5 |
| `reconcilia`, `Criptotrade`, `giva`, `dadosabedoria` | sem campo de processo | **não dispara** |

Nenhum CRÍTICO em nenhum dos 6. Correto: **nenhum dos alvos tem marcador de
sigilo no código** — não porque tratem sigilo bem, mas porque o conceito não
existe lá. O check começa a valer no dia em que existir, e é essa a função dele.

### 4.5 Mutação canônica

```yaml
canonical_mutation:
  descricao: dado de processo sob segredo vai ao LLM externo sem redacao
  arquivos:
    app.py: |
      import requests


      def resumir(processo):
          prompt = f"Resuma: {processo.inteiro_teor} (segredo_de_justica={processo.segredo_de_justica})"
          return requests.post("https://api.openai.com/v1/chat/completions",
                               json={"messages": [{"role": "user", "content": prompt}]})
  config:
    llm_egress: external
  espera_severidade: CRITICO
```

Par negativo para o `consumidor_bom`:

```python
def resumir(processo):
    prompt = f"Resuma: {redact_pii(processo.inteiro_teor)}"
    return llm.invoke(prompt)
```

---

## 5. Testes que a implementação tem de trazer

1. Marcador de sigilo + LLM externo declarado → **1 CRÍTICO**.
2. Mesmo código com `redact_pii(...)` no caminho → **0 achados** (D-08).
3. Mesmo código com `# TODO: redigir antes de mandar` → **1 CRÍTICO** (D-01).
4. Campo de processo **sem** marcador de sigilo → **ALTO**, nunca CRÍTICO.
5. Sink Ollama local → **MÉDIO**, nunca CRÍTICO.
6. Provedor decidido em runtime, sem `llm_egress` declarado → **INDETERMINADO**.
7. Mesmo caso com `llm_egress: external` → **ALTO**.
8. Campo de processo em `examples/` → **0 CRÍTICO**.
9. Número CNJ com dígito verificador inválido → **não conta como CNJ**.
10. Snippet de qualquer achado → **número CNJ e nome de parte mascarados** (D-02).
11. **`Central@2132f1b` → 0 achados** nos arquivos que já chamam `redact_pii` —
    regressão contra punir quem faz certo.

---

## 6. O que este check NÃO faz

- **Não decide se um processo está sob segredo.** Isso é do juiz. O check olha
  se o **código marca** o sigilo e se o dado marcado sai sem redação.
- **Não proíbe LLM em legaltech.** Rebaixa sink local, suprime com redação, e na
  dúvida fica indeterminado.
- **Não substitui S-04/S-05.** S-04 diz quem recebe; S-05, o que foi declarado;
  E-11, o que de fato entra no prompt. Não duplicar achado (D-09).

---

## 7. Pontos abertos para ratificação do dono

1. **Ética ou privacidade?** Argumentei `ethics` — o vetor é decisão automatizada
   sobre pessoas e o pacote já tem a guarda E-00, que tira o check de escopo em
   alvo sem IA (o que resolve elegantemente `reconcilia`/`giva`). Mas o dano é de
   confidencialidade, e `S-09`/`P-12` também se defendem. → **PENDÊNCIA D-06**.
2. **`llm_egress` no `pse-config.yaml`.** Introduz uma declaração nova do
   consumidor. Precisa entrar no schema e em `COMO-ADOTAR.md`. Cuidado: é
   declaração que **liga** o check, não que o afrouxa — omissão deve levar a
   indeterminado (bloqueia), nunca a verde. → **PENDÊNCIA D-07**.
3. **O dado é real?** Se `juridico-platform` e `Central` só processam dado
   sintético/público, o CRÍTICO nunca deveria disparar. → **PENDÊNCIA A-02 / A-04**.
