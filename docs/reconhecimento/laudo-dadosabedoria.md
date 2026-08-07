# Laudo de reconhecimento — `danzeroum/dadosabedoria`

**Setor:** dados / cívico — plataforma de inteligência sobre dados públicos brasileiros.
**Commit auditado:** `f66b977fd56f3bb449fc819eb3c3e78dd65c76a2` (clone raso)
**Suíte:** pse-suite `0.3.0` · `catalog_hash 33d5be7e…20e3` · modo `pse_inventory`
**Laudo bruto:** [`laudos/laudo-dadosabedoria.json`](laudos/laudo-dadosabedoria.json)

> A PSE afirma; o dono valida. Nenhum arquivo deste repositório foi alterado.

---

## 1. Veredito

| | |
|---|---|
| **veredito** | `indeterminado` |
| **exit_code** | **20** (bloqueia igual a violação) |
| findings | 28 — 0 CRÍTICO, 28 ALTO |
| duração | 4,54 s |

**Zero CRÍTICO em 309 arquivos Python.** Entre os 6 alvos, é o único que combina
base grande com nenhuma violação crítica — nenhuma PII crua em log, nenhuma chave
literal, nenhuma credencial hardcoded, nenhuma decisão de alto impacto sem rota
humana. Vale dizer isso explicitamente, porque um laudo só sabe reclamar se
ninguém escrever o que ele calou.

---

## 2. Os três estados

**AUDITADO (13):** `E-00, E-04, E-05, E-07, E-10, P-01, P-03, P-04, P-06, P-07, P-09, S-04, S-06`

**NÃO-APLICÁVEL (4):** P-02, P-08 (catálogo ausente → P-04) · S-05, S-08 (manifesto ausente → S-04)

**FORA-DE-ALCANCE / INDETERMINADO (1):** E-06 — nenhum `fairness_dataset` declarado.
É este check, sozinho, que faz o alvo sair em **20** em vez de **11**.

**NÃO-HABILITADO (10):** todo o Trabalho A. **PREVISTO (1):** E-08.

### FORA-DE-ALCANCE por linguagem

| Superfície | Volume | Estado |
|---|---|---|
| `.py` | 309 | **auditado** (AST) |
| `.ts` | 29 | auditado — heurística, severidade rebaixada |
| `.js` / `.mjs` | 4 | auditado — heurística |
| **`.tsx`** | **81** | **FORA-DE-ALCANCE** |
| **`.jsx`** | **7** | **FORA-DE-ALCANCE** |

Sem `.java` / `.dart` / `.ex` / `.php`. Sem `.sql` — P-02/P-03/P-09 tiveram só os `.py`.

**88 arquivos de frontend fora de alcance — o maior volume da rodada.** A
aplicação `web/` (Next.js) é uma superfície inteira sobre a qual este laudo não
tem absolutamente nada a dizer, nem bom nem ruim.

---

## 3. Triagem dos achados

Os 28 achados se distribuem em apenas 3 checks: S-04 (26), P-04 (1), P-07 (1).

### 3.1 VIOLAÇÃO-PROVÁVEL (17)

#### S-04 · ALTO · APIs de dado público sem manifesto (11)

Não existe `.privacy/third-party-manifest.yml`. Os adaptadores de ingestão chamam:

| Arquivo:linha | Fonte |
|---|---|
| `api/app/ingestao/adaptadores/ibge.py:76` | IBGE |
| `api/app/ingestao/adaptadores/sisvan.py:151` | SISVAN (nutrição/saúde) |
| `api/app/ingestao/adaptadores/siconfi.py:208` | SICONFI |
| `api/app/ingestao/adaptadores/saneamento.py:100` | SNIS / saneamento |
| `api/app/ingestao/adaptadores/energia.py:106` | energia |
| `api/app/ingestao/adaptadores/inep.py:87` | INEP (educação) |
| `api/app/ingestao/adaptadores/ana.py:114` | ANA (águas) |
| `api/app/ingestao/adaptadores/pncp.py:95` | PNCP (contratações) |
| `api/app/ingestao/adaptadores/estban.py:106` | ESTBAN (Bacen) |
| `api/app/core/config.py:48` | host externo na configuração |
| `api/scripts/diagnostico_estban.py:96` | ESTBAN |

**Por que classifico como violação e não como falso-positivo:** a obrigação do
Art. 39 é de **registro**, e o registro não existe. Dado público não é sinônimo de
dado impessoal — SISVAN e INEP, em particular, distribuem microdados de saúde e
educação. O manifesto é onde se declara residência, base de transferência e
`egress_fields`; sem ele, S-05 e S-08 ficaram sem o que auditar (N/A em cascata),
o que significa que **três checks de terceiros foram neutralizados por um arquivo
ausente**.

**Contra-argumento que reconheço:** a maioria destes hosts é `gov.br`, e uma API
pública de consulta pode não configurar operador de tratamento. Isso é mérito, e
mérito é do dono. → PENDÊNCIA D-04.

#### S-04 · ALTO · hosts embutidos no módulo de seed (6)

`api/app/seed/__init__.py:77, 89, 113, 137, 197, 209` — seis hosts distintos.
Seed é **código que executa e popula a base**: os hosts ali são reais e entram no
fluxo de dados do produto, não em andaime de teste.

### 3.2 FALSO-POSITIVO-PROVÁVEL (9)

| Achado | Arquivo:linha | Por quê |
|---|---|---|
| S-04 ALTO | `web/app/robots.ts:4` | **`robots.txt`.** O host ali é o próprio domínio público do site, numa diretiva de crawler. Não é integração, não é egresso, não é terceiro |
| S-04 ALTO ×3 | `web/lib/agir.test.ts:39, 55, 56` | **Teste unitário** de frontend, com URLs de fixture |
| S-04 ALTO | `.env.example:68` | Template de ambiente versionado |
| S-04 ALTO ×4 | `api/scripts/diagnostico_caged.py:45, 46, 47, 48` | Quatro variantes de URL do **mesmo** CAGED, em linhas consecutivas de um script de **diagnóstico** manual. S-04 desduplica por host, mas variantes de path viram hosts distintos — 4 achados para 1 integração, num arquivo que nem é caminho de produção |

**Padrão sistêmico:** S-04 conta **um achado por host distinto**, o que numa
plataforma de ingestão com dezenas de fontes governamentais gera volume alto e
repetitivo. 26 achados de S-04 num único alvo é o tipo de ruído que ensina o
operador a rolar a página. → PENDÊNCIA S-03.

### 3.3 INCERTO (2)

| # | Achado | Arquivo:linha | Por que não decido |
|---|---|---|---|
| 1 | **P-04 ALTO** — catálogo de dados ausente | `tests/qa/catalog.yaml:1` | Caminho *default* da suíte, não declaração do alvo. Mas aqui o mérito é mais forte que em GIVA: o README diz que "o ativo do negócio é a confiança — privacidade estrutural, proveniência e qualidade comprovada existem para protegê-la a cada commit". Um alvo que se declara assim e ingere SISVAN/INEP tem argumento próprio para manter catálogo. → PENDÊNCIA D-02 |
| 2 | **P-07 ALTO** — modelo de consentimento ausente | `tests/qa/consent-model.yaml:1` | Idem. Plataforma de dado **público agregado** pode legitimamente operar sem consentimento (base legal diversa) |

---

## 4. O que a suíte auditou e não achou — vale registrar

Em 309 arquivos Python:

- **P-01** (PII em log) — nenhum achado. Nenhuma variável da régua entrando crua
  numa chamada de log. Notável para uma plataforma de ingestão de dados.
- **P-06 / S-06** (chave e credencial literal) — nenhum achado. **O único dos 6
  alvos sem nenhum CRÍTICO de segredo**, incluindo em `tests/`, onde os outros 5
  concentram falso-positivo.
- **P-03** (soft-delete) — nenhum achado; verificado que não há `deleted_at` /
  `is_deleted` no alvo. Ausência real, não supressão.
- **E-04** (HITL) e **E-05** (proxy de discriminação) — nenhum achado.
- **E-10** (incerteza) — nenhum achado, ao contrário dos outros dois alvos com
  motor de score.

Isso é **AUDITADO com resultado negativo** em 5 categorias, e é a informação de
maior valor deste laudo. Não altera o veredito: E-06 continua indeterminado e o
frontend continua fora de alcance.

---

## 5. Resumo da triagem

| Classe | Qtd. | % |
|---|---|---|
| VIOLAÇÃO-PROVÁVEL | 17 | 61% |
| FALSO-POSITIVO-PROVÁVEL | 9 | 32% |
| INCERTO | 2 | 7% |
| **Total** | **28** | |

Conferência: `python scripts/verificar_triagem.py`.

**A maior taxa de violação-provável da rodada (61%) — e nenhum CRÍTICO.** O perfil
é o oposto de Criptotrade: lá o falso-positivo vinha de fixtures em checks
CRÍTICOS e dirigia o gate; aqui os achados são reais, todos ALTO, e todos do mesmo
tipo — **integração externa não registrada**, resolvível por um único arquivo
(`.privacy/third-party-manifest.yml`) que hoje não existe e que, ao faltar,
também neutralizou S-05 e S-08.

O ruído que resta (9) vem do **volume** de S-04, não de erro de julgamento da
régua: `robots.ts`, teste de frontend, template de ambiente e 4 variantes de URL
do mesmo CAGED. Registrado em PENDÊNCIA S-03, não corrigido nesta rodada.
