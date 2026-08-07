# Testes da PSE Suite

> **Este documento e GERADO.** Nao edite: rode
> `python -m pse.testes > docs/TESTES.md`. A trava de CI regenera e
> compara a cada merge — divergiu, o merge nao abre.

A palavra *teste* cobre duas coisas nesta suite, e mistura-las e o erro
mais facil de cometer. A **Camada A** e o que a PSE audita num alvo; a
**Camada B** e o que prova que a Camada A funciona. A primeira e o
produto; a segunda e a garantia de que o produto nao mente.

| Camada | O que e | Quantidade | Onde vive | Contra quem roda |
|---|---|---|---|---|
| **A — Checks** | O que a PSE audita num alvo | **58** checks | `pse/checks/**` | O sistema auditado |
| **B — Testes** | O que prova que os checks funcionam | **674** funcoes / **745+** casos | `tests/**` | A propria PSE |

---

# Camada A — os 58 checks

## A.1 Como estao divididos

Quatro eixos ortogonais. Nenhum check e duplicado para servir a dois.

### Por pilar — que valor esta em jogo

O prefixo do ID codifica o pilar, sempre. Dominio e multivalorado e
vive em `domain`, nunca no prefixo.

| Pilar | Prefixo | Checks |
|---|---|---|
| ethics | `E-` | 14 |
| privacy | `P-` | 22 |
| security | `S-` | 22 |

### Por dominio — onde o risco se manifesta

E lista: 58 checks produzem 73 atribuicoes.

| Dominio | Checks |
|---|---|
| `api` | 16 |
| `backend` | 16 |
| `ai` | 15 |
| `data` | 15 |
| `frontend` | 11 |

### Por tipo — de onde vem o fato

| Tipo | Checks |
|---|---|
| `estatico` | 34 |
| `runtime` | 12 |
| `estatico+runtime` | 11 |
| `ci` | 1 |

### Por modo — quem pode disparar

O contrato de autorizacao: `inventory` nao toca rede, `passive` le
com a propria identidade, `active` sonda e exige revisores.

| Modo | Checks |
|---|---|
| `inventory` | 35 |
| `active` | 12 |
| `passive` | 11 |

### Desfechos possiveis

E o que distingue a suite de um linter: nem todo check termina em
verde ou achado.

| Desfecho | Quantos podem | O que significa |
|---|---|---|
| `CRITICO` | 15 | emitem a severidade que reprova fail-closed (exit 10) |
| `pulado` | 16 | pre-requisito declarado ausente, com motivo no laudo |
| `indeterminado` | 11 | tentou e nao decidiu — **bloqueia** (exit 20) |

Emitem `CRITICO`: `E-04`, `E-11`, `P-01`, `P-07`, `P-08`, `P-11`, `P-13`, `P-14`, `P-15`, `P-20`, `S-01`, `S-04`, `S-06`, `S-10`, `S-11`.

---

## A.2 Pacote P — Privacidade (22)

| ID | Dominio | Tipo / Modo | Severidade | Desfechos | O que faz |
|---|---|---|---|---|---|
| **P-01** | backend | estatico / inventory | ALTO, CRITICO | — | dado pessoal em log sem mascaramento. |
| **P-02** | data | estatico / inventory | ALTO | pula | retencao declarada no catalogo sem job de eliminacao. |
| **P-03** | data | estatico / inventory | ALTO | — | o "apagado" que continua la. |
| **P-04** | data | estatico / inventory | ALTO, MEDIO | — | catalogo vivo de dados. |
| **P-05** | api | estatico+runtime / active | ALTO | — | minimizacao: campo fora da allowlist deve ser rejeitado. |
| **P-06** | backend | estatico / inventory | — | — | a chave de pseudonimizacao morando junto do dado que ela protege. |
| **P-07** | api, data | estatico+runtime / active | ALTO, CRITICO | indetermina, nao-habilitado | consentimento granular por finalidade, opt-in, com registro. |
| **P-08** | data | estatico / inventory | CRITICO | pula | dado sensivel apoiado em legitimo interesse. |
| **P-09** | data, api | estatico+runtime / active | ALTO | nao-habilitado | k-anonimato em agregacoes. |
| **P-10** | api | runtime / active | ALTO | — | portabilidade: exportacao existe, responde e vem integra. |
| **P-11** | api | estatico+runtime / active | CRITICO | — | oraculo de existencia: 403 e 404 distinguiveis. |
| **P-13** | frontend | estatico / inventory | CRITICO | — | controle de consentimento que nasce ligado. |
| **P-14** | frontend | estatico / inventory | CRITICO | — | dado pessoal no armazenamento do navegador ou na URL. |
| **P-15** | ai | estatico / inventory | ALTO, CRITICO | indetermina, pula | dado pessoal virando feature de treino sem finalidade declarada. |
| **P-16** | ai | estatico / inventory | ALTO | pula | dataset de treino sem governanca declarada. |
| **P-17** | api | estatico / inventory | ALTO | — | discriminacao sem modelo nenhum: o filtro da busca. |
| **P-18** | backend, data | estatico / inventory | ALTO | indetermina, pula | dado sensivel no banco em texto claro. |
| **P-19** | backend, data | estatico / inventory | ALTO | pula | o Art. 18 VI num registro que nao apaga. |
| **P-20** | data | estatico / inventory | ALTO, CRITICO | — | o "anonimo" que nao e anonimo. |
| **P-22** | frontend | runtime / passive | ALTO | — | o consentimento como ele e OBSERVADO, nao como esta declarado. |
| **P-23** | frontend | runtime / passive | ALTO | — | PII na URL, vista no HTML que o alvo de fato entregou. |
| **P-24** | frontend | runtime / passive | ALTO | — | o que o arquivo publicado revela alem do que servia para servir. |

## A.3 Pacote S — Seguranca (22)

| ID | Dominio | Tipo / Modo | Severidade | Desfechos | O que faz |
|---|---|---|---|---|---|
| **S-01** | api | estatico+runtime / active | CRITICO | indetermina | BOLA/IDOR: recurso de titular acessivel por outro titular. |
| **S-02** | api | runtime / active | ALTO | — | rate limit ausente: extracao em massa possivel. |
| **S-03** | api | estatico+runtime / passive | ALTO | — | payload de erro carregando dado pessoal. |
| **S-04** | backend | estatico / inventory | ALTO, CRITICO | — | host externo no codigo que o manifesto de terceiros nao declara. |
| **S-05** | backend, data | estatico+runtime / active | ALTO | pula | payload minimo de egresso: o que sai para cada terceiro. |
| **S-06** | backend | estatico / inventory | ALTO, CRITICO | — | credencial de parceiro hardcoded. |
| **S-07** | api, backend | estatico+runtime / active | ALTO | — | propagacao de finalidade (X-Purpose) + log de auditoria estruturado. |
| **S-08** | data, backend | estatico / inventory | ALTO | pula | destino fora do Brasil sem base de transferencia declarada. |
| **S-09** | frontend | estatico / inventory | ALTO | — | token de sessao vivendo no cliente. |
| **S-10** | ai | estatico / inventory | CRITICO | — | o que ENTRA no modelo: injecao de prompt, nos tres vetores. |
| **S-11** | ai | estatico / inventory | CRITICO | — | o que SAI do modelo chegando a sink perigoso sem validacao. |
| **S-12** | api | estatico / inventory | ALTO | indetermina, pula | a ontologia do contrato: declarada, e implementada. |
| **S-13** | api | estatico / inventory | ALTO | — | o erro como canal de saida: pilha, caminho e versao. |
| **S-14** | backend | estatico / inventory | ALTO | — | o dump de producao pousando num ambiente inferior. |
| **S-15** | backend, data | estatico / inventory | ALTO | — | a role do banco: minimizacao decidida uma vez, herdada para sempre. |
| **S-16** | backend | estatico / inventory | ALTO | pula | residencia de dados no ponto de ESCRITA, nao no de egresso. |
| **S-17** | frontend | runtime / passive | ALTO | — | o cookie de sessao como o navegador o recebeu. |
| **S-18** | frontend | runtime / passive | ALTO | pula | o terceiro que a PAGINA contactou, contra o que o manifesto declara. |
| **S-19** | frontend | runtime / passive | ALTO | — | o que o servidor DECLAROU na resposta, e o que trafegou em claro. |
| **S-20** | frontend | runtime / passive | por tipo | indetermina | credencial servida ao navegador. Par dinamico de P-06. |
| **S-21** | frontend | runtime / passive | MEDIO | — | o bundle que aponta para o proprio codigo-fonte. |
| **S-22** | api | estatico+runtime / active | ALTO | indetermina, nao-habilitado, pula | a finalidade chega, e nada a amarra a uma base legal. |

## A.4 Pacote E — Etica (14)

| ID | Dominio | Tipo / Modo | Severidade | Desfechos | O que faz |
|---|---|---|---|---|---|
| **E-00** | ai | estatico / inventory | ALTO | pula | guarda de escopo do pacote de Etica (o EBD-000 do plano v1). |
| **E-01** | ai, api | estatico+runtime / passive | ALTO | — | decisao automatizada sem explicacao. |
| **E-02** | ai, backend | estatico+runtime / passive | ALTO | — | decision log estruturado. |
| **E-03** | api | runtime / active | ALTO | — | contestacao: o recurso existe e devolve protocolo e prazo. |
| **E-04** | ai, backend | estatico / inventory | CRITICO | — | decisao critica sem rota de revisao humana. |
| **E-05** | ai | estatico / inventory | ALTO | — | variavel proxy de discriminacao no score, sem ajuste de fairness. |
| **E-06** | ai, data | ci / inventory | ALTO | indetermina | drift de disparidade por grupo contra o baseline. |
| **E-07** | ai | estatico / inventory | ALTO | — | Model Card e Datasheet: presentes, versionados e validos. |
| **E-08** | data | estatico / inventory | ALTO | indetermina, pula | provenance/lineage: origem → transformacao → destino rastreavel. |
| **E-09** | ai, api | runtime / active | ALTO | indetermina | kill switch existe, e testavel, e o teste NAO o aciona. |
| **E-10** | ai | estatico / inventory | MEDIO | — | decisao pontual sem incerteza quantificada. |
| **E-11** | ai, backend | estatico / inventory | CRITICO | — | dado pessoal cru entrando em prompt de modelo de linguagem. |
| **E-12** | ai, data | estatico / inventory | ALTO | indetermina, pula | embedding/hash exportado como se fosse anonimo. |
| **E-13** | backend | estatico / inventory | ALTO | pula | host que sai de dentro de uma dependencia (o terceiro-do-terceiro). |

---

# Camada B — os 674 testes da suite

34 arquivos com teste (10427 linhas), mais 2 auxiliares (`conftest.py`, `helpers_alvo.py`). Divididos por **familia de garantia**, nao por ordem alfabetica.

## B.1 As familias

| Familia | Arquivos | Funcoes | Casos |
|---|---|---|---|
| Um arquivo por pacote de checks | 8 | 223 | 243 |
| Camada dinamica — o navegador | 4 | 101 | 114 |
| Contrato e autorizacao | 4 | 68 | 84 |
| Cobertura honesta | 3 | 54 | 59 |
| A regua e o catalogo (D-13) | 4 | 68 | 75 |
| Provas negativas — o gate tem de morder | 6 | 91 | 91 |
| O conserto medido contra alvos reais | 3 | 32 | 38 |
| Integracao de ponta a ponta | 2 | 37 | 41 |

## B.2 Um arquivo por pacote de checks — 223 funcoes

Cada estrato tecnico tem o seu: o teste vive perto do check que prova.

| Arquivo | Fn | Casos | Marcadores | O que garante |
|---|---|---|---|---|
| `test_api_estrato.py` | 38 | 38 | `mordida`, `pse_api`, `pse_privacy`, `pse_security` | S-12, P-17, S-13 — o pacote fundador do estrato de API. |
| `test_backend_estrato.py` | 38 | 38 | `mordida`, `pse_backend`, `pse_privacy`, `pse_security` | S-14, S-15, P-18, P-19, S-16 — o pacote fundador do estrato de backend. |
| `test_data_estrato.py` | 22 | 22 | `mordida`, `pse_data`, `pse_privacy` | P-20 — o fundador do estrato `data`, e a decisão sobre P-21. |
| `test_frontend.py` | 18 | 28 | `mordida`, `parametrize`, `pse_frontend` | P-13, P-14, S-09 — o domínio frontend, ancorado em AST de verdade. |
| `test_ia_estrato.py` | 31 | 36 | `mordida`, `parametrize`, `pse_ai`, `pse_privacy`, `pse_security` | S-10, S-11, P-15, P-16 — os dois buracos de IA que a matriz expôs. |
| `test_ia_terceiros.py` | 16 | 21 | `mordida`, `parametrize`, `pse_ethics` | E-11, E-12, E-13 — IA e a cadeia de terceiros que os checks anteriores nao veem. |
| `test_lineage.py` | 14 | 14 | `mordida`, `pse_ethics` | E-08 — provenance/lineage: origem → transformação → destino rastreável. |
| `test_rust.py` | 46 | 46 | — | O alcance textual ancorado a Rust — S-06, P-18, P-19, S-16. |

## B.3 Camada dinamica — o navegador — 101 funcoes

O que so existe com a aplicacao no ar. `NetworkLog` fabricado verde nao prova observacao, e por isso o motor e testado antes dos checks.

| Arquivo | Fn | Casos | Marcadores | O que garante |
|---|---|---|---|---|
| `test_dinamico.py` | 30 | 33 | `mordida`, `parametrize`, `pse_dinamico`, `pse_navegador`, `pse_privacy`, `pse_security` | P-22, S-17, P-23 — os três fundadores da camada dinâmica. |
| `test_dinamico_fase2.py` | 32 | 32 | `mordida`, `pse_dinamico`, `pse_navegador`, `pse_privacy`, `pse_security` | S-18, S-19, S-20, P-24, S-21 — o resto do passivo, portado da qa-suite. |
| `test_navegador.py` | 20 | 30 | `mordida`, `parametrize`, `pse_dinamico`, `pse_navegador` | O MOTOR da camada dinâmica — antes de qualquer check existir. |
| `test_superficie_dinamica.py` | 19 | 19 | — | A camada dinamica observa UMA superficie, e o laudo tem de dizer qual. |

## B.4 Contrato e autorizacao — 68 funcoes

O que a suite promete ao consumidor, e o que ela promete ao ALVO: passivo que emita uma requisicao a mais reprova.

| Arquivo | Fn | Casos | Marcadores | O que garante |
|---|---|---|---|---|
| `test_alvo_local.py` | 6 | 12 | `parametrize` | Os dois defeitos que so o primeiro alvo local VIVO revelou. |
| `test_contrato.py` | 18 | 18 | `mordida` | D-04, D-05, D-06, D-07 — o contrato com o consumidor. |
| `test_trabalho_a.py` | 28 | 38 | `mordida`, `parametrize`, `pse_ethics`, `pse_privacy`, `pse_security` | Fase 2 — Trabalho A. O teste que mais importa e o que conta requisicoes. |
| `test_trabalho_b.py` | 16 | 16 | `mordida`, `pse_ethics`, `pse_privacy`, `pse_security` | Trabalho B contra fixture com violacoes + contrato de veredito. |

## B.5 Cobertura honesta — 54 funcoes

A fachada e o inimigo: os estados nao colapsam, `pulado` nao vira auditado, arquivo ilegivel nao apaga o veredito dos demais.

| Arquivo | Fn | Casos | Marcadores | O que garante |
|---|---|---|---|---|
| `test_cobertura.py` | 29 | 29 | `skipif` | O mapa de cobertura tem de reprovar exatamente o defeito que ele existe |
| `test_cobertura_web.py` | 15 | 20 | `parametrize` | O estrato web e a maior fatia do alvo — e um arquivo ilegivel apagava o |
| `test_html_no_alcance.py` | 10 | 10 | — | HTML era `IRRELEVANTE`, e isso escondia egresso a terceiro. |

## B.6 A regua e o catalogo (D-13) — 68 funcoes

Lista curada mora em `pse/data/`, nunca no `.py` do check e nunca copiada ao consumidor; e nao muda em silencio.

| Arquivo | Fn | Casos | Marcadores | O que garante |
|---|---|---|---|---|
| `test_catalogo.py` | 10 | 10 | `pse_ethics` | D-12 (catalogo dos 29) + E-00 (guarda de escopo do pack de etica). |
| `test_dominio.py` | 19 | 25 | `mordida`, `parametrize` | A matriz: pilar × domínio. |
| `test_regua.py` | 35 | 35 | `parametrize` | D-13 — a regua curada e vigiada. |
| `test_versao.py` | 4 | 5 | `parametrize` | Gap 5 — a versao tem UMA fonte, e ninguem a restata em silencio. |

## B.7 Provas negativas — o gate tem de morder — 91 funcoes

Check que nunca foi visto reprovando nada e hipotese, nao trava.

| Arquivo | Fn | Casos | Marcadores | O que garante |
|---|---|---|---|---|
| `test_indice.py` | 34 | 34 | `mordida` | A TRAVA — documentação de testes obrigatória, conferida a cada merge. |
| `test_mordida.py` | 9 | 9 | `mordida`, `pse_ethics` | Os repo-provas do Relatorio de Validacao, virados testes permanentes. |
| `test_mutacao.py` | 5 | 5 | `mordida`, `parametrize` | Gap 4 — prova de mutacao: todo check bloqueante tem inverso canonico. |
| `test_orfao.py` | 4 | 4 | `mordida` | A trava de check-órfão — todo check catalogado é exercitado por um teste. |
| `test_ratificacao.py` | 35 | 35 | `mordida`, `pse_privacy`, `pse_security` | As quinze ratificações, seladas pelo COMPORTAMENTO e não pela prosa. |
| `test_reprodutibilidade.py` | 4 | 4 | `mordida`, `skipif` | A fixture tem de existir no REPOSITORIO, não só no disco de quem a escreveu. |

## B.8 O conserto medido contra alvos reais — 32 funcoes

Os tres refinos que a rodada de reconhecimento contra 6 repositorios de fintech e legaltech expos — defeitos da PROPRIA suite que nenhuma fixture pegaria, e que nenhum deles teria aparecido sem alvo de verdade.

| Arquivo | Fn | Casos | Marcadores | O que garante |
|---|---|---|---|---|
| `test_conserto_alcance.py` | 11 | 11 | `mordida`, `pse_privacy`, `pse_security` | D-01 do conserto — `.tsx` e `.jsx` saem da invisibilidade. |
| `test_conserto_dominio.py` | 10 | 16 | `mordida`, `parametrize`, `pse_privacy` | S-02 do conserto — a régua deixa de dizer duas coisas opostas. |
| `test_conserto_severidade.py` | 11 | 11 | `mordida`, `pse_security` | S-01 do conserto — credencial em caminho de teste rebaixa, e não some. |

## B.9 Integracao de ponta a ponta — 37 funcoes

A regua contra um sistema de verdade, e os riscos que so aparecem quando as pecas correm juntas.

| Arquivo | Fn | Casos | Marcadores | O que garante |
|---|---|---|---|---|
| `test_aceite.py` | 12 | 14 | `mordida`, `parametrize`, `pse_aceite` | O teste de aceite: a régua contra um sistema de verdade. |
| `test_fase3.py` | 25 | 27 | `mordida`, `parametrize`, `pse_ethics`, `pse_privacy`, `pse_security` | Fase 3 — os dois riscos novos, e os testes que os medem. |

## B.10 Marcadores

Selecao por eixo, declarada em `pyproject.toml`. Marcador em uso e
nao declarado la reprova o proprio pytest.

| Marcador | O que seleciona | Arquivos que o usam |
|---|---|---|
| `mordida` | testes negativos que provam que o gate aborta | `test_aceite.py`, `test_api_estrato.py`, `test_backend_estrato.py`, `test_conserto_alcance.py`, `test_conserto_dominio.py`, `test_conserto_severidade.py`, `test_contrato.py`, `test_data_estrato.py`, `test_dinamico.py`, `test_dinamico_fase2.py`, `test_dominio.py`, `test_fase3.py`, `test_frontend.py`, `test_ia_estrato.py`, `test_ia_terceiros.py`, `test_indice.py`, `test_lineage.py`, `test_mordida.py`, `test_mutacao.py`, `test_navegador.py`, `test_orfao.py`, `test_ratificacao.py`, `test_reprodutibilidade.py`, `test_trabalho_a.py`, `test_trabalho_b.py` |
| `pse_aceite` | teste de aceite contra alvo REAL (pula se o alvo nao existe) | `test_aceite.py` |
| `pse_ai` | dominio ai (modelo e decisao automatizada) | `test_ia_estrato.py` |
| `pse_api` | dominio api (borda e contrato) | `test_api_estrato.py` |
| `pse_backend` | dominio backend (servico e integracao) | `test_backend_estrato.py` |
| `pse_data` | dominio data (catalogo, retencao, agregacao) | `test_data_estrato.py` |
| `pse_dinamico` | camada dinamica (Trabalho A por navegador) | `test_dinamico.py`, `test_dinamico_fase2.py`, `test_navegador.py` |
| `pse_ethics` | checks do pacote E (Etica) | `test_catalogo.py`, `test_fase3.py`, `test_ia_terceiros.py`, `test_lineage.py`, `test_mordida.py`, `test_trabalho_a.py`, `test_trabalho_b.py` |
| `pse_frontend` | dominio frontend (interface e cliente) | `test_frontend.py` |
| `pse_navegador` | exige Playwright e binario de navegador instalados | `test_dinamico.py`, `test_dinamico_fase2.py`, `test_navegador.py` |
| `pse_privacy` | checks do pacote P (Privacidade) | `test_api_estrato.py`, `test_backend_estrato.py`, `test_conserto_alcance.py`, `test_conserto_dominio.py`, `test_data_estrato.py`, `test_dinamico.py`, `test_dinamico_fase2.py`, `test_fase3.py`, `test_ia_estrato.py`, `test_ratificacao.py`, `test_trabalho_a.py`, `test_trabalho_b.py` |
| `pse_security` | checks do pacote S (Seguranca) | `test_api_estrato.py`, `test_backend_estrato.py`, `test_conserto_alcance.py`, `test_conserto_severidade.py`, `test_dinamico.py`, `test_dinamico_fase2.py`, `test_fase3.py`, `test_ia_estrato.py`, `test_ratificacao.py`, `test_trabalho_a.py`, `test_trabalho_b.py` |

Embutidos do pytest, que aparecem na arvore mas nao sao eixo de
selecao desta suite: `parametrize`, `skipif`.

---

# A ponte — todo check tem teste

Um documento que lista checks e testes sem provar que os segundos
cobrem os primeiros e meia-garantia. O indice
(`docs/INDICE-DE-TESTES.md`) faz a ligacao check a check, e
`tests/test_indice.py` **reprova o merge** que introduzir um check
sem teste — ou um teste citando check que nao existe.

| Situacao | Hoje | O que acontece se mudar |
|---|---|---|
| Checks cobertos por teste | 58 de 58 | check orfao reprova a trava |
| Referencias a check inexistente | 0 | referencia fantasma reprova a trava |
| Excecoes declaradas (`CHECKS_FORA_DO_CATALOGO`) | 3 | excecao calada reprova; declarada, aparece no indice |

---

# O que NAO esta testado

Esta secao e gerada do estado real, e isso e o ponto. Uma doc
obrigatoria que so listasse o que tem cobertura seria propaganda —
e omitir lacuna e exatamente a cobertura de fachada que a suite
cobra dos alvos.

- **Nenhuma linguagem de servidor alem de Python tem parser** — **LACUNA ABERTA**. A suite nomeia mas nao le: C, C#, C++, C/C++, Dart, Elixir, Erlang, Go, Gradle, HCL, Java, Kotlin, Lua, Objective-C, PHP, Perl, Protobuf, R, Ruby, Scala, Svelte, Swift, TOML, Terraform, Vue. Alcance parcial declarado: Rust (somente S-06, P-18, P-19, S-16). Ausencia de achado nessas linguagens nao e atestado de conformidade — e ausencia de leitura.
- **Nao ha mecanismo de exclusao de caminho declaravel** — **LACUNA ABERTA**. O unico filtro e a lista fixa `scan.IGNORAR_DIRS` (`.git`, `.mypy_cache`, `.pytest_cache`, `.venv`, `__pycache__`, `build`, `dist`, `node_modules`, `venv`). O consumidor nao pode declarar caminho fora de escopo, e o autoscan da propria suite conta as fixtures de teste como achado. Fechar a lacuna exige que a exclusao seja DECLARADA e CONTADA no laudo — filtro silencioso seria a cobertura de fachada de volta pela porta dos fundos.
- **IDs deliberadamente ausentes da sequencia do catalogo** — **LACUNA ABERTA**. Sem entrada no catalogo: `P-12`, `P-21`. Buraco honesto e melhor que check que nao verifica nada real — mas so quando o buraco esta escrito.
- **Vetores reais deliberadamente nao implementados** — **LACUNA ABERTA**. Investigados e assinados em `docs/BURACOS-ASSUMIDOS.md` porque o check possivel verificaria a fachada, nao o direito: Zona bruta de data lake sem restrição (`P-21`) — Não há artefato versionado que distinga a zona bruta restrita da irrestrita: a decisão vive em IAM e em política de bucket, fora do repositório (desde v0.9.0); Endpoint de acesso do titular (Art. 18 II) — *"O endpoint existe"* é fraco e *"responde em tempo hábil, com o dado certo, para o titular certo"* é o que a lei pede — e isso não é verificável estaticamente nem por sonda sem impersonar um titular real (desde v0.19.0); Efeito downstream de revogação (Art. 18 IX) — Revogar consentimento tem de parar o processamento **em todos os sistemas a jusante** — filas, réplicas, data lake, parceiros. É comportamento distribuído: nenhum repositório contém a prova, e observar o efeito exigiria acesso a sistemas que não são o alvo (desde v0.19.0)
- **Pendencias de ratificacao ainda abertas** — **LACUNA ABERTA**. Apontar o repositório do `global-ingress` — confirmado versionado e compartilhado por vários projetos; falta o nome (desde v0.17.0); Medir `/dev` no arranjo real (imagem Docker, origem compartilhada) (desde v0.15.1); A gramática dos 3 arquivos `.ts`/`.tsx` servidos (desde v0.15.0); Identidade dos SHAs do cockpit (`d6ae70ea` / `1da4d51`) (desde v0.13.0); O btv declarar `tests/qa/catalog.yaml` (habilita P-18) (desde v0.14.1); O btv declarar `data_residency` (habilita S-16) (desde v0.14.1); **A-01** — `reconcilia` persiste ou loga PAN completo? Bloqueia o check de PAN (desde v0.20.0); **A-02** — `LLM_PROVIDER` de `juridico-platform` em produção é `openai` ou `ollama`? Bloqueia o refino de sigilo em E-11 (desde v0.20.0); **D-07** — introduzir `llm_egress: external\ (desde local` no config, com omissão → INDETERMINADO?)
- **Parametrizacoes que este documento nao consegue contar** — **LACUNA ABERTA**. Os argvalues sao computados em tempo de execucao, entao o numero de casos destas funcoes nao entra na contagem: `test_aceite.py::test_aceite_declara_o_minimo`; `test_aceite.py::test_aceite_roda_ou_fica_pendente_com_motivo`; `test_mutacao.py::test_mutacao_canonica_reprova`; `test_regua.py::test_piso_da_regua_intacto`. O total de casos declarado abaixo e portanto um PISO, nao o numero que o pytest coleta.
- **Checks sem teste que os cubra (orfaos)** — fechada. Nenhum — a trava do indice reprova o merge que introduzir o primeiro.
- **Checks implementados sem mutacao canonica declarada** — fechada. Nenhum — todo check implementado declara no catalogo a violacao minima que deve produzir vermelho.
- **Checks sem docstring de modulo** — fechada. Nenhum — a descricao de todos eles sai do proprio modulo.
- **Checks previstos no catalogo e ausentes nesta versao** — fechada. Nenhum — os 58 catalogados estao implementados.


<!-- fim-do-corpo-comparado -->

> Tudo acima desta marca e comparado byte a byte pela trava de CI.
> O que vier abaixo dela e volatil de proposito e nao reprova merge.

- pacote: `pse-suite 0.20.0`
- regenerar: `python -m pse.testes > docs/TESTES.md`
- regenerar indice: `python -m pse.testes --indice > docs/INDICE-DE-TESTES.md`
