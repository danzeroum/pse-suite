# Como adotar a PSE Suite no consumidor (`danzeroum/project`)

Tudo que entra no consumidor é **declarativo ou de orquestração**. Nenhum check,
nenhuma régua, nenhum threshold fora das faixas que a suite valida.

## 1. Pin da versão (fonte única)

```
# requirements-qa.txt  — único lugar com o número; todo o resto referencia
pse-suite==0.8.0
```

## 2. Config declarativa

```yaml
# tests/qa/pse-config.yaml
pse_suite:
  version_source: requirements-qa.txt      # nunca restate a versão
  catalog_path: tests/qa/catalog.yaml
  third_party_manifest: .privacy/third-party-manifest.yml
  consent_model_path: tests/qa/consent-model.yaml
  lineage_path: lineage.jsonl              # E-08 (opcional: ha candidatos padrao)
  decision_making: automated               # none | assistive | automated
  thresholds:                              # a suite valida a faixa (§10)
    k_anonymity_min: 5
    dpd_max_delta: 0.05
  packs:
    privacy:  {enabled: true}
    security: {enabled: true}
    ethics:
      enabled: true
      fairness_dataset: tests/qa/fixtures/eval.parquet   # E-06 exige
      fairness_report: tests/qa/fairness-report.yaml
```

`packs.*.enabled: false` é **obedecido** e aparece no laudo em
`packs_desabilitados` com o motivo — omissão declarada, nunca silêncio.
Desabilitar *todos* os packs é entrada inválida (exit 30): laudo vazio não é
laudo conforme.

`decision_making` alimenta o **E-00**, a guarda de escopo do pacote de Ética.
Alvo sem decisão automatizada tira o pacote inteiro de escopo com motivo
computado; declarar `none` num código que mostra modelo de ML vira **achado** —
a divergência entre declaração e fato é o que o auditor precisa ver.

## 3. Catálogo vivo (P-04 cobra a existência e a coerência)

```yaml
# tests/qa/catalog.yaml
tables:
  users:
    fields:
      cpf:
        class: personal          # personal | sensitive | anonymized
        owner: financeiro
        purpose: faturamento
        legal_basis: contrato    # sensitive NUNCA aceita legitimo_interesse (P-08)
        retention_years: 5       # declarar retenção exige job de purga REAL (P-02)
```

P-02 exige um **job que execute a eliminação** — função de expurgo cujo corpo
apaga de verdade. A palavra "purge" num comentário não conta.

## 4. Manifesto de terceiros (S-04 / S-08)

```yaml
# .privacy/third-party-manifest.yml
integrations:
  - name: google-analytics
    hosts: [analytics.google.com]
    dpa_signed: true             # false + required -> CRITICO, deploy bloqueado
    dpa_path: contracts/ga-dpa.pdf
    data_residency: US
    transfer_basis: SCC_ANPD     # fora do BR sem base -> S-08
```

## 5. Trabalho A — contrato de autorização

Schema: `pse/schemas/trabalho-a-config-1.0.json`. **Nada de runtime dispara sem
isto.** O `inherits: tests/qa/config.yaml` do plano original caiu: acoplar a PSE
a um schema não publicado da WebQA Suite recriaria a deriva que a doutrina
combate.

```yaml
# tests/qa/pse-config.yaml (continuação)
pse_suite:
  target:
    base_url: https://staging.exemplo.com   # TLS obrigatório
    environment: staging                    # staging | production
    healthcheck: /health                    # != 200 -> Trabalho A indeterminado (20)
    timeout_s: 10

    identities:                             # NOMES de variáveis, nunca valores
      titular_a: {token_env: PSE_TOKEN_A}
      titular_b: {token_env: PSE_TOKEN_B}

    resources_titular_b:                    # recursos da conta sintética B
      - /api/clientes/9f1c2e3a-0000-4000-8000-000000000000

    endpoints:                              # superfícies declaradas por check
      inexistente: /api/clientes/00000000-0000-4000-8000-000000000000  # P-11
      erro:        /api/nao-existe          # S-03
      listagem:    /api/clientes            # S-02, S-07
      escrita:     /api/clientes            # P-05 — escreve de verdade
      decisao:     /api/decisoes/ultima     # E-01, E-02
      contestacao: /api/contestacoes        # E-03 — gera protocolo real
      log_auditoria: /api/logs              # S-07
      exportacao:  /api/exportacao          # P-10 — corpo OMITIDO do trace
      agregacao:   /api/relatorios/bairro   # P-09
      consentimento_protegido: /api/perfil  # P-07
      kill_switch_dry_run: /api/kill-switch # E-09 — SÓ simulação

    authorization:
      attested_by: nome@dominio             # humano identificável
      scope: [pse_passive]                  # granularidade POR MODO
      target_fingerprint: <sha256(base_url)>  # amarra a atestação a ESTE alvo
      expires: "2026-09-30"                 # obrigatória
      synthetic_identities: true            # obrigatória para pse_active
```

Tudo aninhado sob `target`: identidades, recursos e atestação são propriedades
**do alvo auditado**. Separá-las convidaria a apontar uma atestação para outro
alvo — e é exatamente isso que o `target_fingerprint` existe para impedir.

Os segredos vivem no cofre do CI; o YAML versionado carrega só o **nome** da
variável. Prefixo `PSE_` fixo, para que o fiscal de higiene de ambiente do
consumidor prove que a família inteira está coberta pela denylist.

### Classificação de modos

**Passivo** = requisição somente-leitura com a própria identidade do chamador.
**Ativo** = qualquer sonda de autorização negativa, cruzamento de identidades ou
tentativa que espera rejeição. S-01 envia o token de A contra recurso de B: é
sonda deliberada, e ser só-leitura não a torna passiva.

| Modo (`--modo`) | Checks | Dispara |
|---|---|---|
| `pse_inventory` (B, padrão) | os 13 estáticos | automático; agente pode |
| `pse_passive` (A) | S-03, E-01, E-02 | automático, com atestação de escopo `pse_passive` |
| `pse_active` (A) | **S-01**, S-02, S-07, P-05, P-07, P-09, P-10, P-11, E-03, E-09 — mais todos os passivos | só `workflow_dispatch` com revisores + escopo `pse_active` |

Um check `passive` também roda em `pse_active`; um `active` **nunca** roda em
`pse_passive`. S-07 segue `previsto-fase-2`: aparece em `checks_previstos` com
motivo, não em silêncio.

**S-07 foi reclassificado de passivo para ativo** na Fase 3: ele envia uma
requisição sem `X-Purpose` esperando recusa, e sonda que espera rejeição é
ativa — ser somente-leitura não a torna passiva. Reclassificação na direção
conservadora, conforme a regra.

Três checks ativos **escrevem ou acionam no alvo**: P-05 faz `POST` na rota de
escrita, E-03 abre uma contestação real e E-09 dispara o **dry-run** do kill
switch. Por isso `synthetic_identities: true` é obrigatório no escopo ativo, e
por isso produção é recusada.

**E-09 nunca aciona o switch de verdade.** O parâmetro de simulação é constante
no código; se o alvo recusar o dry-run, o check fica indeterminado e **não há
retentativa sem a marca de simulação**. A suite não descobre "na marra" se o
interruptor funciona.

`pse_active` contra `environment: production` é **recusado** pela suite na v1
(exit 30). Revisável em versão futura com dupla atestação.

### Ausência de autorização nunca é verde

- Trabalho A **não habilitado** (sem `target`) → checks A aparecem em
  `checks_nao_habilitados` com motivo. Não bloqueia: o exit segue o Trabalho B.
- Modo que não dispara o check (ativo pedido em `pse_passive`) → idem.
- Trabalho A **habilitado** com atestação ausente, vencida, sem o modo no
  `scope`, ou com `target_fingerprint` divergente da `base_url` → todos os
  checks A em `checks_indeterminados` com o motivo específico, **exit 20**.
- A atestação inteira (nunca os segredos) é carimbada no bloco `artifact` do
  laudo: quem autorizou, o quê, até quando.

## 6. Veredito — o que o CI lê

| Código | Significado | Bloqueia? |
|---|---|---|
| `0` | conforme | não |
| `10` | violação com CRÍTICO | sim |
| `11` | violação com ALTO, sem CRÍTICO | política do CI (abaixo) |
| `20` | indeterminado | **sim, igual ao 10** |
| `30` | entrada inválida | sim |

A suite **não tem flag que rebaixe o gate**. A política "ALTO bloqueia em
`main`, avisa em feature branch" é do consumidor, e é onde o dono da decisão
fica visível:

```yaml
- name: laudo PSE
  id: pse
  continue-on-error: true
  run: pse --path . --config tests/qa/pse-config.yaml
           --output harness/reports/laudo-pse.json
- name: gate
  run: |
    RC=${{ steps.pse.outcome == 'success' && '0' || steps.pse.conclusion }}
    CODE=$(python -c "import json;print(json.load(open('harness/reports/laudo-pse.json'))['exit_code'])")
    case "$CODE" in
      0)  echo "conforme" ;;
      11) [ "${{ github.ref }}" = "refs/heads/main" ] && exit 1 || echo "::warning::ALTO em branch" ;;
      *)  exit 1 ;;    # 10, 20, 30 bloqueiam sempre
    esac
```

## 7. CI — laudo em toda PR + passo negativo (a mordida)

```yaml
# .github/workflows/qa.yml (acréscimo)
pse-inventory:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-qa.txt
    - name: laudo PSE (fail-closed)
      run: pse --path . --config tests/qa/pse-config.yaml
                --output harness/reports/laudo-pse.json
    - name: mordida — prova que a trava aborta (inclui as 21 mutações canônicas)
      # A fixture viaja DENTRO do wheel: este passo não depende de clonar a
      # suite. Se a trava parar de morder, o consumidor descobre aqui.
      run: pse --self-test

pse-passive:                     # Trabalho A somente-leitura, automático
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-qa.txt
    - run: pse --path . --config tests/qa/pse-config.yaml --modo pse_passive
      env: {PSE_TOKEN_A: "${{ secrets.PSE_TOKEN_A }}"}

pse-active:                      # sonda de autorização — NUNCA automático
  if: github.event_name == 'workflow_dispatch'
  environment: pse-active        # exige revisores aprovarem o deploy
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-qa.txt
    - run: pse --path . --config tests/qa/pse-config.yaml --modo pse_active
      env:
        PSE_TOKEN_A: "${{ secrets.PSE_TOKEN_A }}"
        PSE_TOKEN_B: "${{ secrets.PSE_TOKEN_B }}"
```

## 8. Rastreabilidade no grafo do projeto

Cada controle de **produto** (consent engine, decision logger, contestação,
kill switch...) é um `REQ-*` no `business/requirements/backlog.yaml`, com
`validated_by` apontando para o teste que consome o check PSE correspondente —
fechando o elo bidirecional que `ci/validate_metadata.py` já cobra.

Alterar `tests/qa/pse-config.yaml` deve ser **caminho protegido** (CODEOWNERS):
afrouxar a régua exige aval humano visível. Isso vale em dobro para
`packs.*.enabled`, `decision_making` e o bloco `authorization`.

## 9. Procedência

O laudo carrega a quíntupla `(suite, suite_version, repo_commit, catalog_hash,
schema_version)`. O `catalog_hash` cobre `pse/data/` e o código dos checks: dois
laudos que declaram a mesma versão mas divergem no hash foram produzidos por
réguas diferentes. `pse --manifesto` emite o mesmo conjunto no release, com o
resultado da autoprova.

## 10. Thresholds — o consumidor aperta, nunca afrouxa

| Threshold | Faixa da suite | O consumidor pode |
|---|---|---|
| `k_anonymity_min` | piso **5** | aumentar |
| `dpd_max_delta` | teto **0,10** | diminuir |

Declarar fora da faixa não vira achado: vira **recusa de execução** (exit 30).
Achado o operador aprende a ignorar; recusa de execução, não. Threshold que a
suite não conhece também é recusado — um threshold que ela não valida é um
campo de configuração com nome de régua.

## 11. E-06 — o dataset é insumo declarado

`fairness_dataset` ausente deixa E-06 em `checks_indeterminados` (exit 20),
nunca verde. A suite **não sai procurando** qual arquivo seria o dataset, e
**não roda inferência**: carregar os dados e executar o modelo significaria
processar dado sensível de titular real dentro da ferramenta de auditoria,
para produzir um número que o consumidor já tem.

O que ela cobra é o relatório (`fairness-report-1.0`): DPD por grupo, ancorado
à versão do modelo, com o `dataset_fingerprint` que prova o frescor e as
**condições de medição**. Número sem condições não entra.

## 12. IA e cadeia de terceiros (E-11 · E-12 · E-13)

Estáticos, rodam no `pse_inventory` — sem rede, agente pode disparar. Todos
carregam **Art. 42** junto da base específica.

**E-11 · PII em prompt de LLM.** Os fornecedores reconhecidos saem da régua
(`third-party-endpoints.yaml`, categoria `llm`); os termos de PII saem de
`pii-patterns.yaml`. Nada é hardcoded no check — se um fornecedor entra na
régua, o check passa a reconhecê-lo sem tocar em código.

```python
llm.complete(f"cliente {user.cpf}")          # CRÍTICO
llm.complete(redact(prompt))                 # conforme — a chamada executa
# TODO: redact  ...  llm.complete(user.cpf)  # CRÍTICO: comentário não redige
```

**E-12 · derivado tratado como anônimo.** Exportar `embedding`/`hash`/`vetor`
de um campo que o catálogo **não** classifica como `personal`/`sensitive` é
achado. Classifique a origem e o check silencia — o objetivo é a coerência do
inventário, não proibir derivados. Sem catálogo: indeterminado (20).

**E-13 · dependência que exfiltra.** Cruza os hosts encontrados dentro de
`node_modules`/`site-packages`/`vendor` contra o manifesto. Sem manifesto o
check é pulado com motivo (a ausência é de S-04). Hosts de registro, licença e
documentação ficam em `ignorar_em_dependencias` — lista própria e estreita, e
um teste-guarda proíbe que qualquer host de categoria conhecida (analytics,
llm, cdn) entre nela.

O teto de varredura é da suite (4000 arquivos). Quando é atingido, o laudo diz
em `relatorios.cobertura_parcial` — truncamento silencioso leria como
"varri tudo".

## 13. E-08 — trilha de proveniência (o último check do catálogo)

Estático. Só roda quando há o que rastrear: se o catálogo não declara nenhum
campo `personal`/`sensitive`, o check é **pulado com motivo** — N/A declarado,
não verde.

```jsonl
{"dataset": "clientes", "origem": "formulario_web", "transformacao": "validacao + pseudonimizacao", "destino": "postgres.clientes", "campos": ["cpf","email"], "atualizado_em": "2026-08-06"}
```

Três coisas são cobradas, nesta ordem:

1. **O artefato existe.** `lineage_path` declarado vence; sem declaração a
   suite procura candidatos padrão (`lineage.jsonl`, `docs/lineage.jsonl`,
   `.privacy/lineage.jsonl`, …). Declaração que não resolve **é** o achado —
   não motivo para sair procurando outro arquivo.
2. **Cada registro fecha o ciclo**: `origem`, `transformacao` e `destino`.
   Trilha que para no meio não rastreia até o fim, e o fim é justamente o que
   interessa quando se pergunta para onde o dado foi.
3. **A trilha alcança o que existe**: toda tabela com campo pessoal precisa de
   registro. Cobertura aparente esconde buraco.

Arquivo ilegível é **indeterminado** (exit 20), não "sem trilha": quebrado não
é ausente. E documentação afirmando rastreabilidade não conta — a busca só
olha `.jsonl`/`.json`/`.yaml`, nunca `.md`. Se afirmação bastasse, a trava
seria desligável escrevendo um parágrafo.

Base legal: rastreabilidade (Art. 37), com **Art. 42** junto quando o
manifesto declara terceiros — a trilha que atravessa operador carrega a
responsabilidade solidária.

## 14. A matriz: pilar × domínio

A suite deixou de ser backend-only. Cada check declara, além do **pilar**
(privacy/security/ethics), um **domínio** técnico — `frontend`, `api`,
`backend`, `data`, `ai`, lista quando couber.

```bash
pse --path . --pilar privacy               # o DPO: privacidade em todos os estratos
pse --path . --domain frontend             # o time de front: os três pilares no seu estrato
pse --path . --pilar privacy --domain data # o cruzamento
pse --path . --packs frontend              # `--packs` aceita os dois vocabulários
```

Os dois eixos são ortogonais de propósito: o pilar responde *que valor está em
jogo*, o domínio responde *onde ele se manifesta no sistema*. Nenhum check foi
duplicado para a matriz existir — os 33 anteriores foram reclassificados, não
reescritos.

**Recorte que não alcança check nenhum é entrada inválida (exit 30)**, não
"conforme": seria verde por não ter olhado, com o agravante de o consumidor
achar que pediu uma auditoria. O laudo traz `cobertura.por_dominio` justamente
para que um estrato com zero checks apareça como zero, e não seja omitido.

Marcadores pytest acompanham: `-m pse_frontend`, `-m pse_api`, `-m pse_backend`,
`-m pse_data`, `-m pse_ai`, ao lado dos de pilar.

## 15. Domínio frontend (P-13 · P-14 · S-09)

Estáticos, sobre **AST real** de `.js/.jsx/.ts/.tsx` (tree-sitter, gramáticas
javascript e tsx). O material de fundação do frontend propõe `grep -rn`; grep
serve para achar *onde olhar* e nunca como check — é literalmente o D-01, a
menção passando por fato.

| Check | Pilar | Dispara | Não dispara |
|---|---|---|---|
| **P-13** consentimento pré-marcado (CRÍTICO) | privacy | `<input type="checkbox" name="consent_x" checked />` sem handler | `checked={estado} onChange={...}` — escolha registrada; toggle que nasce desligado; `// consent default on` em comentário |
| **P-14** PII no cliente ou na URL (CRÍTICO) | privacy | `localStorage.setItem("cpf", user.cpf)`; `"?email=" + user.email` | valor mascarado (`mask(user.cpf)`); identificador opaco |
| **S-09** token no cliente (ALTO) | security | `localStorage.setItem("token", jwt)`; `document.cookie = "token=…"` | sessão em cookie HttpOnly+Secure emitido pelo servidor, com `credentials: "include"` |

Arquivo que **não parseia** vira `CheckIndeterminado` com a linha do erro
(exit 20), jamais verde: sem AST não há decisão pelo fato. O mesmo vale se a
gramática não estiver instalada no ambiente — a suite declara a limitação e
bloqueia, em vez de fingir cobertura.

P-13 e P-14 são CRÍTICOs, então **falso-positivo aqui custa o pack inteiro**:
o time de frontend aprende a ignorá-lo no primeiro dia. Por isso os testes que
provam que o caso correto **não** dispara vêm antes dos que provam a violação.

## 16. Estrato de IA (S-10 · S-11 · P-15 · P-16)

Estáticos, no `pse_inventory`. Fecham os dois buracos que a matriz expôs.

**S-10 · injeção de prompt.** Três vetores, um check, um CRÍTICO — é o mesmo
ponto de entrada:

```python
llm.complete("resuma: " + request.body)              # CRÍTICO (os três vetores)
llm.complete(sanitize(request.body))                 # conforme (genérico cobre tudo)
t = delimitar(truncar(normalizar_nfkc(req.body), 4000))
llm.complete(t)                                      # conforme (uma proteção por vetor)
# sanitize later  →  llm.complete(request.body)      # CRÍTICO: menção não protege
```

Fontes de entrada, codepoints invisíveis, teto de tamanho e nomes de proteção
vivem em `pse/data/adversarial-patterns.yaml`, com teste-guarda de piso.

**S-11 · saída do modelo em sink perigoso.** Rastreio curto e honesto: o
aninhamento direto (`exec(llm.complete(p))`) e uma variável
(`r = llm.complete(p)` … `db.query(r)`). Não promete fluxo interprocedural —
prometer o que não se entrega seria pior que a lacuna.

**P-15 · PII como feature de treino.** Declare a finalidade no catálogo:

```yaml
cpf:
  purpose: analise_de_credito, treino_de_modelo   # inclui treino → não dispara
  legal_basis: consentimento                       # sensível exige Art. 11
```

A severidade é **condicional** (ratificada): campo `class: sensitive` sem
finalidade de treino é **CRÍTICO** — Art. 11 é trava estrutural, o mesmo
princípio que já rege P-08 — e campo pessoal comum é **ALTO**. Declarar a
finalidade desliga os dois: elevar a severidade sem manter essa porta aberta
transformaria a régua em armadilha.

**P-16 · dataset de treino sem governança.** Nova seção no catálogo, com o
mesmo rigor que se cobra de uma tabela:

```yaml
datasets:
  base_credito:
    finalidade: treino_de_modelo_de_risco
    retention_years: 2
    origem: postgres.clientes
    base_legal: consentimento
```

Sem treino no código, P-15 e P-16 são **pulados com motivo**. Com treino e sem
catálogo, P-15 é **indeterminado** (exit 20) — sem inventário a pergunta não é
respondível.
