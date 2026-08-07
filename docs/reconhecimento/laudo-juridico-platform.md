# Laudo de reconhecimento — `danzeroum/juridico-platform`

**Setor:** legaltech — LegalScore / Compliance, jurimetria, defensor, ingestão fiscal.
**Commit auditado:** `87f49348da3da594d82b1b8a54ecc179bbc2800f` (clone raso)
**Suíte:** pse-suite `0.3.0` · `catalog_hash 33d5be7e…20e3` · modo `pse_inventory`
**Laudo bruto:** [`laudos/laudo-juridico-platform.json`](laudos/laudo-juridico-platform.json)

> Este é o alvo da **prova de não-falso-positivo** (Etapa 2b), documentada em
> [`PROVA-NAO-FALSO-POSITIVO.md`](PROVA-NAO-FALSO-POSITIVO.md). Nenhum arquivo
> deste repositório foi alterado.

---

## 1. Veredito

| | |
|---|---|
| **veredito** | `indeterminado` |
| **exit_code** | **20** (bloqueia igual a violação) |
| findings | 36 — 0 CRÍTICO, 27 ALTO, 9 MÉDIO |
| duração | 3,63 s |

**Leitura do 20:** não há nenhum CRÍTICO, mas E-06 ficou indeterminado, e
indeterminação **não degrada para verde**. Este alvo é o exemplo mais limpo da
doutrina na rodada: `exit 20` com zero CRÍTICO é a suíte dizendo *"não achei
violação grave, e também não consigo afirmar que está tudo bem"*.

---

## 2. Os três estados

**AUDITADO (13):** `E-00, E-04, E-05, E-07, E-10, P-01, P-03, P-04, P-06, P-07, P-09, S-04, S-06`

**NÃO-APLICÁVEL (4):** P-02, P-08 (catálogo ausente → P-04) · S-05, S-08 (manifesto ausente → S-04)

**FORA-DE-ALCANCE / INDETERMINADO (1):** E-06 — nenhum `fairness_dataset` declarado.

**NÃO-HABILITADO (10):** todo o Trabalho A. **PREVISTO (1):** E-08.

### FORA-DE-ALCANCE por linguagem

| Superfície | Volume | Estado |
|---|---|---|
| `.py` | 270 | **auditado** (AST) |
| `.ts` | 31 | auditado — heurística, severidade rebaixada |
| `.sql` | 5 | auditado (P-02/P-03/P-09) |
| **`.tsx`** | **66** | **FORA-DE-ALCANCE** |

Sem `.java` / `.dart` / `.ex` / `.php`. **66 arquivos de frontend não auditados** —
o maior volume fora de alcance entre os alvos junto com dadosabedoria.

---

## 3. O controle correto que a PSE reconheceu — Etapa 2b

`services/shared/lgpd_crypto.py` implementa **crypto-shredding AES-256-GCM por
titular**, com chave por `tenant:pseudonym`, IV de 96 bits por operação e erasure
por destruição de chave.

**A PSE produziu ZERO findings neste arquivo.** P-06, P-03, P-01, S-06 e S-04
olharam e não morderam.

E isso foi **provado como decisão, não como cegueira**: uma cópia isolada do
arquivo, com o mesmo comportamento e o controle quebrado (chave literal no lugar
de `os.urandom`, mais um `deleted_at`), produz `P-06 CRÍTICO` + `P-03 ALTO` na
mesma linha. Método, comandos e saídas em
[`PROVA-NAO-FALSO-POSITIVO.md`](PROVA-NAO-FALSO-POSITIVO.md).

**Nenhum check precisou de refino.** Nenhum caso novo foi adicionado ao
`consumidor_bom`, e a suíte não sofreu bump — a Etapa 2b não encontrou
falso-positivo a corrigir.

---

## 4. Triagem dos achados

### 4.1 VIOLAÇÃO-PROVÁVEL (14)

#### S-04 · ALTO · terceiros no código sem manifesto (13)

Não existe `.privacy/third-party-manifest.yml`, e o código chama uma quantidade
grande de APIs externas de dado público e fiscal:

| Arquivo:linha | Terceiro |
|---|---|
| `services/ingest/tasks/bcb.py:4` | Banco Central |
| `services/ingest/tasks/caged.py:28` | CAGED |
| `services/ingest/tasks/siconfi.py:5` | SICONFI |
| `services/ingest/tasks/pncp.py:5` | PNCP |
| `services/ingest/tasks/ibge.py:37` | IBGE |
| `services/ingest/tasks/receita_cnpj.py:4` | Receita Federal (CNPJ) |
| `services/ingest/tasks/sefaz_scraper.py:27, 28, 29` | SEFAZ |
| `services/ingest/tasks/confaz_discovery.py:26` | CONFAZ |
| `services/gateway/routers/compliance.py:48` | host externo no gateway |
| `services/defensor/protocolo/real.py:99, 108` | protocolo real |

**Por que violação:** a obrigação do Art. 39 é de **registro**, e o registro não
existe. Que o terceiro seja um órgão público não dispensa declarar residência,
base de transferência e o que sai para ele — que é exatamente o vão que S-05
cobriria, e que ficou N/A por falta do manifesto.

#### S-04 · ALTO · **o LLM externo** (1) — o achado mais relevante

`services/shared/config.py:102`

```python
return os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
```

`api.openai.com` está na régua do pacote, categoria `llm`
(`third-party-endpoints.yaml`). O **default** do sistema é enviar prompt para um
LLM externo, e não há manifesto, DPA, residência de dados nem base de
transferência internacional declarada.

> Note o que a suíte **conseguiu** e o que **não conseguiu**: pegou o *host*
> (S-04), porque ele é literal no default. Não tem como dizer **o que vai dentro
> do prompt** — S-05 responderia isso, mas ficou N/A por falta de manifesto. Esse
> vão é a razão de existir a proposta de sigilo-em-LLM (§5).

### 4.2 FALSO-POSITIVO-PROVÁVEL (7)

| Achado | Arquivo:linha | Por quê |
|---|---|---|
| E-10 MÉDIO ×4 | `docs/test_score_engine_contract.py:52`, `services/scoring/tests/contract/test_score_engine_contract.py:52`, `tests/unit/test_feature_assembler.py:142`, `tests/unit/test_score_factory.py:51` | São **testes** do motor de score, não código de decisão. Cobrar "incerteza quantificada" de um teste de contrato não faz sentido |
| E-10 MÉDIO ×2 | `docs/engines.py:111`, `services/scoring/engine/engines.py:110` — `def healthy(...)` | Função de **healthcheck**. Cai no check porque contém uma chamada que casa `^score$`. Nada a ver com inferência sobre pessoa |
| S-04 ALTO | `docs/design_handoff_.../prototype/support.js:1012` | Protótipo de design em `docs/`, bundle de UI. Não é caminho de execução |

E-10 é MÉDIO por decisão de projeto e **não bloqueia** — o ruído aqui é barato,
mas **6 dos 9** achados de E-10 são falso-positivo, o que mostra que o casamento
`^score$` está largo demais (pega healthcheck e teste de contrato).

### 4.3 INCERTO (15)

| # | Achado | Por que não decido |
|---|---|---|
| 1 | **E-07 ALTO** — `services/audit/anomaly/detector.py:19` (`from sklearn`) sem Model Card | Há ML de verdade. Mas é **detecção de anomalia em trilha de auditoria** — o Model Card do Art. 20 endereça decisão sobre pessoas. Se o detector sinaliza *contribuintes*, é obrigatório; se sinaliza *lançamentos*, é discutível |
| 2–4 | **P-09 ALTO ×3** — `services/early_warning/queries.py:30`, `services/forecasting/queries.py:30`, `services/jurimetria/queries.py:133` | `GROUP BY classe_tpu, assunto_tpu` sobre `jurimetria.indicador`: agregado de estatística processual, com `LIMIT 100`. Uma célula pequena em recorte fino (tribunal + classe + assunto raro) **pode** individualizar um processo — e processo tem parte. Não decido daqui |
| 5 | **P-04 ALTO** — catálogo ausente | Caminho *default* da suíte, não declaração do alvo. Ver PENDÊNCIA D-02 |
| 6 | **P-07 ALTO** — modelo de consentimento ausente | Idem; e legaltech opera muito sobre execução de contrato / obrigação legal |
| 7–9 | **E-10 MÉDIO ×3** — `docs/factory.py:41`, `services/scoring/engine/factory.py:41` (`def score(...)`), `services/audit/anomaly/detector.py:53` (`def detect(...)`) | Estes são os **reais**: motor de score e detector rodando sem medida de confiança. Incerto porque não sei se a incerteza é calculada uma camada acima |
| 10–12 | **S-04 ALTO ×3** — `.env.example:51, 61, 66` | Template de ambiente versionado. Declara intenção de integração; registrar no manifesto é correto, chamar de "uso no código" é forçar |
| 13 | **S-04 ALTO** — `services/shared/config.py:25` | Host em configuração, irmão da linha 102 (que classifiquei como violação). Diferença: a 102 tem default de LLM externo explícito; esta não consegui atribuir a um terceiro concreto |
| 14 | **S-04 ALTO** — `tests/unit/test_config.py:87` | Teste unitário da própria configuração |
| 15 | **S-04 ALTO** — `.github/workflows/ci.yml:343` | Host de toolchain de CI — classifiquei o gêmeo do Central como falso-positivo, mas aqui a linha está num workflow que também publica artefato, e não confirmei o destino |

Soma-se a estes, **sem ser achado**, o **E-06 indeterminado**: há score de
compliance (`services/scoring/`) e `sklearn`, mas sem `fairness_dataset`
declarado a suíte não mede — e **bloqueia**, corretamente. É ele que produz o
`exit 20` deste alvo.

---

## 5. Dado de processo indo a LLM — o vetor do segundo check proposto

Levantado por inspeção dirigida; a PSE de hoje **não produz este achado**.

**Caminho completo, ancorado no fato:**

`services/defensor/orchestrator.py:78-84` monta o prompt:

```python
prompt = (
    f'Redija a seção "{sec.titulo}" da defesa, no canal {request.canal.value}, '
    f"para um caso do tipo {request.tipo_caso.value}.\n"
    f"Reclamante: {request.reclamante}. Reclamada: {request.reclamada}.\n"
    f"Fatos relatados: {request.descricao}\n"
    …
)
texto = generate_text(prompt, system=_LLM_SYSTEM, max_tokens=400)
```

→ `services/shared/ai/generate.py:25` `generate_text()` — **nenhuma redação,
nenhum mascaramento, nenhum guardrail** em todo o módulo.
→ `generate.py:56` `_openai()` → `POST {LLM_BASE_URL}/chat/completions`
→ `services/shared/config.py:102` → default **`https://api.openai.com/v1`**.

**O que sai:** nome do reclamante, nome da reclamada e a **narrativa dos fatos**
de uma defesa jurídica — isto é, o núcleo do que pode estar sob sigilo.

**Onde a suíte para hoje:** S-04 viu o *host*. Nada olha o *conteúdo do prompt*.
E `pii-patterns.yaml` não tem uma linha sequer sobre segredo de justiça, sigilo
profissional da advocacia ou processo em segredo.

**Bifurcação que impede veredito automático (e deve virar `CheckIndeterminado`,
não achado):** `generate.py:31` escolhe o provedor em **runtime**
(`settings.LLM_PROVIDER`). Se for `ollama`, o destino é
`http://ollama:11434` — local, sem egresso. Estaticamente não dá para saber qual
está em produção. → PENDÊNCIA A-02.

Especificação completa em [`PROPOSTA-CHECK-SIGILO-LLM.md`](PROPOSTA-CHECK-SIGILO-LLM.md).

---

## 6. Resumo da triagem

| Classe | Qtd. | % |
|---|---|---|
| VIOLAÇÃO-PROVÁVEL | 14 | 39% |
| FALSO-POSITIVO-PROVÁVEL | 7 | 19% |
| INCERTO | 15 | 42% |
| **Total** | **36** | |

Conferência: `python scripts/verificar_triagem.py`.

Alta fração de incerto (42%) — e isso é honesto, não preguiça: 3 dos P-09 exigem
saber se a célula agregada individualiza processo, e 3 dos E-10 exigem saber se a
incerteza é medida em outra camada. Nenhuma dessas perguntas se responde do lado
de fora do repositório.
