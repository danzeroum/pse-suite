# ONBOARDING-NOTES — o que a PSE Suite é, e como operá-la

> Nota de dev novo no projeto, escrita **antes** de rodar qualquer laudo (Etapa 0).
> Fonte: `README.md`, `docs/COMO-ADOTAR.md`, `pse/data/checks-catalog.yaml`,
> `pse/model.py`, `pse/cli.py`, `pse/engine/`, `pse/checks/**`, `tests/`.
> Estado verificado: `pse --manifesto` nesta branch, em clone limpo.

---

## 0. Divergência entre o enunciado da tarefa e o repositório real

O pedido descreve a suíte como **"58 checks, ~713 testes, 5 domínios × 3 pilares ×
4 modos"**, com `RATIFICACOES.md`, `docs/matriz-dominio.md`, `docs/cobertura-btv.md`
e uma doc de testes gerada; e cita `P-18/P-19/P-20` e `E-11`.

**Nada disso existe neste repositório.** O que existe, medido:

| Enunciado | Repositório real (`8cd937d`, v0.3.0) |
|---|---|
| 58 checks | **30 no catálogo** — 29 implementados + E-08 `previsto-fase-3` |
| ~713 testes | **144 testes**, todos verdes |
| 5 domínios × 3 pilares × 4 modos | **3 pilares** (privacy/security/ethics) × **3 modos** (`pse_inventory`, `pse_passive`, `pse_active`). Não há eixo "domínio" |
| `RATIFICACOES.md`, `docs/matriz-dominio.md`, `docs/cobertura-btv.md` | ausentes (só existe `docs/COMO-ADOTAR.md`) |
| doc de teste gerada + trava de CI | ausente |
| `P-18`, `P-19`, `P-20` | inexistentes — privacidade vai de **P-01 a P-11** |
| `E-11` (PII em prompt) | inexistente — ética vai de **E-00 a E-10** |

`git log` confirma: a branch `claude/pse-suite-architecture-validation-5lm0p3`
citada no enunciado **já foi mergeada** (PR #1, commit `8cd937d`) e é exatamente
esta v0.3.0 de 29 checks. Não há branch com 58 checks em lugar nenhum do remoto.

**Como prossegui** (premissa declarada, não presumida): auditei a suíte que
existe. Onde o enunciado nomeia um check inexistente, mapeei para o análogo real
e disse qual — nunca inventei o check ausente:

| Enunciado | Análogo real usado | Por quê |
|---|---|---|
| P-06/P-18/P-19/P-20 na Etapa 2b | **P-06** (chave em claro) + **P-03** (soft-delete sem eliminação) + **S-06** (credencial hardcoded) | são os únicos checks desta versão que poderiam morder `lgpd_crypto.py`. P-03 é o mais relevante: sua própria recomendação pede "crypto-shredding" |
| E-11 (PII em prompt) | **S-04** (host de terceiro) + **S-05** (payload de egresso) | é onde a suíte hoje toca egresso a LLM — e o vão entre os dois é justamente o que a Etapa 3 especifica |

O resto desta nota descreve a suíte real.

---

## 1. O que a PSE é

Um **padrão externo e versionado** (`pip install pse-suite`) que audita um
repositório-alvo em três pilares: **P**rivacidade, **S**egurança e **É**tica por
design. Não é uma lib do projeto auditado: é o fiscal, e mora fora.

A regra que organiza tudo o mais:

> **A régua mora no pacote, nunca no consumidor.**
> `pse/data/*.yaml` (padrões de PII, campos sensíveis, proxies de discriminação,
> hosts de terceiros) evolui por versão *deste* pacote. Se cada consumidor tivesse
> cópia editável, apagar uma linha faria o laudo dizer "nenhum achado" — sem erro,
> sem aviso, indistinguível de um projeto seguro.
> *Uma trava que o vigiado desliga em silêncio não é trava.*

O consumidor **declara** (config, catálogo de dados, manifesto de terceiros,
atestação); o pacote **fornece** o motor, a régua e o veredito.

---

## 2. Como rodar

```bash
pip install -e ".[dev]"          # dev; no consumidor: pin em requirements-qa.txt

pse --path .                     # Trabalho B (inventário estático), laudo no stdout
pse --path . --output laudo.json # laudo em arquivo
pse --path . --packs privacy     # um pilar por vez (privacy|security|ethics)
pse --path . --config tests/qa/pse-config.yaml
pse --path . --modo pse_passive  # Trabalho A somente-leitura
pse --path . --modo pse_active   # Trabalho A com sonda de autorização

pse --self-test                  # a trava desta versão instalada ainda morde?
pse --manifesto                  # versão, catalog_hash, checks, autoprova
```

`--path` é obrigatório (salvo `--self-test`/`--manifesto`). Path inexistente ou
que não é diretório → **exit 30**. Auditar o que não existe jamais é "conforme".

**Não existe flag que rebaixe o gate.** A política ("ALTO bloqueia em `main`,
avisa em feature branch") vive no CI do consumidor, declarativa e protegida por
CODEOWNERS — onde o dono da decisão é visível.

---

## 3. Os cinco códigos de saída

| Código | Significado | Bloqueia? |
|---|---|---|
| `0` | **conforme** — rodou e não achou nada | não |
| `10` | **violação com CRÍTICO** | sim, sempre (fail-closed) |
| `11` | **violação com ALTO**, sem CRÍTICO | política do CI do consumidor |
| `20` | **indeterminado** — tentou e não conseguiu decidir | **sim, igual ao 10** |
| `30` | **entrada inválida** — path/config/catálogo/versão irresolvíveis | sim |

Precedência quando coexistem: **`30 > 10 > 20 > 11 > 0`**
(`pse/evidence.py::veredito`; o 30 nasce antes do laudo, em `cli.py`).

O ponto inteiro dos cinco estados: **"não olhei" nunca compartilha código de saída
com "conforme"**. Um `20` é uma resposta honesta — e bloqueia igual, porque dúvida
não degrada para verde.

Dois casos que viram **30 e não achado**, de propósito:
- threshold fora da faixa da suíte (`k_anonymity_min` piso 5, `dpd_max_delta` teto
  0,10 — `pse/limites.py`). O consumidor **aperta, nunca afrouxa**;
- todos os packs desabilitados em `pse-config.yaml` — laudo vazio não é laudo conforme.

> Achado, o operador aprende a ignorar. Recusa de execução, não.

---

## 4. Os três estados que nunca se colapsam

Este é o coração da suíte. Colapsar qualquer par produz **verde falso** — o pior
defeito possível. Em `pse/model.py` cada estado é uma exceção distinta, e o
`runner` os separa em listas distintas do laudo.

| Estado | Exceção | Significado | Vai para | Bloqueia? |
|---|---|---|---|---|
| **AUDITADO** | — (retorno normal) | olhei e decidi: resultado X (com ou sem achado) | `checks_executados` + `findings` | só se houver achado |
| **NÃO-APLICÁVEL** | `SkipCheck` | a pré-condição **declarativa** não existe — o check não faz sentido aqui (sem manifesto de terceiros não há o que conferir em S-08) | `checks_pulados` | **não** — mas o motivo é obrigatório |
| **FORA-DE-ALCANCE** | `CheckIndeterminado` | **tentei e não decidi**: fato não decidível estaticamente, arquivo ilegível, linguagem sem parser, alvo caído, atestação inválida | `checks_indeterminados` | **sim** (exit 20) |

Mais dois destinos, que existem para que ausência nunca seja silêncio:

| Estado | Exceção | Significado | Vai para | Bloqueia? |
|---|---|---|---|---|
| **NÃO-HABILITADO** | `NaoHabilitado` | o check existe e o consumidor não o pediu nesta execução (não pediu Trabalho A, ou pediu num modo que não o inclui) | `checks_nao_habilitados` | não |
| **PREVISTO** | — (catálogo) | declarado no catálogo e ainda **não implementado** nesta versão (hoje: E-08) | `checks_previstos` | não |

**A diferença que mais importa na prática:**

- `SkipCheck` = *"a pergunta não se aplica a este alvo"* → não bloqueia.
- `CheckIndeterminado` = *"a pergunta se aplica e eu não consegui responder"* → bloqueia.

Trocar um pelo outro é o bug clássico: um `.py` com `SyntaxError` que virasse
`SkipCheck` sairia verde. Por isso `scan.arvore()` levanta `CheckIndeterminado`
em `SyntaxError` — sem AST não há como decidir pelo fato.

E há a **guarda de pack** (E-00): um check pode declarar `guarda_de_pack: true`.
Se a guarda pula, o pacote inteiro sai de escopo — com o motivo computado
propagado para cada check (`packs_fora_de_escopo`), nunca em verde silencioso.

---

## 5. As duas leis de ancoragem

### D-01 — âncora no FATO, nunca na menção

Um check não pode concluir nada a partir de uma string que aparece em comentário
ou dentro de um literal: ali o vigiado escreve o que quiser, e a trava vira
decoração. Daí `scan.codigo_efetivo()` (apaga comentários — e literais quando
`sem_literais=True`) e `scan.arvore()` (AST, o fato verdadeiro).

- `# TODO: implementar revisao_humana algum dia` **não** desliga o CRÍTICO de E-04.
- `# nota: avaliar equalized_odds no futuro` **não** desliga E-05.
- Comentário citando `purge` **não** satisfaz P-02 — só uma função cujo corpo
  executa uma eliminação de verdade.

Cuidado inverso, e explícito no código: `sem_literais=True` serve para lógica de
**supressão**, nunca de **detecção de segredo/PII** — ali o literal *é* o fato
(`api_key = "sk-live-..."` é uma credencial, não a menção de uma).

A fixture `consumidor_silencioso` existe só para provar isto: violação real +
comentário citando o controle **não** fica verde.

### D-08 — não punir o caso correto

Código que faz a coisa certa **não dispara**. `logger.info("cpf=%s", mascarar(cpf))`
é conforme; um campo cifrado é conforme; chave vinda de env/vault é conforme.

> Falso-positivo em CRÍTICO ensina o operador a ignorar o laudo — é tão grave
> quanto falso-negativo.

A fixture `consumidor_bom` existe só para isto: se algum check acusar aquele
diretório, ele tem falso-positivo.

**Corolário operacional (precisão sobre recall):** onde não há AST, o grep é
frágil. Na dúvida → `CheckIndeterminado`, nunca achado forçado nem verde forçado.
P-01 faz isso literalmente: **CRÍTICO** via AST em Python, **ALTO** via heurística
nas outras linguagens, com a justificativa escrita no próprio módulo.

### E a lei de postura

**A PSE afirma, o DONO valida.** Um achado é hipótese ancorada, não veredito.
Achado em repo-alvo é devolvido ao dono — **nunca corrigido pela PSE**, que não é
dona daquele repositório.

---

## 6. Sanitização — a régua obedece ao que receita

`pse/sanitize.py` (D-02): a evidência **não republica** o que denuncia. O
localizador de um achado é `arquivo:linha`, **nunca o literal**. Mascaramento por
borda (2 caracteres + `***`), idempotente, aplicado em **dois** pontos:

1. `Finding.__post_init__` — na origem, para o segredo não viver em claro nem em
   memória (um gravador de trace do Trabalho A o receberia cru);
2. `evidence.montar_laudo` — o choke point da serialização.

P-10 é o caso extremo: o pacote de portabilidade **é** o conjunto dos dados do
titular, então o trace **omite a resposta inteira** e guarda só status, tamanho e
a lista de *chaves*. Mascarar não serviria — o problema não é um campo, é o volume.

---

## 7. Os 30 checks: id, pilar, o que ancora

Legenda de modo: `inv` = inventory (Trabalho B, sem rede) · `pas` = passive
(Trabalho A leitura) · `act` = active (Trabalho A, sonda de autorização).

### Pacote P — Privacidade (11)

| ID | Sev. | Modo | O que ANCORA (o fato, não a menção) |
|---|---|---|---|
| **P-01** PII em log | CRÍTICO | inv | AST: o que a *chamada de log recebe como argumento*. Duas violações: valor de PII literal na string, ou variável cujo nome está na régua passada crua. `mascarar(cpf)` suprime. Fora do Python, heurística de linha rebaixada a ALTO |
| **P-02** retenção sem purga | ALTO | inv | Catálogo declara `retention_years` **e** não existe função cujo corpo *execute* uma eliminação (chamada `delete/drop/purge/...` ou SQL `DELETE FROM`). Um gap **por tabela**. Sem catálogo → `SkipCheck` |
| **P-03** soft-delete | ALTO | inv | grep de `deleted_at` / `is_deleted` / `status == 'deleted'` em `.py`/`.sql`. Um achado por arquivo. Recomenda eliminação física ou **crypto-shredding** |
| **P-04** catálogo vivo | ALTO/MÉDIO | inv | Catálogo existe; cada campo tem `class, owner, purpose, legal_basis, retention_years`; campo da lista curada de sensíveis está classificado `sensitive`; e o todo valida contra `catalog-1.0.json`. Emite também o relatório de **cobertura** |
| **P-05** minimização | ALTO | act | POST com campo fora da allowlist: se o alvo **aceita** (2xx), a borda não minimiza. Escreve de verdade → exige `synthetic_identities` |
| **P-06** chave segregada | **CRÍTICO** | inv | Literal de `hmac_key/secret_key/private_key/senha/password = "…"` (≥8 chars) no fonte. Chave vinda de env/vault/`os.urandom` não casa |
| **P-07** consentimento | CRÍTICO | act | Estático: modelo valida contra `consent-model-1.0.json` (que recusa por construção pré-marcado e irrevogável). Runtime: rota protegida responde 2xx sem consentimento |
| **P-08** sensível + LI | **CRÍTICO** | inv | Campo `class: sensitive` com `legal_basis: legitimo_interesse`. Trava estrutural do Art. 11, sem exceção. Sem catálogo → `SkipCheck` |
| **P-09** k-anonimato | ALTO | act | Estático: `GROUP BY` sem `HAVING COUNT(...)`. Runtime: célula de contagem `0 < v < k` na resposta. `k` da suíte, piso 5 |
| **P-10** portabilidade | ALTO | act | Exportação responde, é objeto estruturado, e traz prova de integridade + estrutura declarada. Trace **sem corpo** |
| **P-11** oráculo | **CRÍTICO** | act | Recurso alheio (declarado) e recurso inexistente respondem **status diferentes** → dá para enumerar titulares sem ler um dado |

### Pacote S — Segurança (8)

| ID | Sev. | Modo | O que ANCORA |
|---|---|---|---|
| **S-01** BOLA/IDOR | **CRÍTICO** | act | Token do titular A obtém 200/206 em recurso **declarado** do titular B. A suíte não enumera recurso alheio — isso seria executar a violação |
| **S-02** rate limit | ALTO | act | 25 requisições consecutivas sem 429/503. O teto é da suíte, não do consumidor |
| **S-03** erro com PII | ALTO | pas | Payload de erro casa CPF/e-mail/telefone, ou traz nome de campo da régua |
| **S-04** terceiro sem DPA | CRÍTICO/ALTO | inv | Host literal `https?://…` no código sem entrada no manifesto (ALTO); integração declarada `required` sem `dpa_signed` (CRÍTICO) |
| **S-05** egresso mínimo | ALTO | inv | Integração sem `egress_fields` declarados; ou com identificador direto/sensível saindo. *DPA autoriza o tratamento, não dispensa a minimização.* Sem manifesto → `SkipCheck` |
| **S-06** credencial hardcoded | **CRÍTICO** | inv | Literal `api_key/apikey/access_token = "…"` (≥12) ou `Authorization: Bearer …` (≥16) |
| **S-07** finalidade + log | ALTO | act | Requisição sem `X-Purpose` é atendida; e o log de auditoria não registra quem/o quê/quando/sobre o quê/**para quê** |
| **S-08** transferência intl. | ALTO | inv | `data_residency` fora do BR sem `transfer_basis`. Sem manifesto → `SkipCheck` |

### Pacote E — Ética (11, sendo 1 previsto)

| ID | Sev. | Modo | O que ANCORA |
|---|---|---|---|
| **E-00** escopo (**guarda**) | ALTO | inv | *Computa* indícios de decisão automatizada (import de ML, função `score/decidir/negar_…`, chamada `predict/fit/…`) e confronta com `decision_making`. Código diz "há" + consumidor diz `none` → **achado de divergência**. Nada declarado e nenhum indício → pack inteiro N/A |
| **E-01** explicação | ALTO | pas | Resposta da decisão não traz `motivo/fatores/reason_code/...` em nenhuma profundidade |
| **E-02** decision log | ALTO | pas | Decisão não registra modelo, features, score, limiar e revisor |
| **E-03** contestação | ALTO | act | Contestação aceita sem protocolo rastreável ou sem prazo/SLA |
| **E-04** HITL | **CRÍTICO** | inv | AST: função de decisão de alto impacto (`negar_credito`, `bloquear_conta`, …) sem **chamada** que encaminhe a revisão humana (aceita 1 nível de indireção). Comentário não roteia ninguém |
| **E-05** proxy de discriminação | ALTO | inv | Variável proibida (`cep`, `bairro`, `genero`, `raca`, …) perto de `score/features/model` **sem chamada** de ajuste (`equalized_odds`, `re_weighting`, …) que execute |
| **E-06** disparidade | ALTO | inv | Exige que a medição **exista**, valide contra `fairness-report-1.0`, esteja **fresca** (fingerprint do dataset) e o DPD esteja no teto. **Nunca roda inferência** — não processa dado de titular real para produzir número que o consumidor já tem |
| **E-07** Model Card | ALTO | inv | Import de ML sem nenhum arquivo `model-card`. O finding aponta o **import** que cria a obrigação |
| **E-08** lineage | — | inv | **`previsto-fase-3`** — declarado no catálogo, não implementado. Sai em `checks_previstos`: previsto e ausente nunca é silêncio |
| **E-09** kill switch | ALTO | act | Só pede **dry-run**; `DRY_RUN` é constante, sem ramo que a omita e **sem retentativa sem dry-run**. Alvo que não simula → indeterminado (mais barato que descobrir o switch funcionando porque a auditoria o puxou) |
| **E-10** incerteza | MÉDIO | inv | Função que chama inferência e não calcula nenhuma medida de confiança. MÉDIO por decisão: é boa prática ausente, não violação legal — **não pode bloquear** |

**Conjunto CRÍTICO ratificado (fail-closed):**
`P-01, P-06, P-08, P-11, S-01, S-04(dpa), S-06, E-04`.

---

## 8. Um check de cada pilar, por extenso

**P-01 (privacidade) — PII em log.** Pergunta errada: *"a palavra `cpf` aparece
nesta linha?"*. Pergunta certa: *"o que esta chamada de log **recebe como
argumento**?"*. A regex de linha única da v0.1 errava nos dois sentidos, medido:
punia `logger.info("cpf=%s", mascarar(cpf))` com CRÍTICO (falso-positivo no
mascaramento correto) e perdia a mesma chamada quebrada em três linhas
(falso-negativo). Hoje: AST, julga os *argumentos*. Uma string de formato que só
*cita* `cpf=%s` não é violação — o valor vem dos argumentos, e são eles os julgados.

**S-01 (segurança) — BOLA/IDOR.** Envia o token do titular A contra um recurso
**declarado** do titular B e exige que não venha 200. Ser somente-leitura **não**
a torna passiva: é sonda de autorização deliberada, então é `pse_active`, com
escopo atestado, em staging, com identidades sintéticas. E a suíte **não descobre**
o recurso de B — enumerar recurso alheio seria executar exatamente a violação que
o check existe para impedir. Se o alvo devolve 401/403, isso é **P-11**, não S-01:
cada check responde por uma coisa só.

**E-04 (ética) — rota humana.** Uma função que decide sobre direitos (crédito,
conta, benefício) e não chama nenhuma rota de revisão humana é CRÍTICO. O que
suprime é uma **chamada que executa** — inclusive via um nível de indireção (uma
função local que encaminha). O que **não** suprime é
`# TODO: implementar revisao_humana algum dia`: na v0.1 isso desligava o CRÍTICO,
e é a lição D-01 em uma linha.

---

## 9. Autoprova: a régua prova que ainda morde

```bash
pse --self-test
```

Audita uma fixture **embarcada no wheel** e exige vermelho, e roda a **mutação
canônica** de cada check — a violação mínima que deve reprová-lo, declarada como
*dado* no catálogo (`canonical_mutation`). Check implementado sem mutação
declarada **reprova a si mesmo**:

> Um check que nunca foi visto reprovando nada é uma hipótese, não uma trava.

O consumidor roda isso no próprio CI, sem clonar este repositório.

**Estado medido nesta branch, em clone limpo:**

```
suite_version   0.3.0
catalog_hash    33d5be7e85777045d0088c3f5f7a91e394c83c4be33cfeda519b6073be0420e3
implementados   29     previstos  ["E-08"]
autoprova       ok=true — 29 mutações canônicas reprovam
pytest          144 passed
```

O `catalog_hash` cobre `pse/data/` **e** o código dos checks: dois laudos com a
mesma `suite_version` e hashes diferentes foram produzidos por réguas diferentes,
e isso fica visível sem depender da palavra de ninguém.

---

## 10. Alcance real da varredura estática (o que a suíte enxerga)

Levantado do código, porque determina o que pode ser declarado FORA-DE-ALCANCE:

| Extensão | Quem olha | Profundidade |
|---|---|---|
| `.py` | todos os checks estáticos | **AST** (o fato) |
| `.js`, `.ts`, `.go`, `.java` | P-01, P-06, S-04, S-06, E-04 | heurística de linha, severidade rebaixada |
| `.sql` | P-02, P-03, P-09 | texto efetivo |
| `.sh` | P-02 | texto efetivo |
| `.yaml`, `.yml` | S-04, S-06 | texto |
| `.env` (+ `.env.*`) | P-06, S-04, S-06 | texto — `_casa()` trata o sufixo vazio (D-03) |
| `.md`, `.json` | E-07 | só nome de arquivo |
| **`.tsx`, `.jsx`** | **ninguém** | **fora de alcance** |
| `.dart`, `.ex`, `.php`, `.rb`, `.cs`, `.kt` | **ninguém** | **fora de alcance** |

`.tsx`/`.jsx` não estarem em nenhum conjunto de extensões é a limitação de alcance
mais relevante para os alvos desta rodada — e por isso está **declarada** em cada
laudo, nunca silenciada.

Diretórios sempre ignorados: `.git`, `node_modules`, `.venv`, `venv`,
`__pycache__`, `dist`, `build`, `.mypy_cache`, `.pytest_cache`. Arquivo > 2 MB é pulado.

---

## 11. Trabalho A: nenhum byte antes da atestação

Ordem obrigatória: **modo habilitado → atestação válida para este modo e este
alvo → tokens no ambiente → healthcheck**. Atestação ausente, vencida, com escopo
errado ou com `target_fingerprint` de outro alvo deixa todos os checks A em
`checks_indeterminados` (exit 20) — nunca verde, nunca uma requisição.

`pse_active` contra `environment: production` é **recusado (exit 30)** antes até
do healthcheck. O healthcheck roda uma vez por execução e o veredito vale para
todos: alvo caído não merece uma sonda sequer.

---

## 12. Checklist do operador novo

1. `pip install -e ".[dev]"` → `pytest` (144 verdes) → `pse --self-test`.
2. `pse --path <alvo>` e leia **primeiro** `veredito` e `exit_code`.
3. Depois leia, nesta ordem, e **não confunda**:
   `checks_indeterminados` (bloqueia — não consegui decidir) →
   `checks_pulados` (N/A, com motivo) →
   `checks_nao_habilitados` (não pedido) →
   `checks_previstos` (não implementado) →
   `findings`.
4. Antes de reportar um achado, pergunte: **qual é o fato?** Se a resposta for
   "aparece a palavra X", não é achado — é menção.
5. Antes de reportar um verde, pergunte: **o check olhou mesmo?** Se a linguagem
   está fora do alcance da §10, o estado é **fora-de-alcance**, não "sem achado".
6. O achado é do dono. A PSE afirma; quem valida é ele.
