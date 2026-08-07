# Proposta de check — **S-09 · PAN não mascarado em log, resposta ou persistência**

> **ESPECIFICAÇÃO, NÃO IMPLEMENTAÇÃO.** Nenhum código de check foi escrito nesta
> rodada. Este documento é o que precisa ser ratificado antes de existir código.

**Origem:** o estrato. O vetor foi visto em `danzeroum/reconcilia@2a89a1b`, num
parser de EDI da Rede que lê `card_number` de posição fixa. Não é regra genérica
de PCI traduzida para YAML — é o que o alvo real tem.

---

## 1. O vão

`pse/data/pii-patterns.yaml` tem hoje:

```yaml
identificadores: [cpf, rg, cnh, passaporte, cns, titulo_eleitor]
contato: [email, e_mail, telefone, celular, endereco, cep_residencial]
credenciais: [password, senha, hashed_password, token, api_secret]
```

**Não há número de cartão.** Consequência medida: a PSE rodou contra um sistema de
reconciliação de adquirentes que processa PAN em 5 arquivos e **não produziu um
único achado sobre cartão**. P-01 não conhece o termo, S-03 não conhece o valor,
S-05 não conhece o campo.

Não é um buraco em ética ou em documentação: é o dado de maior valor de mercado no
alvo, invisível para a régua.

---

## 2. O vetor real, no alvo real

Todos os fatos abaixo estão em `reconcilia@2a89a1b`, verificados por leitura.

### 2.1 Onde o PAN entra

| Arquivo:linha | Fato |
|---|---|
| `src/infrastructure/parsers/rede_layouts.py:63` | `"card_number": (60, 79),  # masked` — layout `012` |
| `src/infrastructure/parsers/rede_layouts.py:77` | `"card_number": (60, 79),` — layout `024`, **mesmo offset, sem o comentário** |
| `src/infrastructure/acquirers/cielo_edi_parser.py:32` | `"card_number": (97, 116)` |

Uma janela de 19 caracteres em posição fixa de arquivo EDI. **19 é exatamente o
comprimento máximo de um PAN.**

> **O comentário `# masked` é o caso-escola de D-01.** Ele *afirma* que o campo
> vem mascarado. Um check que lesse comentários concluiria "conforme" e ficaria
> verde — e o layout `024`, duas dúzias de linhas abaixo, tem o mesmo campo sem
> comentário nenhum. **A afirmação não é o fato.** O check proposto nunca deve
> ler esse comentário, para nada.

### 2.2 Onde o PAN vive

| Arquivo:linha | Fato |
|---|---|
| `src/infrastructure/acquirers/rede_torc_parser.py:265-266` | `card_number = fields[7]` → `card_last_4 = card_number[-4:]` |
| `src/infrastructure/acquirers/cielo_edi_parser.py:115-116` | `card_number = record.get("card_number", "")` → `card_last_4 = card_number[-4:]` |
| `src/infrastructure/acquirers/rede_api_parser.py:141-142` | `_card_last_4(card_number)` |

O PAN completo existe **em variável**, e só os 4 últimos entram no dicionário de saída.

### 2.3 O tratamento CORRETO — que não pode virar achado

| Arquivo:linha | Fato |
|---|---|
| `rede_torc_parser.py:281` | saída expõe `"cartao_last4": card_last_4` |
| `cielo_edi_parser.py:126` | saída expõe `"card_last_4": card_last_4` |
| `tests/unit/infrastructure/test_cielo_edi_parser.py:57` | fixture `"card_number": "************1234"` |
| `tests/utils/rede_edi_sample.py:82, 95` | idem |

**Este é o caso D-08 do check.** O alvo faz truncamento para últimos 4 — o
tratamento que o PCI DSS aceita — e mascara as próprias fixtures. Um check que
disparasse aqui seria falso-positivo em cima de quem faz certo.

---

## 3. A régua nova proposta

Arquivo novo no pacote: **`pse/data/pan-patterns.yaml`**. Mora no pacote, como
toda régua — o consumidor não edita.

```yaml
# Regua de PAN (Primary Account Number). NUNCA copiada para o consumidor.
# Um PAN e o unico dado desta suite cuja deteccao tem verificacao aritmetica
# propria (Luhn) — e por isso o unico em que o achado pode ser afirmado com
# alta confianca a partir do literal.

# 1. Nomes de campo que carregam PAN.
campos:
  - card_number
  - cardnumber
  - numero_cartao
  - num_cartao
  - pan
  - primary_account_number
  - card_no
  - cc_number
  - credit_card

# 2. Nomes que indicam o dado JA TRATADO — nunca disparam (D-08).
campos_seguros:
  - card_last_4
  - card_last4
  - cartao_last4
  - last_four
  - bin
  - card_bin
  - card_token
  - card_hash
  - card_fingerprint
  - masked_card
  - card_brand
  - card_expiry

# 3. Funcoes cuja chamada prova o tratamento (ancora no FATO, D-08).
tratamentos:
  - mascarar
  - mask
  - redact
  - truncat
  - last4
  - last_4
  - tokeniz
  - hash
  - sha
  - hmac
  - encrypt
  - cifrar

# 4. Deteccao do VALOR. 13 a 19 digitos, com separadores opcionais.
#    Este regex sozinho e inutil: ver `validacao` abaixo.
valor:
  regex: '(?<![0-9])(?:[0-9][ -]?){12,18}[0-9](?![0-9])'
  # NUNCA emitir achado sem AS DUAS validacoes:
  validacao:
    luhn: true          # digito verificador (ISO/IEC 7812)
    bin_conhecido: true # os 1-6 primeiros digitos numa faixa de emissor real

# 5. Faixas de BIN. Um numero que passa Luhn mas nao esta em faixa de emissor
#    e um numero que passa Luhn — nao e um cartao.
bin_ranges:
  visa:        {prefixos: ["4"],                                    comprimentos: [13, 16, 19]}
  mastercard:  {prefixos: ["51-55", "2221-2720"],                   comprimentos: [16]}
  amex:        {prefixos: ["34", "37"],                             comprimentos: [15]}
  elo:         {prefixos: ["4011", "4312", "4389", "5041", "6277", "6362", "6363", "5067", "5090"],
                comprimentos: [16]}
  hipercard:   {prefixos: ["606282", "3841"],                       comprimentos: [16, 19]}
  diners:      {prefixos: ["300-305", "3095", "36", "38-39"],       comprimentos: [14]}
  discover:    {prefixos: ["6011", "622126-622925", "644-649", "65"], comprimentos: [16, 19]}
  jcb:         {prefixos: ["3528-3589"],                            comprimentos: [16, 19]}

# 6. Numeros de teste publicados pelas bandeiras. Passam Luhn E BIN, e nao sao
#    cartao de ninguem. Allowlist explicita, no pacote.
pan_de_teste:
  - "4111111111111111"   # Visa
  - "4012888888881881"   # Visa
  - "5555555555554444"   # Mastercard
  - "5105105105105100"   # Mastercard
  - "378282246310005"    # Amex
  - "371449635398431"    # Amex
  - "6011111111111117"   # Discover
  - "30569309025904"     # Diners
```

### Por que Luhn é inegociável

**Medido no alvo real.** As fixtures de `reconcilia` usam:

| Literal | Dígitos | Luhn |
|---|---|---|
| `1234567890123456789` (`tests/integration/test_cielo_integration.py:88`) | 19 | **inválido** |
| `9876543210987654321` (`tests/integration/test_cielo_integration.py:98`) | 19 | **inválido** |
| `4111111111111111` (número de teste Visa) | 16 | **válido** |
| `************1234` (fixture mascarada) | 4 | não aplicável |

Um check de "13-19 dígitos" produziria **2 CRÍTICOs falsos** só neste arquivo.
Luhn os elimina aritmeticamente, sem heurística e sem opinião.

E Luhn **sozinho** não basta: cerca de 1 em 10 sequências numéricas aleatórias
passa. Por isso a régua exige **Luhn E faixa de BIN E comprimento coerente com a
bandeira** — três condições independentes. Um NSU de 16 dígitos, um ID de
transação, um timestamp concatenado: nenhum satisfaz as três.

---

## 4. Especificação do check

| Campo | Valor |
|---|---|
| **ID** | `S-09` |
| **Pacote** | `security` (o par é `P-01`; ver §7) |
| **Título** | PAN não mascarado em log, resposta de API ou persistência |
| **Base legal** | PCI DSS v4.0 req. 3.3 e 3.5 · LGPD Art. 46 |
| **Tipo** | `estatico` |
| **Modo** | `inventory` |
| **Severidade** | **CRÍTICO** (valor de PAN real) · **ALTO** (campo `card_number` cru num sink, sem valor) |
| **Status proposto** | `previsto-fase-4` até ser implementado |

### 4.1 Os três vetores

**V1 — PAN literal no fonte (CRÍTICO).**
Constante de string que casa `valor.regex` **E** passa Luhn **E** cai em
`bin_ranges` **E** não está em `pan_de_teste`. Vale em qualquer arquivo,
incluindo `.env` e fixtures — um PAN real numa fixture é um PAN real vazado.

**V2 — campo de PAN indo cru para um sink (CRÍTICO em Python, ALTO fora).**
Via AST, mesma mecânica de P-01: identificador cujo nome está em `campos`,
entrando como argumento de:
- chamada de log (reusar `RX_LOG` de P-01);
- retorno de rota HTTP / construção de dict de resposta;
- chamada de persistência (`execute`, `insert`, `save`, `commit`, `create`, `update`).

**V3 — campo de PAN persistido sem cifra (ALTO).**
`card_number` como coluna em `CREATE TABLE` / modelo ORM, sem que o mesmo módulo
chame algo de `tratamentos`.

### 4.2 Supressão — o cuidado D-08, explícito

O check **NÃO dispara** quando:

1. o identificador está em `campos_seguros` (`card_last_4`, `bin`, `card_token`…);
2. o argumento passa por uma chamada de `tratamentos` — **chamada que executa**,
   nunca comentário. `mascarar(card_number)` é conforme, como em P-01;
3. o valor literal casa `^\**\d{0,4}$` ou tem ≤6 dígitos após remover `*`/`X`
   — já mascarado (`************1234` do alvo real);
4. o literal está em `pan_de_teste`;
5. o valor não passa Luhn **ou** não cai em faixa de BIN.

**Aplicado ao alvo real, o resultado esperado:**

| Fato em `reconcilia` | Veredito esperado |
|---|---|
| `"cartao_last4": card_last_4` (saída dos 3 parsers) | **não dispara** — `campos_seguros` |
| `"card_number": "************1234"` (2 fixtures) | **não dispara** — regra 3 |
| `card_number="1234567890123456789"` (2 fixtures) | **não dispara** — Luhn inválido |
| `# masked` em `rede_layouts.py:63` | **irrelevante** — comentário nunca é lido |
| `card_number = fields[7]` sem sink | **não dispara** — variável local não é vetor |
| PAN indo para `logger.*` ou resposta, se existir | **CRÍTICO** |

**Resultado previsto hoje em `reconcilia`: zero achados** — porque o alvo trata
corretamente. Isso é a validação da especificação, não a sua falha. Um check que
nasce disparando no primeiro alvo é suspeito; um que nasce reconhecendo o
tratamento correto e fica de guarda é o que esta suíte quer.

### 4.3 Quando ficar INDETERMINADO

Precisão sobre recall onde não há AST:

- arquivo `.py` que não parseia → `CheckIndeterminado` (via `scan.arvore`);
- em `.js`/`.ts`/`.java` (sem AST), V2 e V3 **não rodam** — só V1, que é
  aritmético e não precisa de contexto. A ausência de V2/V3 fora do Python entra
  em `ctx.relatorio("cobertura_parcial", …)`, como S-03 e S-05 já fazem;
- campo de PAN alcançando um sink por **variável intermediária de outro módulo**
  → não rastreável estaticamente: **não forçar achado**, registrar cobertura parcial.

### 4.4 Sanitização — obrigatória e específica

`pse/sanitize.py` precisa ganhar `RX_PAN` **junto** com o check, e a ordem
importa: um laudo que denuncia PAN em claro e o republica em `harness/runs/` é
exatamente o defeito D-02 que a suíte já pagou uma vez.

Mascaramento proposto, diferente do `_borda` genérico: **preservar os 4 últimos**,
não os 2 primeiros — `************1234`. É a forma que o revisor reconhece, é o que
o PCI DSS permite exibir, e é coerente com o que o próprio alvo já faz.

### 4.5 Mutação canônica (obrigatória — senão o check reprova a si mesmo)

```yaml
canonical_mutation:
  descricao: PAN valido (Luhn + BIN) vai cru para o log
  arquivos:
    app.py: |
      import logging
      logger = logging.getLogger(__name__)


      def registrar(card_number):
          logger.info("transacao card_number=%s", card_number)
  espera_severidade: CRITICO
```

E o par negativo, no `consumidor_bom` (falso-positivo em CRÍTICO custa mais que
falso-negativo):

```python
def registrar(card_number):
    logger.info("transacao cartao=%s", card_last_4(card_number))
```

---

## 5. Testes que a implementação tem de trazer

1. `4111111111111111` em `logger.info` → **1 CRÍTICO**.
2. `1234567890123456789` (Luhn inválido) → **0 achados**. *Este é o teste que
   justifica Luhn; sem ele, 16 dígitos quaisquer viram falso-positivo.*
3. `************1234` → **0 achados**.
4. `logger.info(..., mascarar(card_number))` → **0 achados** (D-08).
5. `card_last_4` em qualquer sink → **0 achados**.
6. `4111111111111111` em `pan_de_teste` → **0 achados**.
7. Um `.js` com PAN literal válido → **1 achado**, e `cobertura_parcial` anotada.
8. Snippet de qualquer achado → **PAN mascarado no laudo** (D-02).
9. **`reconcilia@2a89a1b` inteiro → 0 achados** — regressão contra falso-positivo
   em código real que faz certo.

---

## 6. O que este check NÃO faz

- **Não valida conformidade PCI DSS.** Escopo, segmentação de rede e SAQ não são
  auditáveis estaticamente. O check cobre um requisito (3.3/3.5), não a norma.
- **Não decide se o alvo pode processar PAN.** Isso é do dono.
- **Não rastreia fluxo entre módulos.** Onde não alcança, registra cobertura
  parcial — nunca inventa nem silencia.

---

## 7. Ponto aberto para ratificação do dono

**`S-09` ou `P-12`?** Argumentei `security` porque a base primária é PCI DSS e o
vizinho natural é S-03 (PII em payload de erro). Mas PAN é dado pessoal sob LGPD,
e a mecânica de detecção é irmã de P-01 — `P-12` também se defende.

A decisão importa porque governa o `--packs` do consumidor: quem roda
`--packs privacy` num sistema de pagamento deveria receber este check?
→ **PENDÊNCIA D-05**.
