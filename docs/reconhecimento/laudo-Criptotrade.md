# Laudo de reconhecimento — `danzeroum/Criptotrade`

**Setor:** fintech — plataforma de trading automatizado de cripto com agentes de IA.
**Commit auditado:** `1cb24a4319e05a494216c6ad52c2c543691129f0` (clone raso)
**Suíte:** pse-suite `0.3.0` · `catalog_hash 33d5be7e…20e3` · modo `pse_inventory`
**Laudo bruto:** [`laudos/laudo-Criptotrade.json`](laudos/laudo-Criptotrade.json)

> A PSE afirma; o dono valida. Nenhum arquivo deste repositório foi alterado.

---

## 1. Veredito

| | |
|---|---|
| **veredito** | `violacao` |
| **exit_code** | **10** (violação com CRÍTICO — fail-closed) |
| findings | 25 — **14 CRÍTICO**, 11 ALTO |
| duração | 4,91 s |

---

## 2. Os três estados

**AUDITADO (13):** `E-00, E-04, E-05, E-07, E-10, P-01, P-03, P-04, P-06, P-07, P-09, S-04, S-06`

**NÃO-APLICÁVEL (4):** P-02, P-08 (catálogo ausente → P-04) · S-05, S-08 (manifesto ausente → S-04)

**FORA-DE-ALCANCE / INDETERMINADO (1):** E-06 — nenhum `fairness_dataset` declarado.
Relevante aqui: o repositório se descreve como plataforma de **agentes de IA** e a
guarda E-00 confirmou indícios de decisão automatizada, então o pack de ética
está **em escopo** — e mesmo assim a fairness não é mensurável. Bloqueia, e deve.

**NÃO-HABILITADO (10):** todo o Trabalho A. **PREVISTO (1):** E-08.

### FORA-DE-ALCANCE por linguagem

| Superfície | Volume | Estado |
|---|---|---|
| `.py` | 219 | **auditado** (AST) |
| `.js` / `.ts` | 21 / 1 | auditado — heurística, severidade rebaixada |
| `.sql` | 13 | auditado (P-02/P-03/P-09) |
| **`.jsx`** | **26** | **FORA-DE-ALCANCE** |

Sem `.java` / `.dart` / `.ex` / `.php`. **26 arquivos de frontend não auditados.**

---

## 3. Triagem dos achados

### 3.1 VIOLAÇÃO-PROVÁVEL (4)

#### P-01 · CRÍTICO · e-mail de titular vai cru para o log (2)

| Arquivo:linha | Evidência (mascarada) |
|---|---|
| `src/api/routes/users.py:83` | `logger.warning("Invite e-mail failed for %s", email, exc_info=True)` |
| `src/auth/store.py:447` | `logger.info("Bootstrapped first admin user %s", email)` |

**O fato:** o AST mostra a variável `email` — termo da régua do pacote — entrando
como argumento posicional de `logger.warning`/`logger.info`, sem mascaramento.
Ambos são caminhos de produção (rota de convite de usuário; bootstrap do primeiro
admin), não scripts de desenvolvimento.

`users.py:83` é o mais sensível: além do e-mail, carrega `exc_info=True`, que
anexa o stack trace inteiro ao mesmo registro.

#### S-04 · ALTO · terceiros no código sem manifesto (2)

| Arquivo:linha | Terceiro |
|---|---|
| `src/api/routes/exchanges.py:211` | exchange de cripto (host externo) |
| `src/notifications/senders.py:48` | provedor de notificação |

Não existe `.privacy/third-party-manifest.yml` — o que deixou S-05 e S-08 sem o
que auditar. Numa plataforma de trading, a exchange é o terceiro que recebe
ordem, valor e identidade da conta.

### 3.2 FALSO-POSITIVO-PROVÁVEL (14)

#### P-06 · CRÍTICO · senha de fixture em testes de autenticação (8)

| Arquivo:linha | Evidência (mascarada) |
|---|---|
| `tests/api/test_auth.py:40` | `def _login(client, email="**@***", password="s3***", **kw):` |
| `tests/api/test_auth.py:56, 57, 64, 65, 70, 149` | `_login(client, password="wr***")` etc. |
| `tests/api/test_account.py:87` | `_client_as(password="ne***")` |

Oito CRÍTICOs num único arquivo de teste de login, cujos literais são
`wrong-password`, `s3cret`, `new-password` — os valores canônicos de um teste de
autenticação. **Não há segredo a rotacionar.**

> Este é o caso mais forte da rodada para o refino de P-06/S-06 em caminhos de
> teste: 8 de 8 CRÍTICOs de P-06 neste alvo são fixtures. Se um segredo de
> produção aparecesse no nono, ninguém o veria. → PENDÊNCIA S-01.

#### P-01 · CRÍTICO · CLI administrativo de linha de comando (3)

`scripts/create_admin.py:36, 49, 52`

Evidência: `print(f"Admin user {args.email} created.")`

`args.email` vem de `argparse` — é o e-mail que o **operador acabou de digitar no
próprio terminal**. Imprimir de volta na sessão interativa não é "gravar PII em
log": não há persistência, não há coleta, não há exportação. O check acerta a
regra (`print` + variável da régua, crua) e erra o risco.

> P-01 trata `print` como sink de log. Para um CLI administrativo isso produz
> CRÍTICO sem exposição. Não proponho mudança — distinguir `print` de CLI de
> `print` de servidor exige saber o contexto de execução, que estaticamente não
> se tem. Registro como limitação conhecida.

#### S-04 · ALTO · hosts em teste (2)

`tests/api/test_notifications.py:145`, `tests/unit/test_llm_and_routing.py:59` —
hosts em teste unitário (mock de notificação e de roteamento de LLM).

#### S-06 · CRÍTICO · credencial de fixture já anotada pelo próprio alvo (1)

`tests/api/test_connections.py:20`

Evidência (mascarada): `API_KEY = "ex***"  # gitleaks:allow (test fixture)`

O valor real começa com `ex…`, coerente com `example`, e o repositório **já
reconheceu** o literal como fixture, anotando-o para outra ferramenta.

> **Observação para a suíte, não para o alvo:** a PSE não lê essa anotação — e
> corretamente, porque uma supressão que o vigiado escreve no próprio
> repositório é exatamente "a trava que o vigiado desliga em silêncio". Registro
> sem propor mudança nesse ponto. O refino defensável continua sendo o de
> PENDÊNCIA S-01 (rebaixar severidade em caminho de teste), que é decisão da
> régua, não do auditado.

### 3.3 INCERTO (7)

| # | Achado | Por que não decido |
|---|---|---|
| 1 | **P-09 ALTO** — `src/api/routes/desk.py:76` | `SELECT … FROM ledger_events WHERE event_type='signal_generated' GROUP BY sym` — agrega **sinais de trading por símbolo**. Símbolo não é pessoa. Provavelmente falso-positivo; fica incerto porque `ledger_events` pode carregar identidade de conta que eu não rastreei até o fim |
| 2 | **P-09 ALTO** — `src/api/routes/pairs.py:49` | Idem, agregação por par de negociação |
| 3 | **P-04 ALTO** — catálogo ausente | Caminho *default* da suíte. Ver PENDÊNCIA D-02 |
| 4 | **P-07 ALTO** — modelo de consentimento ausente | Idem |
| 5–7 | **S-04 ALTO ×3** — `.env.example:12`, `.env.example:38`, `.env.template:17` | Templates de ambiente versionados. Declaram intenção de integração (exchange, notificação); registrar no manifesto é correto, chamar de "uso no código" é forçar |

Somam-se a estes, sem serem achados: o **E-06 indeterminado** — plataforma de
agentes de IA com decisão sobre ordens; se algum agente decide sobre **conta de
pessoa** (limite, bloqueio, recusa de saque), fairness é obrigatório
(→ PENDÊNCIA A-03) — e os **26 `.jsx` fora de alcance**.

---

## 4. Notas de contexto

**E-04 (HITL) executou e não achou nada.** O README declara "Human-in-the-Loop"
como princípio. E-04 procura funções com nomes de decisão de alto impacto sobre
**direitos** (`negar_credito`, `bloquear_conta`, `recusar_beneficio`…). Um sistema
de trading decide sobre **ordens**, não sobre direitos de titular — o vocabulário
da régua não alcança este domínio. Isso é **auditado com resultado negativo**, e
não "não se aplica": o check rodou, procurou, e o padrão não estava lá.

**P-03 (soft-delete) executou e não achou nada** — verificado: não há `deleted_at`
nem `is_deleted` em nenhum `.py`/`.sql` do alvo. Ausência real, não supressão.

---

## 5. Resumo da triagem

| Classe | Qtd. | % |
|---|---|---|
| VIOLAÇÃO-PROVÁVEL | 4 | 16% |
| FALSO-POSITIVO-PROVÁVEL | 14 | 56% |
| INCERTO | 7 | 28% |
| **Total** | **25** | |

Conferência: `python scripts/verificar_triagem.py`.

**56% de falso-positivo provável — a pior taxa da rodada**, e 9 dos 14 vêm de um
único arquivo de teste de autenticação (`tests/api/test_auth.py` + `test_account.py`).

O número que mais importa: dos **14 CRÍTICOs** que produzem o `exit 10`, **9 são
fixtures de senha** e **3 são um CLI ecoando no terminal**. Sobram **2** achados
CRÍTICOs de verdade — os dois `logger` com e-mail de titular. O gate está
disparando pelo motivo errado.

É a evidência mais forte da rodada de que o refino de P-06/S-06 em caminho de
teste (PENDÊNCIA S-01) vale mais, para este alvo, que qualquer check novo.
