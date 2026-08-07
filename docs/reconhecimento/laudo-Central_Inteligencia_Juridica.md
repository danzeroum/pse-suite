# Laudo de reconhecimento — `danzeroum/Central_Inteligencia_Juridica`

**Setor:** legaltech — agentes jurídicos multi-agente, integração com tribunais, LLM.
**Commit auditado:** `2132f1ba127a683eede00cf0ed11751cdb376ec6` (clone raso)
**Suíte:** pse-suite `0.3.0` · `catalog_hash 33d5be7e…20e3` · modo `pse_inventory`
**Laudo bruto:** [`laudos/laudo-Central_Inteligencia_Juridica.json`](laudos/laudo-Central_Inteligencia_Juridica.json)

> A PSE afirma; o dono valida. Nenhum arquivo deste repositório foi alterado.

---

## 1. Veredito

| | |
|---|---|
| **veredito** | `violacao` |
| **exit_code** | **10** (violação com CRÍTICO — fail-closed) |
| findings | 27 — **3 CRÍTICO**, 20 ALTO, 4 MÉDIO |
| duração | 8,61 s |

---

## 2. Os três estados

**AUDITADO (13):** `E-00, E-04, E-05, E-07, E-10, P-01, P-03, P-04, P-06, P-07, P-09, S-04, S-06`

**NÃO-APLICÁVEL (4):** P-02, P-08 (catálogo ausente → P-04) · S-05, S-08 (manifesto ausente → S-04)

**FORA-DE-ALCANCE / INDETERMINADO (1):** E-06 — nenhum `fairness_dataset` declarado.

**NÃO-HABILITADO (10):** todo o Trabalho A. **PREVISTO (1):** E-08.

### FORA-DE-ALCANCE por linguagem

| Superfície | Volume | Estado |
|---|---|---|
| `.py` | 401 | **auditado** (AST) — maior base Python da rodada |
| `.js` | 12 | auditado — heurística, severidade rebaixada |
| `.yaml` / `.yml` | 190 | auditado (S-04/S-06) |
| **`.jsx`** | **33** | **FORA-DE-ALCANCE** |
| `.graphql`, `.mako`, `.jsonl` | 3 | **FORA-DE-ALCANCE** |

Sem `.java` / `.dart` / `.ex` / `.php`.

---

## 3. O controle correto que a PSE não puniu

`src/safety/pii.py` implementa `PIIDetector` / `redact_pii()` com padrões
brasileiros (EMAIL, OAB, CNPJ, CPF, PHONE, CEP), e é **chamado de fato** —
`grep` no AST-adjacent confirma chamadas reais, não menções:

| Arquivo:linha | Chamada |
|---|---|
| `src/agents/supervisor_agent.py:164, 420` | `"original_task": redact_pii(task_description)` |
| `src/protocols/safety_protocol.py:57` | `redacted = redact_pii(value)` |
| `src/memory/vector_memory.py:347-348` | `task = _redact_pii(task)` + `self._redact_obj(...)` |
| `src/integrations/adapters/djen_adapter.py:79` | `texto=_redact_pii(entry.get("texto") …)` |

**A PSE não acusou nenhum destes arquivos** — nem P-01, nem S-03. Correto (D-08):
o alvo faz a coisa certa nos pontos de **persistência e trilha de auditoria**, e a
régua não pune quem faz certo.

**Mas repare onde a redação NÃO está** — e isto é o vetor de §5:
`src/services/llm_client.py:35` envia `messages=[{"role":"user","content": prompt}]`
**sem passar por `redact_pii`**. A redação protege o que é *armazenado*; não
protege o que é *enviado ao modelo*.

---

## 4. Triagem dos achados

### 4.1 VIOLAÇÃO-PROVÁVEL (10)

#### S-04 · ALTO · terceiros no código sem manifesto (10)

Não existe `.privacy/third-party-manifest.yml`.

| Arquivo:linha | Terceiro |
|---|---|
| `src/services/datajud_client.py:32` | **DataJud / CNJ** — base nacional de processos |
| `src/agents/tribunal_api_client.py:22, 27` | **API de tribunal** |
| `src/integrations/adapters/djen_adapter.py:27` | **DJEN** — diário de justiça eletrônico |
| `src/integrations/adapters/tse_adapter.py:27` | TSE |
| `src/integrations/adapters/receita_cnpj_adapter.py:3` | Receita Federal |
| `src/integrations/ecac/adapter.py:191` | e-CAC |
| `src/fiscal/parser/xml_fiscal.py:71, 328` | schema fiscal |
| `src/fiscal/per_dcomp/serializer.py:45` | PER/DCOMP |

**Por que estes pesam mais que em outros alvos:** DataJud, tribunal e DJEN são as
fontes que trazem **dado de processo** para dentro do sistema. É precisamente o
material que pode estar sob segredo de justiça — e ele entra sem nenhum registro
de terceiro, sem DPA e sem declaração do que sai/entra (S-05 ficou N/A).

### 4.2 FALSO-POSITIVO-PROVÁVEL (10)

#### S-06 · CRÍTICO · credencial de fixture em teste (3)

| Arquivo:linha | Evidência (mascarada) |
|---|---|
| `tests/integration/test_datajud.py:85, 103` | `client = DataJudClient("tjsp", api_key="ch***")` |
| `tests/unit/test_api_security.py:47` | `headers={"Authorization": "Bearer no***"}` |

Os três CRÍTICOs do alvo são fixtures de teste. `test_api_security.py:47` é
especialmente irônico: o literal é um token **propositalmente inválido**, usado
para provar que a API o rejeita — o teste de segurança sendo acusado pela suíte
de segurança. → PENDÊNCIA S-01.

#### P-01 · ALTO · heurística sem AST (3)

| Arquivo:linha | Por quê |
|---|---|
| `scripts/smoke-producao-console.js:55` | `console.warn('⚠️ Sem token — endpoints autenticados retornarão 401/403.')` — a palavra `token` aparece **numa mensagem literal em português**, não há variável de credencial |
| `scripts/smoke_test_browser.js:66` | `console.group('2. Auth / Token')` — **um rótulo de seção de log** |
| `src/api/static/spa/assets/index-ffgJmG-l.js:40` | **bundle minificado** de vendor (React), 1 linha de milhares de caracteres |

Os três são o retrato exato do porquê P-01 rebaixa a severidade para ALTO fora do
Python: sem AST, "a palavra aparece perto de uma chamada de log" é tudo que dá
para saber. O mecanismo de proteção funcionou — nenhum destes virou CRÍTICO.

#### S-04 · ALTO · toolchain e artefato de build (4)

`.github/ISSUE_TEMPLATE/config.yml:4`, `.github/workflows/ci.yml:181`,
`src/api/static/spa/assets/index-ffgJmG-l.js:33`, `.env.example:97`.

Template de issue do GitHub, host de CI, bundle minificado e template de ambiente.

### 4.3 INCERTO (7)

| # | Achado | Por que não decido |
|---|---|---|
| 1 | **E-10 MÉDIO** — `src/integrations/orchestrator.py:104` (`def _investigate_inner`) | Orquestrador de investigação que chama inferência sem medida de confiança. Este é provavelmente **real** — mas não sei se a confiança é calculada na camada do agente |
| 2 | **E-10 MÉDIO** — `examples/patterns/memory_management.py:31` | Arquivo de **exemplo/documentação**. Cobrar incerteza de um exemplo didático é discutível |
| 3–4 | **E-10 MÉDIO ×2** — `tests/integration/test_intelligence_orchestrator.py:146`, `tests/unit/integrations/test_risk_engine.py:79` | São testes (`test_risk_score_with_protesto`, `test_empty_results_zero_score`). Mesmo padrão de falso-positivo de E-10 em `tests/` visto no juridico-platform |
| 5 | **P-04 ALTO** — catálogo ausente | Caminho *default* da suíte. Mas aqui o argumento de mérito é forte: um sistema que ingere processo de tribunal **deveria** ter catálogo. Ver PENDÊNCIA D-02 |
| 6 | **P-07 ALTO** — modelo de consentimento ausente | Idem |
| 7 | **S-04 ALTO** — `scripts/dev/fase2-stubs.py:473` | Stub de desenvolvimento. O host é real, mas o arquivo é andaime de fase — pode ou não sobreviver ao próximo release |

Somam-se a estes o **E-06 indeterminado** e os **33 `.jsx` fora de alcance**, que
não são achados mas também não são verde.

---

## 5. Dado de processo indo a LLM — o segundo vetor

Levantado por inspeção dirigida; a PSE de hoje **não produz este achado**.

`src/services/llm_client.py:27-35`:

```python
def gerar_resposta_ollama(prompt: str, modelo: str = "llama3") -> str:
    logger.info("Enviando prompt para o modelo '%s'", modelo)
    …
    messages=[{"role": "user", "content": prompt}],
```

**O que a régua do próprio alvo cobre e o que não cobre:**
`src/safety/pii.py` detecta EMAIL, OAB, CNPJ, CPF, PHONE, CEP. Note que "OAB" ali
é o **número de inscrição do advogado tratado como PII** — não é o conceito de
**sigilo profissional**. Não há, em lugar nenhum do alvo, nem na régua da PSE:

- número de processo em **segredo de justiça**;
- marcador `nivel_sigilo` / `em_segredo` de retorno de tribunal;
- sigilo profissional da advocacia (EOAB Art. 7º, II e §6º);
- dado sob segredo de justiça vindo do DataJud/DJEN.

Confirmação medida: `grep -i 'segredo de justiça|sigilo|em_segredo'` em todos os
`.py` dos dois alvos jurídicos retorna **1 ocorrência isolada** — o conceito
praticamente não existe no código.

**Onde a suíte para hoje:** S-04 registra o host (aqui, Ollama local — o que
enfraquece o caso de egresso neste alvo específico). Ninguém olha o conteúdo do
prompt, e nenhum termo de sigilo existe na régua.

Especificação em [`PROPOSTA-CHECK-SIGILO-LLM.md`](PROPOSTA-CHECK-SIGILO-LLM.md).
Pergunta que sobra: `tribunal_api_client.query_real_process()` traz processo em
segredo? → PENDÊNCIA A-04.

---

## 6. Resumo da triagem

| Classe | Qtd. | % |
|---|---|---|
| VIOLAÇÃO-PROVÁVEL | 10 | 37% |
| FALSO-POSITIVO-PROVÁVEL | 10 | 37% |
| INCERTO | 7 | 26% |
| **Total** | **27** | |

Conferência: `python scripts/verificar_triagem.py`.

Os **3 CRÍTICOs do alvo são todos fixtures de teste** — ou seja, o `exit 10`
deste laudo é dirigido inteiramente por falso-positivo. O `exit 20` que E-06 já
garantiria seria o veredito mais fiel ao que a suíte de fato apurou.
Registrado em PENDÊNCIA S-01.
