# PENDÊNCIA_DO_DONO — o que a PSE não pode decidir

> **A PSE afirma, o DONO valida.** Cada item aqui é uma pergunta que a suíte não
> tem como responder de fora do repositório, e que muda o veredito de um ou mais
> achados. Nenhuma foi presumida.

Três famílias:
**A —** o alvo processa dado real? · **D —** decisão de doutrina/política ·
**S —** refino candidato da própria suíte (fica para uma rodada com bump).

---

## A · O alvo processa dado real em produção?

Esta é a pergunta que mais muda severidade em toda a rodada. Um `CRÍTICO` sobre
dado sintético é ruído; o mesmo `CRÍTICO` sobre dado de titular é incidente.

### A-01 · `reconcilia` — o PAN completo é persistido ou logado?

**Fato.** `rede_torc_parser.py:265-266`, `cielo_edi_parser.py:115-116` e
`rede_api_parser.py:141-142` leem o PAN completo para variável e expõem só
`card_last_4` na saída. As fixtures usam `************1234` — mascaramento correto.

**O que não consigo ver:** entre a leitura do EDI e o descarte, o PAN completo
existe em memória. Ele chega a algum `logger`, a alguma coluna, a algum payload de
erro, a algum dump de debug?

**Pergunta:** os arquivos EDI de Cielo/Rede/Stone processados em produção trazem
PAN completo ou já vêm truncados pela adquirente? E há retenção do arquivo bruto?

**Impacto:** define se o check S-09 proposto nasce com achado real neste alvo, e
define o escopo PCI DSS do sistema. **Bloqueante para a implementação de S-09.**

### A-02 · `juridico-platform` — `LLM_PROVIDER` em produção é `openai` ou `ollama`?

**Fato.** `config.py:102` → default `https://api.openai.com/v1`.
`generate.py:31` escolhe o ramo em runtime. `orchestrator.py:78-84` manda nome de
reclamante, nome de reclamada e narrativa dos fatos, **sem nenhuma redação**.

**Pergunta:** qual valor de `LLM_PROVIDER` está em produção? Se `openai`: existe
DPA com o provedor, e há acordo de não-treinamento sobre os prompts?

**Impacto:** decide entre **ALTO** (egresso externo sem redação) e **MÉDIO**
(local sem redação) no E-11 proposto. Sem a resposta, o check fica
**INDETERMINADO** por especificação — que bloqueia, e está certo.

### A-03 · `Criptotrade` — os agentes decidem sobre pessoas ou sobre ativos?

**Fato.** A guarda E-00 computou indícios de decisão automatizada e colocou o
pack de ética **em escopo**. E-06 ficou indeterminado (sem `fairness_dataset`), o
que sozinho leva o alvo a exit 20.

**Pergunta:** algum agente decide sobre **conta de pessoa** — recusar cadastro,
bloquear conta, limitar operação, negar saque? Ou só sobre ordens e ativos?

**Impacto:** se decide sobre pessoas, E-06 (fairness), E-01/E-02 (explicação,
decision log) e E-04 (rota humana) passam de "não achou" a obrigatórios. Se não,
boa parte do pack de ética é legitimamente N/A — e isso deve ser **declarado**
em `pse-config.yaml`, não inferido.

### A-04 · `Central_Inteligencia_Juridica` — o DataJud traz processo em segredo?

**Fato.** `datajud_client.py:32`, `tribunal_api_client.py:22,27`,
`djen_adapter.py:27` ingerem dado de tribunal.
`tribunal_api_client.query_real_process()` consulta processo por número.
`grep` por termos de sigilo nos dois alvos jurídicos retorna **1 ocorrência** —
o conceito praticamente não existe no código.

**Pergunta:** a API do tribunal retorna processos em segredo de justiça? Se sim,
existe filtro **antes** da ingestão, ou o dado entra e só depois passa por
`redact_pii` (que não conhece sigilo, só PII)?

**Impacto:** define se `marcadores_sigilo` da régua E-11 encontrariam algo. Hoje
não encontrariam — e a ausência do marcador pode significar "não há processo em
segredo" **ou** "há e ninguém marca". As duas são muito diferentes.

### A-05 · `dadosabedoria` — SISVAN e INEP trazem microdado?

**Fato.** `adaptadores/sisvan.py:151` (nutrição/saúde) e `adaptadores/inep.py:87`
(educação) ingerem sem manifesto de terceiros.

**Pergunta:** os endpoints consumidos devolvem **agregado** ou **microdado**
individualizável? SISVAN em particular pode trazer dado de saúde — sensível pelo
Art. 11, que não admite legítimo interesse.

**Impacto:** se é microdado de saúde, P-08 (hoje N/A por falta de catálogo)
passaria a CRÍTICO assim que o catálogo existisse.

---

## D · Decisões de doutrina e política

### D-01 · `.tsx`/`.jsx` fora de alcance — ampliar a suíte ou declarar o limite?

**Fato medido nesta rodada:**

| Alvo | `.tsx`/`.jsx` não auditados |
|---|---|
| dadosabedoria | 88 |
| juridico-platform | 66 |
| reconcilia | 43 |
| Central | 33 |
| Criptotrade | 26 |
| giva | 25 |
| **Total** | **281 arquivos** |

`.ts` está no alcance de P-01/P-06/S-04/S-06/E-04 (heurística); **`.tsx` não está
em conjunto de extensão nenhum**. Um `console.log(user.cpf)` num componente React
é invisível para a suíte inteira.

**Pergunta:** adicionar `.tsx`/`.jsx` aos conjuntos existentes (ganho imediato,
mesma heurística de linha já usada para `.ts`), ou manter fora e declarar
explicitamente em `COMO-ADOTAR.md` que frontend React não é auditado?

**Recomendação:** adicionar. É uma linha em cinco conjuntos de extensão, e a
severidade rebaixada fora do Python já protege contra falso-positivo. O status
quo é o pior dos dois mundos: silêncio que se parece com verde.

### D-02 · P-04/P-07 disparam em quem nunca adotou a PSE

**Fato.** Nos 6 alvos, P-04 e P-07 dispararam ALTO com a mesma mensagem, sempre
apontando o **caminho default da suíte** (`tests/qa/catalog.yaml`,
`tests/qa/consent-model.yaml`). São **12 dos 148 achados** da rodada (~8%), com
informação zero sobre o código auditado — nenhum dos 6 se declarou consumidor.

**Pergunta:** "catálogo ausente" em repositório que não adotou o padrão é achado
de conformidade, ou é `SkipCheck` ("o alvo não declarou adoção")?

**Tensão real, e por isso é do dono:** transformar em `SkipCheck` cria um jeito de
sumir com P-04 — basta não declarar. Isso é literalmente "a trava que o vigiado
desliga em silêncio". Manter como está preserva a trava e paga com ruído.

**Recomendação:** manter o achado, e distinguir a mensagem quando o consumidor
não declarou `catalog_path` — dizendo "path default; declare `catalog_path` ou
adote o padrão", em vez de "catálogo ausente".

### D-03 · `giva` está no escopo certo?

**Fato.** GIVA valida planilha fiscal NCM/ICMS. 13 checks rodaram sobre 79 `.py` e
produziram **zero achados ancorados em fato**; os únicos 2 são artefato ausente.

**Pergunta:** GIVA trata dado de pessoa natural em algum ponto? Se não, o pack de
privacidade é legitimamente N/A e isso deveria estar **declarado**.

### D-04 · API pública de governo é "terceiro" para o Art. 39?

**Fato.** 26 dos 28 achados de `dadosabedoria` e 13 dos 36 de `juridico-platform`
são S-04 sobre `gov.br` (IBGE, BCB, SICONFI, PNCP, CAGED, Receita, SEFAZ, DataJud…).

**Pergunta:** consumir API pública de consulta configura operador de tratamento
que exige DPA? Ou basta registrar a integração com residência e finalidade,
dispensando `dpa_signed`?

**Impacto:** o manifesto já tem `required: true|false` por integração — se
"público" mapear para `required: false`, o CRÍTICO de DPA não dispara e o ALTO de
registro permanece. Precisa de posição do dono para virar orientação em
`COMO-ADOTAR.md`.

### D-05 · O check de PAN é `S-09` ou `P-12`?

Base primária é PCI DSS (→ security), mas PAN é dado pessoal sob LGPD e a mecânica
é irmã de P-01 (→ privacy). Governa o que um consumidor recebe ao rodar
`--packs privacy`. Detalhe em [`PROPOSTA-CHECK-PAN-PCI.md`](PROPOSTA-CHECK-PAN-PCI.md) §7.

### D-06 · O check de sigilo é `E-11`, `S-09` ou `P-12`?

`ethics` tem a vantagem da guarda E-00 (tira o check de escopo em alvo sem IA,
resolvendo `reconcilia`/`giva` de graça). Mas o dano é de confidencialidade.
Detalhe em [`PROPOSTA-CHECK-SIGILO-LLM.md`](PROPOSTA-CHECK-SIGILO-LLM.md) §7.

### D-07 · Introduzir `llm_egress` no `pse-config.yaml`?

E-11 precisa saber se o sink de LLM é externo ou local quando o provedor é
decidido em runtime. Proposta: declaração `llm_egress: external|local`, **cuja
omissão leva a INDETERMINADO** (bloqueia), nunca a verde. Exige entrada no schema
e em `COMO-ADOTAR.md`.

---

## S · Refinos candidatos da própria suíte

**Nenhum foi implementado nesta rodada** — reconhecimento não altera a suíte, e a
Etapa 2b não encontrou o falso-positivo que autorizaria exceção. Todos exigem bump.

### S-01 · P-06/S-06 em caminhos de teste — o mais urgente

**Medido:** dos **19 achados CRÍTICOs de credencial** (P-06 + S-06) na rodada,
**18 estão sob `tests/`** — o único fora é
`reconcilia/scripts/generate_test_password.py:9`:

| Alvo | CRÍTICOs de credencial | sob `tests/` |
|---|---|---|
| Criptotrade | 9 | **9** (8× P-06 em `test_auth.py`/`test_account.py`, 1× S-06) |
| reconcilia | 7 | **6** |
| Central | 3 | **3** |

Valores como `wrong-password`, `test-secret`, `new-password` — e em
`Central/tests/unit/test_api_security.py:47`, um token **propositalmente inválido**
usado para provar que a API o rejeita.

**Por que importa mais que qualquer check novo:** é exatamente o cenário D-08. 18
CRÍTICOs falsos ensinam o operador a ignorar a categoria "credencial hardcoded" —
e aí o 19º, que é real, passa junto. Em `Central`, os 3 CRÍTICOs que produzem o
`exit 10` são **todos** fixtures: o veredito do laudo é dirigido por falso-positivo.

**Cuidado ao refinar:** "ignorar `tests/`" é perigoso — segredo real vaza em teste
com frequência. A direção defensável é **rebaixar de CRÍTICO para MÉDIO** em
caminho de teste (mantém visível, para de dirigir o gate), nunca suprimir.
Alternativa mais precisa: detectar valor obviamente sintético
(`test`, `example`, `dummy`, `fake`, `changeme`, `xxx`) **no próprio literal**.

### S-02 · P-01 acusa e-mail em domínio reservado

`reconcilia/scripts/seed_mvp.py:96,105` e `seed_test_user.py:83` produzem 3
CRÍTICOs sobre `test@example.com` — **RFC 2606**, num script de seed.

**A incoerência é da régua:** `third-party-endpoints.yaml` já tem `example.com` na
lista `ignorar`, e **P-01 não a consulta**. O mesmo domínio é ignorado por S-04 e
acusado por P-01.

**Direção:** fazer P-01 (e S-03) consultarem a lista `ignorar` para valores de
e-mail literais. Estende naturalmente para `example.org`, `example.net`,
`.invalid`, `.test`, `.localhost`.

### S-03 · S-04 gera volume alto em plataforma de ingestão

`dadosabedoria`: **26 achados de S-04** num alvo de 28. Um achado por host
distinto, incluindo `robots.ts`, testes de frontend e 4 variantes de URL do mesmo
CAGED. **77 dos 148 achados da rodada (52%) são S-04** — mais da metade do laudo
consolidado é um único check.

**Direção possível:** agrupar por *integração* (host + arquivo de origem) em vez
de por host bruto, e não contar host que aparece só em `.env.example`,
`robots.ts`, workflow de CI ou `*.test.ts`. Requer cuidado: o critério não pode
virar um jeito de esconder integração real movendo-a para um arquivo "ignorado".

### S-04 · P-01 não detecta logger inline — falso-NEGATIVO

**Descoberto na Etapa 2b** ([`PROVA-NAO-FALSO-POSITIVO.md`](PROVA-NAO-FALSO-POSITIVO.md) §4):

```python
logging.getLogger(__name__).info("cpf=%s", cpf)   # NÃO detectado
logger.info("cpf=%s", cpf)                        # detectado (CRÍTICO)
```

`scan.nome_chamado` não atravessa um nó `ast.Call`, então o primeiro resolve para
`'info'` e `RX_LOG` não casa.

**Impacto medido nesta rodada: ZERO.** O padrão `getLogger(...).<nivel>(` ocorre
**0 vezes** nos 6 alvos — todos usam a forma nomeada. É gap latente, não achado
perdido aqui.

**Direção:** em `nome_chamado`, ao encontrar `ast.Call` na cadeia de atributos,
continuar a resolução por `.func` em vez de parar.

### S-05 · E-10 dispara em teste e em healthcheck

10 dos 13 achados de E-10 na rodada são falso-positivo provável: funções de teste
(`test_score_dentro_do_intervalo`) e `def healthy(...)` que só contém uma chamada
casando `^score$`. É MÉDIO e **não bloqueia**, então o custo é baixo — mas o
padrão é o mesmo de S-01.

---

## Resumo

| Família | Itens | Bloqueia o quê |
|---|---|---|
| **A** — dado real | A-01…A-05 | severidade dos achados; **A-01 bloqueia S-09**; A-02 bloqueia o veredito de E-11 |
| **D** — doutrina | D-01…D-07 | alcance da suíte; **D-05/D-06/D-07 bloqueiam a implementação dos 2 checks** |
| **S** — refino | S-01…S-05 | qualidade do laudo; todos exigem bump, nenhum feito aqui |

**Ordem recomendada:** **S-01** primeiro (17 CRÍTICOs falsos corroendo a
credibilidade do gate hoje), depois **D-01** (281 arquivos invisíveis), depois
**A-01/A-02** (destravam os dois checks novos).
