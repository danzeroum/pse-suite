# Matriz pilar x dominio — os 43 checks

> **Gerado**, nunca escrito a mao: `python -m pse.matriz > docs/matriz-dominio.md`.
> Ha teste que reprova se este arquivo divergir do catalogo — um mapa
> errado e pior que mapa nenhum, porque parece confiavel.

Duas dimensoes ortogonais. O **pilar** responde *que valor esta em jogo*;
o **dominio**, *onde ele se manifesta no sistema*. O prefixo do ID codifica
o pilar — a unica das duas que e univalorada; o dominio e lista, porque
um check pode examinar mais de um estrato.

## Grade

| | frontend | api | backend | data | ai | total no pilar |
|---|---|---|---|---|---|---|
| **privacy** | P-13 P-14 | P-05 P-07 P-09 P-10 P-11 P-17 | P-01 P-06 | P-02 P-03 P-04 P-07 P-08 P-09 | P-15 P-16 | 16 |
| **security** | S-09 | S-01 S-02 S-03 S-07 S-12 S-13 | S-04 S-05 S-06 S-07 S-08 | S-05 S-08 | S-10 S-11 | 13 |
| **ethics** | **—** | E-01 E-03 E-09 | E-02 E-04 E-11 E-13 | E-06 E-08 E-12 | E-00 E-01 E-02 E-04 E-05 E-06 E-07 E-09 E-10 E-11 E-12 | 14 |
| **total no dominio** | 3 | 15 | 11 | 11 | 15 | 43 |

A soma da ultima linha (55) e maior que 43 porque um check aparece em
mais de uma coluna quando examina mais de um estrato. Nao e erro de contagem:
e a multiplicidade do dominio, que e exatamente a razao de ele nao caber
no prefixo do ID.

## Buracos

Celula vazia nao e defeito por definicao — e pergunta. O que nao pode e ficar
sem resposta: cada uma abaixo precisa de um *nao se aplica* ou de um
*falta check*, assinado.

| Pilar x dominio | Leitura |
|---|---|
| `ethics` x `frontend` | **Falta check.** O material de fundacao tem farto insumo aqui — dark pattern, recusar mais dificil que aceitar, desinformacao de interface. Ficou fora do pacote fundador de proposito: exige julgamento, e AST sozinha nao decide se um botao e coercitivo. |

### Buracos ja fechados

Ficam registrados: e a historia que mostra o mapa cumprindo a funcao — a
celula vazia virou pergunta, e a pergunta virou check.

| Pilar x dominio | Como foi fechado |
|---|---|
| `privacy` x `ai` | Existia so de rabo de olho, via ethics. Fechado por **P-15** (dado pessoal como feature de treino sem finalidade declarada) e **P-16** (dataset de treino sem governanca). |
| `security` x `ai` | Estava vazio. Fechado por **S-10** (injecao de prompt: instrucao concatenada, caractere invisivel, token flooding) e **S-11** (saida do modelo em sink perigoso). Nasceram olhando o estrato. |

## Densidade por dominio

O numero sozinho engana: o que interessa e se o check NASCEU do estrato ou
foi etiquetado depois. Densidade por heranca nao e cobertura — e um numero
que engana quem le o mapa.

| Dominio | Checks | Leitura |
|---|---|---|
| `frontend` | 3 | Unico dominio cujos checks foram desenhados OLHANDO para ele. Os tres nasceram do estrato. |
| `api` | 15 | **S-12, P-17 e S-13 nasceram do estrato** — do contrato, do filtro de busca e do payload de erro. Os demais continuam sendo classificacao a posteriori: vieram do Trabalho A e do inventario e foram etiquetados depois. Era a leitura critica que a propria matriz fazia deste dominio, e ela deixou de valer para o pacote fundador. |
| `backend` | 11 | A posteriori. Sao os estaticos do inventario, reclassificados. |
| `data` | 11 | A posteriori, mas o mais coerente dos quatro herdados: catalogo, retencao, k-anonimato e lineage sao genuinamente do estrato de dados. |
| `ai` | 15 | Os quatro mais novos (S-10, S-11, P-15, P-16) nasceram do estrato; os demais foram etiquetados a posteriori. Primeiro dominio herdado a receber checks proprios. |

## Os 43, um por linha

| Check | Pilar | Dominio(s) | Titulo |
|---|---|---|---|
| `E-00` | ethics | ai | Escopo do pack de etica (guarda) — ha decisao automatizada sobre pessoas? |
| `E-01` | ethics | ai, api | Decisao automatizada sem explicacao (motivo/fatores/reason_code) |
| `E-02` | ethics | ai, backend | Decision log estruturado (modelo_v, features, score, limiar, revisor) |
| `E-03` | ethics | api | Contestacao — endpoint de recurso com protocolo e SLA |
| `E-04` | ethics | ai, backend | HITL — decisoes criticas com rota de revisao humana |
| `E-05` | ethics | ai | Proxy de discriminacao — feature proibida no pipeline |
| `E-06` | ethics | ai, data | Drift de disparidade — DPD por grupo vs baseline |
| `E-07` | ethics | ai | Model Card + Datasheet presentes, versionados e validos |
| `E-08` | ethics | data | Provenance/lineage — origem, transformacao e destino rastreaveis |
| `E-09` | ethics | ai, api | Kill switch / modo degradado digno, documentado e testavel |
| `E-10` | ethics | ai | Incerteza quantificada em decisoes pontuais |
| `E-11` | ethics | ai, backend | PII em prompt de LLM sem redacao |
| `E-12` | ethics | ai, data | Embedding/hash exportado como se fosse anonimo |
| `E-13` | ethics | backend | Dependencia com host nao declarado no manifesto |
| `P-01` | privacy | backend | PII em logs/prints sem mascaramento |
| `P-02` | privacy | data | Retencao declarada sem job de purga |
| `P-03` | privacy | data | Soft-delete sem eliminacao fisica / crypto-shredding |
| `P-04` | privacy | data | Catalogo vivo de dados |
| `P-05` | privacy | api | Minimizacao por jornada — DTO rejeita campo fora da allowlist |
| `P-06` | privacy | backend | Pseudonimizacao com chave segregada |
| `P-07` | privacy | api, data | Consentimento granular por finalidade, opt-in, com registro |
| `P-08` | privacy | data | Dado sensivel nunca com base legal legitimo interesse |
| `P-09` | privacy | data, api | k-anonimato em agregacoes de BI |
| `P-10` | privacy | api | Portabilidade — endpoint de exportacao existe e responde |
| `P-11` | privacy | api | Oraculo de existencia — 403 vs 404 distinguivel |
| `P-13` | privacy | frontend | Controle de consentimento pre-marcado |
| `P-14` | privacy | frontend | PII no armazenamento do cliente ou na URL |
| `P-15` | privacy | ai | Dado pessoal como feature de treino sem finalidade declarada |
| `P-16` | privacy | ai | Dataset de treino sem governanca declarada |
| `P-17` | privacy | api | Endpoint de busca aceita filtro sensivel sem bloqueio |
| `S-01` | security | api | BOLA/IDOR — recurso de titular sem assertOwnership |
| `S-02` | security | api | Rate limit + paginacao por cursor (anti-extracao em massa) |
| `S-03` | security | api | Erros e webhooks sem PII no payload |
| `S-04` | security | backend | Manifesto de terceiros — host externo registrado com DPA |
| `S-05` | security | backend, data | Payload minimo de egresso — schema por destino, PII proibida |
| `S-06` | security | backend | Chave por parceiro — nenhuma API key global/hardcoded |
| `S-07` | security | api, backend | Propagacao de finalidade (X-Purpose) + log de auditoria estruturado |
| `S-08` | security | data, backend | Transferencia internacional exige base declarada no manifesto |
| `S-09` | security | frontend | Token sensivel persistido no cliente |
| `S-10` | security | ai | Injecao de prompt (instrucao, invisivel, flooding) |
| `S-11` | security | ai | Saida do modelo em sink perigoso sem validacao |
| `S-12` | security | api | Ontologia x-ethics ausente ou nao implementada no contrato |
| `S-13` | security | api | Resposta de erro expoe pilha, caminho ou versao interna |

Todo check tem ao menos um dominio, e todo prefixo corresponde ao pilar —
as duas coisas sao verificadas em `tests/test_dominio.py`.
