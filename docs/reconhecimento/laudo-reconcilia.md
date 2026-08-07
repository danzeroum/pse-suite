# Laudo de reconhecimento — `danzeroum/reconcilia` (ConciliaIA)

**Setor:** fintech — reconciliação financeira de adquirentes (Cielo, Rede, Stone).
**Commit auditado:** `2a89a1b293a58548c7e90c4a1644e7a33ee973e8` (clone raso)
**Suíte:** pse-suite `0.3.0` · `catalog_hash 33d5be7e…20e3` · modo `pse_inventory`
**Comando:** `pse --path <clone> --output laudo-reconcilia.json` (sem `--config`)
**Laudo bruto:** [`laudos/laudo-reconcilia.json`](laudos/laudo-reconcilia.json)

> A PSE **afirma**; o dono **valida**. Tudo abaixo é hipótese ancorada em
> `arquivo:linha`, com evidência mascarada. Nenhum arquivo deste repositório foi
> alterado.

---

## 1. Veredito

| | |
|---|---|
| **veredito** | `violacao` |
| **exit_code** | **10** (violação com CRÍTICO — fail-closed) |
| findings | 30 — **16 CRÍTICO**, 14 ALTO |
| duração | 3,46 s |

---

## 2. Os três estados — o que a suíte fez com cada check

**AUDITADO (13)** — olhou e decidiu:
`E-00, E-04, E-05, E-07, E-10, P-01, P-03, P-04, P-06, P-07, P-09, S-04, S-06`

**NÃO-APLICÁVEL (4)** — pré-condição declarativa ausente, não bloqueia:

| Check | Motivo |
|---|---|
| P-02, P-08 | catálogo de dados ausente — cobrado por P-04 |
| S-05, S-08 | manifesto de terceiros ausente — cobrado por S-04 |

**FORA-DE-ALCANCE / INDETERMINADO (1)** — bloqueia igual a violação:

| Check | Motivo |
|---|---|
| E-06 | nenhum `fairness_dataset` declarado em `pse-config.yaml`. A suíte **não sai procurando** qual arquivo seria o dataset |

**NÃO-HABILITADO (10)** — Trabalho A não pedido nesta execução:
`P-05, P-10, P-11, S-01, S-02, S-03, S-07, E-01, E-02, E-03, E-09`

**PREVISTO E AUSENTE (1):** `E-08` (lineage) — `previsto-fase-3`.

### FORA-DE-ALCANCE por linguagem — declarado, não silenciado

| Superfície | Volume | Estado |
|---|---|---|
| `.py` | 204 arquivos | **auditado** (AST) |
| `.ts` | 35 arquivos | auditado — heurística de linha (P-01/P-06/S-04/S-06/E-04), severidade rebaixada |
| `.sql` | 3 arquivos | auditado (P-02/P-03/P-09) |
| **`.tsx`** | **43 arquivos** | **FORA-DE-ALCANCE** — `.tsx` não está em nenhum conjunto de extensões da suíte |

Não há `.java`, `.dart`, `.ex` nem `.php` neste alvo.
**O frontend React inteiro (43 `.tsx`) não foi auditado.** Isso não é "sem
achado": é ausência de alcance. Ver PENDÊNCIA D-01.

---

## 3. Triagem dos achados

> Atribuição por achado, verificável: [`triagem.json`](triagem.json) +
> `python scripts/verificar_triagem.py`. Os índices abaixo são a posição do
> finding no laudo JSON.

### 3.1 VIOLAÇÃO-PROVÁVEL (7)

#### P-01 · CRÍTICO · e-mail de titular real vai cru para o log de autenticação (5)

| Arquivo:linha | Evidência (mascarada) |
|---|---|
| `src/api/routes/auth.py:69` | `logger.warning("login_blocked_locked_out", email=request.email, retry_after=locked_for)` |
| `src/api/routes/auth.py:79` | `logger.warning("login_failed_user_not_found", email=request.email)` |
| `src/api/routes/auth.py:95` | `logger.warning("login_failed_invalid_password", user_id=str(user.id), email=user.email)` |
| `src/infrastructure/repositories/postgresql_user_repository.py:36` | `self._logger.debug("user_not_found", email=email)` |
| `src/infrastructure/repositories/postgresql_user_repository.py:39` | `self._logger.debug("user_found", user_id=str(model.id), email=email)` |

**Por que é violação e não menção (D-01):** o fato não é a palavra `email` — é
que o AST mostra a variável `request.email` / `user.email` **entrando como
argumento nomeado** de uma chamada de log, sem passar por nenhuma função de
mascaramento. `email` está na régua do pacote (`pii-patterns.yaml → contato`).

**Agravante de contexto:** as três linhas de `auth.py` estão em caminhos de
**falha de login** — os mais logados e os mais exportados para observabilidade
externa. A linha 95 é a pior: registra o e-mail exatamente quando a senha está errada.

> Contraste que mostra que o repo *sabe* fazer certo: a linha 86 do mesmo arquivo
> loga `login_failed_inactive_user` com **apenas** `user_id` — e não foi acusada.
> A régua não pune quem faz certo (D-08).

#### S-04 · ALTO · terceiro que processa dado de transação, sem manifesto (2)

| Arquivo:linha | Terceiro |
|---|---|
| `src/infrastructure/acquirers/stone_api_client.py:21` | adquirente Stone — cliente de produção |
| `src/api/gateway.py:28` | host externo no gateway da API |

**Vetor real:** adquirentes processam dado de transação de titular. São exatamente
os terceiros que o Art. 39 quer registrados, com DPA, residência e base de
transferência. Não existe `.privacy/third-party-manifest.yml` no repositório — o
que também deixou **S-05 e S-08 sem o que auditar** (N/A em cascata).

Os demais achados de S-04 são teste, template ou toolchain: ver §3.2 e §3.3.

### 3.2 FALSO-POSITIVO-PROVÁVEL (14)

#### P-01 · CRÍTICO · e-mail sintético em script de seed (3)

`scripts/seed_mvp.py:96`, `scripts/seed_mvp.py:105`, `scripts/seed_test_user.py:83`

Evidência (mascarada): `print("   Email:    te***@***")`

O literal é `test@example.com` — **domínio reservado RFC 2606**, num script de
seed de desenvolvimento que imprime as credenciais que ele mesmo acabou de criar.
Não há titular. O disparo é correto pela regra escrita (P-01 acusa *valor de PII
literal dentro do argumento*), mas o **impacto de privacidade é nulo**.

> **Causa raiz, e é da suíte:** `pse/sanitize.py::RX_EMAIL` casa qualquer
> `algo@dominio.tld` e a lista `ignorar` de `third-party-endpoints.yaml`
> (que já contém `example.com`) **não é consultada por P-01**. Um `example.com`
> ignorado em S-04 e acusado em P-01 é incoerência da régua, não do alvo.
> → candidato a refino, registrado em PENDÊNCIA S-02.

#### P-01 · ALTO · heurística sem AST em script de smoke test (3)

`scripts/smoke-test-console.js:38, 40, 45`

Evidência: `log('Sem sessão — login:',CONFIG.EMAIL);`

Script de console para smoke test manual, com constante de configuração local.
A própria suíte já se protege aqui: sem AST para `.js`, a severidade é **ALTO e
não CRÍTICO**, com a justificativa escrita no módulo. Funcionou como projetado.

#### P-06 · CRÍTICO · segredo de teste, obviamente sintético (5)

| Arquivo:linha | Evidência (mascarada) |
|---|---|
| `tests/unit/security/test_jwt_handler.py:15, 32, 43` | `handler = JWTHandler(secret_key="te***")` |
| `tests/unit/security/test_password_hasher.py:17, 41` | `password = "Se***"` |

Fixtures cujo valor é literalmente `test-secret` / `SecurePassword…`, em testes
unitários de JWT e de hashing. Rotacionar não faz sentido; vazar não expõe nada.

> **Padrão sistêmico:** P-06 e S-06 **não excluem caminhos de teste**. Nos 6 alvos,
> **18 dos 19** CRÍTICOs de credencial estão sob `tests/`. Isso é o cenário exato
> que a doutrina D-08 combate — CRÍTICO em massa por fixture ensina o operador a
> ignorar a categoria inteira, e aí o segredo *real* passa junto.
> → candidato a refino, registrado em PENDÊNCIA S-01.

#### P-09 · ALTO · agregação que não é sobre pessoas (1)

`scripts/database/init-schema.sql:452`

```sql
SELECT DATE(timestamp), provider, SUM(cost_usd), COUNT(*) …
FROM cost_tracking GROUP BY DATE(timestamp), provider
```

Agregação de **custo de API por provedor e dia**. Não há titular na célula, logo
não há reidentificação possível. P-09 é hoje um grep de `GROUP BY` sem
`HAVING COUNT`, sem saber se a entidade agregada é uma pessoa.

#### S-04 · ALTO · toolchain e teste unitário (2)

`.pre-commit-config.yaml:2` (repositório de hooks do pre-commit) e
`tests/unit/test_auto_import_alert.py:35` (host em teste unitário).

Um repositório de hooks não é operador de dado pessoal. S-04 hoje casa qualquer
`https?://host` literal, sem distinguir dependência de build de processador de dado.

### 3.3 INCERTO (9)

| # | Achado | Arquivo:linha | Por que não decido |
|---|---|---|---|
| 1 | **P-01 CRÍTICO** | `src/api/routes/auth.py:122` | Chamada de log **multi-linha**; o AST acusa o nó, mas o snippet de uma linha não mostra o argumento. Precisa de olho humano |
| 2 | **P-04 ALTO** | `tests/qa/catalog.yaml:1` | Só é violação se este repo se declarar **consumidor** da PSE. Hoje o caminho é o *default* da suíte, não uma declaração dele — é "ausência de adoção", não "defeito do alvo". Mas com PAN e e-mail em trânsito, um catálogo **deveria** existir → incerto, não falso-positivo |
| 3 | **P-07 ALTO** | `tests/qa/consent-model.yaml:1` | Idem. E aqui há mérito: reconciliação opera sobre **execução de contrato**, base em que consentimento pode legitimamente não existir |
| 4 | **P-06 CRÍTICO** | `scripts/generate_test_password.py:9` | **Único CRÍTICO de credencial da rodada fora de `tests/`.** Está em `scripts/`, o nome diz "test", mas é utilitário versionado |
| 5 | **P-06 CRÍTICO** | `tests/integration/test_acquirer_clients.py:33` | Sintético pelo nome, mas é **integração com adquirente**: se algum dia apontar para sandbox real, a credencial é real |
| 6–7 | **S-04 ALTO ×2** | `tests/integration/test_cielo_integration.py:44`, `tests/unit/infrastructure/test_cielo_conciliator_client.py:29` | Hosts de sandbox de adquirente em teste. Sandbox de adquirente pode ser ambiente real com contrato — não é o mesmo que um mock |
| 8–9 | **S-04 ALTO ×2** | `.env.example:50`, `.env.example:51` | Template versionado. Os hosts ali são declaração de intenção de integração. Registrar no manifesto é correto; chamar de "uso no código" é forçar |

Somam-se a estes, sem serem achados: o **E-06 indeterminado** (bloqueia) e os
**43 `.tsx` fora de alcance** — se houver PAN, e-mail ou token em `console.log`
no React, a suíte não teria como saber.

## 4. PAN / cartão — o vetor que a régua atual não vê

Este é o achado mais importante do repositório, e a PSE **não o produziu**,
porque não tem entrada de PAN na régua. Levantado por inspeção dirigida:

| Arquivo:linha | Fato | Leitura |
|---|---|---|
| `src/infrastructure/parsers/rede_layouts.py:63` | `"card_number": (60, 79),  # masked` | O comentário **afirma** mascaramento. D-01: comentário não é fato. A afirmação está fora do código que executa |
| `src/infrastructure/parsers/rede_layouts.py:77` | `"card_number": (60, 79),` | **Mesmo campo, mesmo offset, sem o comentário.** Layout `024` vs `012` |
| `src/infrastructure/acquirers/rede_torc_parser.py:265-266` | `card_number = fields[7]` → `card_last_4 = card_number[-4:]` | PAN **completo em variável**; só os 4 últimos entram no dict de saída |
| `src/infrastructure/acquirers/cielo_edi_parser.py:115-116` | idem | idem |
| `src/infrastructure/acquirers/rede_api_parser.py:141-142` | `_card_last_4(card_number)` extrai dígitos | idem |

**Tratamento correto observado (não deve virar achado — D-08):** a saída dos três
parsers expõe apenas `card_last_4` / `cartao_last4`. As fixtures de teste usam
`"card_number": "************1234"` (`tests/unit/infrastructure/test_cielo_edi_parser.py:57`,
`tests/utils/rede_edi_sample.py:82,95`) — mascaramento correto.

**A pergunta que sobra, e que só o dono responde:** o PAN completo existe em
memória entre a leitura do EDI e o descarte. Ele é **persistido** ou **logado** em
algum ponto? A PSE de hoje não sabe responder. → PENDÊNCIA A-01.

Este é o alvo real do check **PAN/PCI** proposto em
[`PROPOSTA-CHECK-PAN-PCI.md`](PROPOSTA-CHECK-PAN-PCI.md).

---

## 5. Resumo da triagem

| Classe | Qtd. | % |
|---|---|---|
| VIOLAÇÃO-PROVÁVEL | 7 | 23% |
| FALSO-POSITIVO-PROVÁVEL | 14 | 47% |
| INCERTO | 9 | 30% |
| **Total** | **30** | |

Conferência: `python scripts/verificar_triagem.py`.

**47% de falso-positivo provável**, concentrado em duas causas sistêmicas da
suíte — credencial em `tests/` (5) e e-mail em domínio reservado (3) — ambas
registradas como pendência de refino, **nenhuma corrigida nesta rodada**.

O dado que mais pesa: dos **16 CRÍTICOs** que produzem o `exit 10`, apenas **5**
sobrevivem à triagem como violação provável. Os outros 11 são fixture, seed
sintético ou chamada que não consegui ler.
