# PSE Suite

Suite de **evidências de Privacidade, Segurança e Ética por Design** — o padrão
externo e versionado consumido pela harness de `danzeroum/project`.

> **O projeto declara configuração e autorização; o padrão fornece o motor e as verificações.**
>
> **Não copie a régua.** `pse/data/` (padrões de PII, campos sensíveis, proxies de
> discriminação, hosts de terceiros) evolui por versão deste pacote. Se cada
> consumidor tivesse uma cópia editável, remover uma linha faria o laudo dizer
> "nenhum achado" — sem erro, sem aviso, indistinguível de um projeto seguro.

## Os três pacotes (testes separados entre si)

| Pacote | Marcador pytest | Checks |
|---|---|---|
| Privacidade | `pse_privacy` | P-01 PII em logs · P-02 retenção · P-03 soft-delete · P-04 catálogo · P-05 minimização · P-06 chave no código · P-07 consentimento · P-08 sensível+legítimo interesse · P-09 k-anonimato · P-10 portabilidade · P-11 oráculo |
| Segurança | `pse_security` | S-01 BOLA/IDOR · S-02 rate limit · S-03 PII em erro · S-04 terceiro sem DPA · S-05 payload de egresso · S-06 credencial hardcoded · S-07 finalidade e log · S-08 transferência internacional |
| Ética | `pse_ethics` | E-00 escopo · E-01 explicação · E-02 decision log · E-03 contestação · E-04 rota humana · E-05 proxy de discriminação · E-06 disparidade · E-07 Model Card · **E-08 lineage** · E-09 kill switch · E-10 incerteza · **E-11 PII em prompt de LLM** · **E-12 derivado tratado como anônimo** · **E-13 dependência que exfiltra** |

**33 de 33.** O catálogo do plano está inteiro implementado — `checks_previstos`
sai vazio no laudo, e o campo continua lá: sumir com ele faria o consumidor
perder a diferença entre "nenhum pendente" e "esta versão nem sabe responder isso".

### Os quatro últimos: IA, cadeia de terceiros e rastreabilidade

Quatro buracos que os checks anteriores não viam. E-11, E-12 e E-13 carregam
**Art. 42** (responsabilidade solidária) junto da base específica — perante o
titular, quem escolheu o operador responde pelo que ele faz; E-08 o carrega
quando a trilha atravessa terceiro.

- **E-11** — E-05 e E-06 olham o *viés* do modelo; nenhum dos dois olha o que
  **entra** nele. Um prompt é transferência a terceiro, com o agravante de que
  o destino pode retê-lo para treino. Só suprime o achado uma chamada de
  redação que **executa**: `# TODO: redact` não redige nada.
- **E-12** — ataca a frase "não é dado pessoal, é só o hash". A pergunta não é
  se você exporta derivados, é se **o catálogo reconhece a origem como pessoal**.
  O silêncio do catálogo é a alegação de anonimato que ninguém assinou.
- **E-13** — S-04 ignora `node_modules`/`site-packages` por construção, senão o
  laudo vira ruído. O efeito colateral era um buraco inteiro: a dependência que
  um dia adicionou telemetria nunca aparece no manifesto, porque ninguém
  escreveu aquela URL. E-13 é o único check que entra nesses diretórios, e
  nomeia o pacote que trouxe o host.
- **E-08** — a pergunta que ninguém consegue responder depois de um incidente:
  *este dado veio de onde, passou por quê e foi parar aonde?* Exige o artefato
  de trilha (`lineage.jsonl` ou equivalente declarado) e confere que ele
  **alcança** as tabelas com dado pessoal — existir trilha não basta se ela não
  cobre o que existe. Um README afirmando rastreabilidade não conta.

## A matriz: pilar × domínio

Cada check declara também um **domínio** técnico. O pilar responde *que valor
está em jogo*; o domínio, *onde ele se manifesta no sistema*.

| | frontend | api | backend | data | ai |
|---|---|---|---|---|---|
| **privacy** | P-13 P-14 | P-05 P-07 P-09 P-10 P-11 | P-01 P-06 | P-02 P-03 P-04 P-07 P-08 P-09 | — |
| **security** | S-09 | S-01 S-02 S-03 S-07 | S-04 S-05 S-06 S-07 E-13* | S-05 S-08 | — |
| **ethics** | — | E-01 E-03 E-09 | E-02 E-04 E-11 E-13 | E-06 E-08 E-12 | E-00 E-01 E-02 E-04…E-12 |

<sub>* E-13 é do pilar ethics; a coluna mostra o estrato que ele examina.</sub>

```bash
pse --pilar privacy                 # o DPO, atravessando todos os estratos
pse --domain frontend               # o time de front, nos três pilares
pse --pilar privacy --domain data   # o cruzamento
```

Recorte que não alcança check nenhum é **exit 30**, não "conforme" — seria
verde por não ter olhado. `cobertura.por_dominio` mostra estrato com zero
checks como zero, em vez de omiti-lo.

## Os dois trabalhos

| Trabalho | Marcador | Checks |
|---|---|---|
| **B** — inventário estático (sem rede, agente pode disparar) | `--modo pse_inventory` | P-01/02/03/04/06/08 · S-04/05/06/08 · E-00/04/05/06/07/08/10/11/12/13 |
| **A passivo** — leitura com a própria identidade | `--modo pse_passive` | S-03 · E-01 · E-02 |
| **A ativo** — sonda de autorização, só `workflow_dispatch` | `--modo pse_active` | S-01 · S-02 · S-07 · P-05 · P-07 · P-09 · P-10 · P-11 · E-03 · E-09 |

O Trabalho A **não emite um byte** antes de a atestação passar: modo habilitado
→ atestação válida para este modo e este alvo → tokens no ambiente →
healthcheck. Atestação ausente, vencida, com escopo errado ou com
`target_fingerprint` de outro alvo deixa todos os checks A em
`checks_indeterminados` (exit 20) — nunca verde, nunca uma requisição.
`pse_active` contra `environment: production` é recusado (exit 30) antes até do
healthcheck. Contrato completo em `docs/COMO-ADOTAR.md` §5.

## Uso

```bash
pip install pse-suite            # no consumidor: via requirements-qa.txt (pin)
pse --path . --config tests/qa/pse-config.yaml --output harness/reports/laudo-pse.json
pse --path . --packs privacy     # um pacote por vez
```

## Veredito — três estados, nunca binário

Um check pulado nunca é indistinguível de um check verde, e "não consegui
auditar" nunca compartilha código de saída com "conforme".

| Código | Significado | Bloqueia? |
|---|---|---|
| `0` | conforme | não |
| `10` | violação com CRÍTICO | sim |
| `11` | violação com ALTO, sem CRÍTICO | política do CI do consumidor |
| `20` | indeterminado — a suite tentou e não conseguiu decidir | **sim, igual ao 10** |
| `30` | entrada inválida — path/config/catálogo/versão irresolvíveis | sim |

Precedência quando coexistem: `30 > 10 > 20 > 11 > 0`.

**Não existe flag que rebaixe o gate.** A suite reporta a verdade em códigos
distintos; a política "ALTO bloqueia em `main`, avisa em feature branch" vive no
CI do consumidor, declarativa e protegida por CODEOWNERS — onde o dono da
decisão é visível. Uma trava que o vigiado pode desligar em silêncio não é trava.

Três destinos possíveis para um check, todos visíveis no laudo:

- `checks_executados` — rodou e decidiu;
- `checks_pulados` — **N/A declarado**: a pré-condição declarativa não existe
  (sem manifesto de terceiros não há o que conferir em S-08). Não bloqueia, mas
  o motivo é obrigatório;
- `checks_indeterminados` — **tentei e não decidi**: fato não decidível
  estaticamente, arquivo ilegível, alvo caído, atestação inválida. Bloqueia;
- `checks_nao_habilitados` — **previsto e não pedido**: o consumidor não pediu
  Trabalho A, ou pediu num modo que não inclui este check. Não bloqueia;
- `checks_previstos` — **declarado no catálogo e ainda não implementado**.

## Thresholds: o consumidor aperta, nunca afrouxa

`k_anonymity_min` tem piso 5 e `dpd_max_delta` tem teto 0,10 — **na suite**.
Declarar fora da faixa não vira achado: vira recusa de execução (exit 30).
Achado o operador aprende a ignorar; recusa, não.

## Dois riscos que a própria auditoria carrega

**E-09 nunca aciona o kill switch de verdade.** Só envia a simulação, e o
parâmetro de dry-run é constante — não há ramo de código que o omita, nem
retentativa "sem dry-run" quando o alvo recusa. Alvo que não expõe simulação
vira indeterminado, que é infinitamente mais barato que descobrir o switch
funcionando porque a auditoria o puxou.

**E-06 nunca roda inferência.** Não carrega o dataset nem executa o modelo:
isso significaria processar dado sensível de titular real dentro de uma
ferramenta de auditoria, para produzir um número que o consumidor já tem. Ele
exige que a medição exista, esteja fresca (fingerprint do dataset) e traga as
condições — número sem condições de medição não entra.

## Laudo

Schema `laudo-pse-1.0` (`schemas/`), com bloco `artifact` de procedência:

```
suite · suite_version · schema_version · catalog_hash · repo_commit
· config_fingerprint · timestamp_utc
```

O `catalog_hash` cobre `pse/data/` **e** o código dos checks: dois laudos que
declaram a mesma `suite_version` mas divergem no hash foram produzidos por
réguas diferentes, e isso fica visível sem depender da palavra de ninguém.

A evidência é sanitizada com a própria régua antes de ser serializada — o laudo
não republica o CPF, o e-mail ou a chave que acabou de denunciar. O localizador
de um achado é `arquivo:linha`, nunca o literal.

## Versão

Fonte única: `pyproject.toml`. O laudo lê dos metadados do pacote instalado. A
suite **nunca fabrica** um número: versão irresolvível é ambiente quebrado
(exit 30), não `0.6.0-dev`.

## Autoprova — a régua obedece ao que receita

```bash
pse --self-test     # a trava desta versão instalada ainda morde?
pse --manifesto     # versão, catalog_hash, checks, resultado da autoprova
```

`--self-test` audita uma fixture **embarcada no wheel** e exige vermelho, e
roda a **mutação canônica** de cada check: a violação mínima que deve reprová-lo,
declarada como dado no catálogo. Check implementado sem mutação declarada
**reprova a si mesmo** — um check que nunca foi visto reprovando nada é uma
hipótese, não uma trava.

O consumidor roda isso no próprio CI, sem clonar este repositório. Se um check
parar de morder, o pipeline diz qual.

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest                    # inclui a mordida: prova que o gate aborta
pytest -m pse_privacy     # um pacote isolado
pytest -m mordida         # só os testes negativos
```

As fixtures são três, e as três importam:

| Fixture | Prova |
|---|---|
| `consumidor_ruim` | a suite acha o que existe |
| `consumidor_silencioso` | violação real + comentário citando o controle **não** fica verde — a âncora é o fato, não a menção |
| `consumidor_bom` | o controle correto **não** vira achado — falso-positivo em CRÍTICO ensina o operador a ignorar o laudo |
