# Como adotar a PSE Suite no consumidor (`danzeroum/project`)

Tudo que entra no consumidor é **declarativo ou de orquestração**. Nenhum check,
nenhuma régua, nenhum threshold fora das faixas que a suite valida.

## 1. Pin da versão (fonte única)

```
# requirements-qa.txt  — único lugar com o número; todo o resto referencia
pse-suite==0.14.1
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

## 17. Estrato de API (S-12 · P-17 · S-13)

Três checks nascidos da pergunta *o que é próprio de uma borda de API?* — o
contrato, o filtro de busca e o payload de erro.

**S-12 · ontologia no contrato.** Declare a PII no espaço de extensão do
próprio OpenAPI, onde quem consome a API já olha:

```yaml
components:
  schemas:
    Cliente:
      x-ethics:
        pii: [cpf, email]
        sensitive: [genero]
        allowlist_scopes:
          cliente:leitura: [id, cidade]        # o escopo restrito
          cliente:completo: [id, cidade, cpf]  # o escopo amplo
        purpose: atendimento_ao_cliente
      properties:
        id: {type: string}
        cpf: {type: string}
```

Dois vetores: schema com PII e **sem** `x-ethics` → achado; `x-ethics` que
promete um campo que a classe homônima em Python **não implementa** → achado.
O segundo é o de maior valor — ontologia que ninguém implementou é confiada
por quem lê o contrato.

Schema sem dado pessoal **não** precisa de `x-ethics`: exigi-lo de um `Pedido`
com id e valor seria burocracia, e burocracia ensina o time a preencher por
reflexo. Sem nenhum arquivo com `openapi:`/`swagger:` de topo, o check é
**pulado com motivo**; spec que não parseia é **indeterminado** (exit 20).

**Limite declarado:** a ligação schema → DTO é por *nome de classe*. Repo que
só publica contrato (gateway, monorepo de specs) não tem DTO e não é punido
por isso — o vetor B simplesmente não é avaliado ali.

**P-17 · filtro sensível na busca.**

```python
@app.get("/clientes")
def buscar():
    return repo.buscar(raca=request.args.get("raca"))   # ALTO

@app.get("/clientes")                                   # conforme
def buscar():
    filtros = validar_filtros(request.args)             # allowlist que EXECUTA
    return repo.buscar(**filtros)
```

Lê os dois lados do mesmo fato: a view (parâmetro nomeado ou
`request.args.get`) e o **contrato** (`parameters: [{in: query, name: raca}]`)
— é no contrato que a capacidade fica pública. O caminho correto mais comum
sequer chega ao check: quem monta o filtro a partir de um vocabulário fechado
nunca menciona um campo proibido.

**S-13 · erro expõe internals.**

```python
return jsonify({"trace": traceback.format_exc()}), 500   # ALTO: pilha
return jsonify({"modulo": __file__}), 500                # ALTO: caminho
return jsonify({"runtime": sys.version}), 500            # ALTO: versão
app.run(debug=True)                                      # ALTO: console interativo

log.exception("falha")                                   # conforme: vai para dentro
return jsonify({"erro": "interno", "correlacao": cid}), 500
```

A distinção é onde o traceback **chega**: retorno ou construtor de resposta é
achado; chamada de log não é. Punir observabilidade empurraria o time a apagar
o traceback em vez de sanear a resposta.

## 18. Estrato de backend (S-14 · S-15 · P-18 · P-19 · S-16)

Cinco vetores de infraestrutura que só existem deste lado do sistema.

**S-14 · dump de produção em ambiente inferior.**

```bash
pg_dump "$PROD_URL" > dump_prod.sql
psql "$STAGING_URL" < dump_prod.sql            # ALTO

pg_dump "$PROD_URL" > dump_prod.sql            # conforme
python scripts/anonimizar_dump.py dump_prod.sql dump_anon.sql
psql "$STAGING_URL" < dump_anon.sql
```

O achado exige origem de produção **e** destino inferior na mesma linha —
`pg_dump prod > prod.sql` é só backup e não dispara. O passo de
descaracterização precisa rodar **antes** do restore, no mesmo arquivo (um
pipeline partido em dois arquivos é um limite declarado no check). Pega
também no YAML do CI, que é onde o restore de fato roda.

**S-15 · role com privilégio excessivo.**

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA public TO app;  -- ALTO: vale para o futuro
GRANT ALL PRIVILEGES ON clientes TO app_etl;         -- ALTO: inclui DELETE
GRANT SELECT ON clientes TO app;                     -- ALTO: tabela com PII
GRANT SELECT (id, cidade) ON clientes TO app;        -- conforme: por coluna
```

**P-18 · sensível sem cifra de aplicação.** Declare no catálogo:

```yaml
genero:
  class: sensitive
  encryption:
    algorithm: AES-256-GCM
    key_management: aws-kms       # KMS | Vault | HSM — fora da aplicação
```

Dois caminhos para o verde: a declaração acima, **ou** uma cifra de aplicação
aplicada ao campo no código. Cifra declarada **sem** `key_management` continua
sendo achado — a chave que a aplicação guarda viaja junto com o dump.

**P-19 · eliminação em log append-only.**

```python
producer.send("clientes", {"cpf": c.cpf})                    # ALTO
producer.send("clientes", cifrar_por_titular({...}, c.id))   # conforme
def esquecer(titular_id): return destroy_key(titular_id)     # conforme
```

A rotina de crypto-shredding é procurada no **repositório inteiro** — ela
quase nunca mora ao lado do produtor, e exigi-la no mesmo arquivo reprovaria
toda arquitetura bem separada.

**S-16 · residência no ponto de escrita.**

```yaml
# tests/qa/pse-config.yaml
pse_suite:
  data_residency: BR        # sem esta linha o check é PULADO, não presumido
```

```python
boto3.client("s3", region_name="us-east-1")   # ALTO com data_residency: BR
boto3.client("s3", region_name="sa-east-1")   # conforme
```

Sem `data_residency` declarado o check é **pulado com motivo**. Supor `BR`
porque a LGPD é brasileira seria a suite decidindo pelo consumidor uma coisa
que é dele — há operação legítima com residência europeia, e achado inventado
custa mais confiança do que achado ausente.

## 19. Estrato de dados (P-20) — e o P-21 que não existe

**P-20 · hash sem chave tratado como anonimização.**

```python
h = hashlib.sha256(cliente.cpf.encode()).hexdigest()   # ALTO
db.insert("dim_cliente", {"id_anonimo": h})            # ...porque é guardado

hashlib.sha1(c.biometria.encode()).hexdigest()         # CRÍTICO: sensível

# conforme — HMAC com chave de cofre
hmac.new(chave_do_vault("pseudo"), c.cpf.encode(), hashlib.sha256)

# conforme — sal aleatório por registro
sal = secrets.token_bytes(16)
hashlib.sha256(sal + c.email.encode())

# conforme — checksum de conteúdo: não há titular nisto
hashlib.sha256(conteudo).hexdigest()
```

Três condições, todas necessárias: digest **determinístico e sem segredo**,
sobre **campo de PII**, cujo resultado **alcança escrita ou exportação**. Hash
em memória que não é guardado não é dado; hash de arquivo não toca titular.

O grupo `credenciais` da régua está **fora de escopo por construção** —
hashear senha é o que se deve fazer, e o defeito ali (falta de KDF) é outro
assunto.

E a recomendação que o achado carrega vale repetir: enquanto houver qualquer
forma de reverter, o campo continua sendo **dado pessoal** no catálogo.
Pseudonimizado não é anonimizado.

**P-21 — o check que decidimos não escrever.** Zona bruta de data lake com
acesso irrestrito é risco real, e mesmo assim não virou check:

1. identificar a zona bruta viria do **nome** do bucket (`raw`, `bronze`,
   `landing`) — menção, não fato, e o D-01 proíbe esse atalho num check que
   bloquearia CI;
2. policy sem `Condition` no Terraform **não é violação por si**: a restrição
   pode viver numa SCP, num permission boundary, num grant de Lake Formation
   ou no provedor de identidade, todos fora do repositório — o check acusaria
   setup correto;
3. a suite não tem parser de HCL, e adicionar um para avaliar uma forma de
   política indecidível seria construir a **aparência** de cobertura.

O que faria P-21 nascer: um artefato de policy-as-code versionado declarando
finalidade e expiração por zona. Aí há declaração a confrontar com fato — que
é como todos os outros funcionam.

## 20. Camada dinâmica (P-22 · S-17 · P-23) — o navegador

Até aqui a suite lia repositório. Estes três **carregam a página e observam**.

### Instalação — Playwright é opcional

```bash
pip install pse-suite                 # estático apenas; segue leve
pip install 'pse-suite[browser]'      # + camada dinâmica
python -m playwright install chromium
```

Sem Playwright, os dinâmicos ficam **indeterminados (exit 20) com instrução de
instalar** — nunca verdes. Não ter olhado é diferente de olhar e não achar
nada, e o laudo diz qual dos dois aconteceu.

`PSE_BROWSER_ENGINES=chromium,firefox` roda a matriz de engines. **Engine
desconhecida é exit 30**, não filtro silencioso: um typo que degenerasse em
"rodou zero engines e passou" seria a pior forma de verde falso.

`PSE_BROWSER_EXECUTABLE` aponta um binário fora do registro do Playwright —
útil em imagem de container onde o navegador já vem instalado.

### O contrato de Trabalho A rege o navegador

Nenhuma página é aberta antes dos cinco degraus (modo → atestação → tokens →
healthcheck). Sem atestação válida, os três vão para `checks_indeterminados` e
o processo sai **20** — e zero navegações são emitidas. Isso é medido por
contagem nos testes, não prometido em docstring.

Os três são **passivos**: carregam e observam. Clicar no banner e submeter
formulário escrevem no sistema do alvo e ficam para a fase seguinte, atrás do
gate ativo.

**`http://` só é aceito em loopback** (`127.0.0.1`, `localhost`). É mudança de
regra declarada: a exigência de https existe porque sonda em texto claro vaza o
token na rede, e em loopback não há rede. `http://127.0.0.1.atacante.com` segue
recusado — a exceção casa o host exato.

### Configuração

```yaml
pse_suite:
  target:
    base_url: https://staging.exemplo.com
    environment: staging
    healthcheck: /health
    trackers_allowlist:            # decisão documentada do controlador
      - tagmanager.exemplo.com     # já opera sob consentimento gerenciado
    authorization:
      attested_by: nome@dominio
      scope: [pse_passive]
      target_fingerprint: <sha256(base_url)>
      expires: "2026-12-31"
```

```bash
pse --path . --config tests/qa/pse-config.yaml --modo pse_passive
```

### O que cada um observa

| | Achado | Conforme |
|---|---|---|
| **P-22** | `_ga` gravado ou `google-analytics.com` chamado no primeiro load | tag só depois do aceite; cookie essencial (sessão, CSRF, idioma) nunca conta |
| **S-17** | `Set-Cookie: sessionid=...` sem `HttpOnly`/`Secure`/`SameSite` | `HttpOnly; Secure; SameSite=Lax` |
| **P-23** | `<a href="/f?cpf=...">`, `<form method=get><input name=cpf>` | identificador opaco na URL; `method=post` para dado pessoal |

P-22 é **ALTO e não CRÍTICO** de propósito: o nome do host não prova a
finalidade do tratamento. É sinal forte, não prova cabal — e o achado diz isso.

### A evidência não vaza o que ela prova

O valor do cookie **nunca existe** no objeto observado, e a query string entra
no laudo com os valores apagados (`?cpf=***`). O nome do parâmetro fica: é ele
que identifica o vazamento e orienta a correção. Um laudo que carimbasse o CPF
observado seria o segundo vazamento, e pior que o primeiro — distribuído por
CI, anexo de PR e caixa de e-mail.

### Correlação estático × dinâmico

O laudo ganha um bloco `correlacoes` ligando **P-14×P-23** e **S-09×S-17**:

| Cenário | Leitura |
|---|---|
| `confirmado_nas_duas_camadas` | foi escrito **e** está no ar; corrija pelo `arquivo:linha` do estático |
| `so_na_camada_estatica` | está no código e a observação não exercitou aquela rota |
| `so_na_camada_dinamica` | está no ar e **não** está no código auditado — template do servidor, tag gerenciada, dependência |

Nenhum finding é removido: é índice, não filtro. Deduplicar perderia
justamente a informação que só o par carrega.

## 21. Camada dinâmica — Fase 2 (S-18 · S-19 · S-20 · P-24 · S-21)

A Fase 1 olha requisição, cookie e URL. A Fase 2 lê **o corpo que o servidor
entregou**. Continua tudo passivo: nenhum check desta fase clica, submete ou
pede ao servidor um recurso que ele não ofereceu.

**S-18 · terceiro observado.** Par dinâmico de S-04. Todo host que a página
contacta recebe IP e User-Agent do visitante — operador que precisa estar
mapeado (Art. 37) e contratado (Art. 39). Declare no manifesto:

```yaml
# .privacy/third-party-manifest.yml
integrations:
  - name: tag-manager
    hosts: [tagmanager.exemplo.com]   # subdomínio herda: é o mesmo controlador
    dpa_signed: true
```

Sem manifesto o check é **pulado** (cobrado por S-04). O inventário completo
vai para `relatorios.terceiros_observados` mesmo sem achado — é insumo de
ROPA, e o consumidor precisa saber o que já está certo.

**S-19 · cabeçalhos e mixed content.**

```
Content-Security-Policy: default-src 'self'    # comece em Report-Only
X-Content-Type-Options: nosniff
Referrer-Policy: no-referrer
```

Só o **documento de origem** vira achado — cabeçalho ausente em asset de
terceiro é maturidade do fornecedor e entra como observação. `HSTS` e
`X-Frame-Options` também são observação: dependem de decisão de arquitetura.
Cabeçalho presente com valor vazio conta como **ausente**.

**S-20 · credencial servida.** Par dinâmico de P-06, e a urgência é outra:
a chave no bundle está **publicada**, e todo visitante já a leu.

```
rotacione a credencial  →  depois remova do código  →  depois mova a chamada
                                                        para o servidor
```

Nunca o contrário: apagar do código não invalida o que já foi servido. Corpo
acima de 512 KB não é lido, e se **nenhum** candidato puder ser lido o check
fica **indeterminado** — não avaliado nunca é limpo.

**P-24 · metadado publicado.** EXIF-GPS em imagem é achado; autoria é
observação. Remova o EXIF no pipeline de publicação, para toda imagem — o
upload de titular é o pior caso, porque a foto vem do celular dele.

**S-21 · sourcemap.** `//# sourceMappingURL` no bundle é **MEDIO**: o `.map`
**não é baixado**. Confirmar se está publicado exige uma requisição que o
navegador não fez — sondagem, logo Fase 3.

### O que ainda NÃO existe (Fase 3, atrás do gate ativo)

Clicar no banner de consentimento, submeter formulário, exercer direito de
titular, buscar o `.map`, pedir arquivo não linkado. Tudo isso **escreve ou
sonda** o sistema do alvo, e fica atrás de `pse_active` com atestação de
escopo própria. Na dúvida entre passivo e ativo, ativo.

## 22. Alvo local (`local_target`) e o teste de aceite

### `127.0.0.1` é caso especial, e por isso tem degrau próprio

Aplicação local-first (o `danzeroum/btv` é o caso) roda em loopback. Ali não
há rede: o pacote não passa por interface física, não há intermediário e não
há prova de posse a fazer — a razão da exigência de `https://` não alcança o
caso.

**E é justamente por isso que o degrau precisa ser explícito.** Sem ele,
qualquer coisa que suba numa porta local viraria alvo sondável sem registro,
e o contrato perderia o sentido no único lugar onde é mais fácil burlá-lo.

```yaml
pse_suite:
  target:
    base_url: http://127.0.0.1:8080     # http só em loopback
    environment: staging
    healthcheck: /health
    authorization:
      attested_by: nome@dominio
      scope: [pse_passive]
      expires: "2026-12-31"
      local_target: true                # SUBSTITUI o target_fingerprint
```

| Situação | Resultado |
|---|---|
| loopback **sem** `local_target` | **indeterminado** (exit 20) |
| `local_target: true` em alvo **publicado** | **exit 30** — a atestação estaria mentindo sobre o alvo |
| alvo publicado | `target_fingerprint` segue **obrigatório** |
| loopback + `local_target`, escopo/prazo faltando | indeterminado — o degrau substitui a prova de **posse**, não a autorização |
| alvo local **não iniciado** | indeterminado, **zero requisições** |

`local_target` substitui o fingerprint porque a porta de um alvo local é
efêmera: um fingerprint que muda a cada execução vira burocracia que o
operador aprende a colar sem ler.

### O bloco `alcance` — o que a suite **não** leu

Todo laudo agora carrega:

```json
"alcance": {
  "lidos": [{"linguagem": "Python", "arquivos": 88, "ferramenta": "ast (stdlib)"}],
  "fora_de_alcance": [{"linguagem": "Rust", "arquivos": 137}],
  "arquivos_fora_de_alcance": 173,
  "nota": "AUSENCIA DE ACHADO NAS LINGUAGENS ACIMA NAO E ATESTADO DE CONFORMIDADE..."
}
```

Não é finding — não há defeito no alvo por ser escrito em Rust. É **estado**:
sem ele, "nenhum achado em `.rs`" seria indistinguível de "Rust auditado e
limpo". Um consumidor que exija cobertura de Rust lê este bloco e decide.

### Teste de aceite (`aceites/*.yaml`)

A fixture prova que o **check** está certo. O aceite prova que a **régua**
reproduz um sistema real. São coisas diferentes, e a segunda só existe com
alvo de verdade.

```bash
python -m pse.aceite          # roda todos os aceites declarados
pytest -m pse_aceite          # o mesmo, como teste
```

O baseline compara por **faixa**, nunca por número exato — aceite que quebra
a cada commit do alvo é desligado no primeiro mês. O que ele fixa:
check que **parou de executar**, check que **parou de morder**, **falso
positivo novo**, e **estrato que saiu do alcance**.

**Alvo ausente → PENDENTE com motivo datado, nunca verde.** Mesma regra dos
checks dinâmicos, aplicada ao próprio aceite.
