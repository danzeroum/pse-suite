# Matriz pilar x dominio — os 52 checks

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
| **privacy** | P-13 P-14 P-22 P-23 | P-05 P-07 P-09 P-10 P-11 P-17 | P-01 P-06 P-18 P-19 | P-02 P-03 P-04 P-07 P-08 P-09 P-18 P-19 P-20 | P-15 P-16 | 21 |
| **security** | S-09 S-17 | S-01 S-02 S-03 S-07 S-12 S-13 | S-04 S-05 S-06 S-07 S-08 S-14 S-15 S-16 | S-05 S-08 S-15 | S-10 S-11 | 17 |
| **ethics** | **—** | E-01 E-03 E-09 | E-02 E-04 E-11 E-13 | E-06 E-08 E-12 | E-00 E-01 E-02 E-04 E-05 E-06 E-07 E-09 E-10 E-11 E-12 | 14 |
| **total no dominio** | 6 | 15 | 16 | 15 | 15 | 52 |

A soma da ultima linha (67) e maior que 52 porque um check aparece em
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

### Risco investigado e fora de escopo estatico

Distinto de celula vazia: aqui ha check POSSIVEL em tese, e a decisao foi
que ele nao seria verificavel de verdade neste artefato. Fica assinado
porque *nao implementei* e *nao existe risco* sao coisas opostas — e so a
segunda seria mentira.

| Dominio x risco | Decisao |
|---|---|
| `data` x `zona_bruta` | **P-21 — zona bruta de data lake com acesso irrestrito. Investigado, NAO implementado.** Tres razoes, nesta ordem. (1) A identificacao da zona bruta viria do NOME do bucket (`raw`, `bronze`, `landing`): isso e mencao, nao fato, e o D-01 proibe exatamente esse atalho — num check cuja consequencia seria bloquear CI. (2) Uma policy sem `Condition` no Terraform nao e violacao por si: a restricao pode viver numa SCP, num permission boundary, num grant de Lake Formation ou no provedor de identidade, todos FORA do repositorio. O check acusaria setup correto — o D-08 ao contrario. (3) A suite nao tem parser de HCL, e adicionar um para avaliar uma forma de politica que nao se consegue decidir seria construir a aparencia de cobertura. **O que faria P-21 nascer:** um artefato de policy-as-code versionado que declare finalidade e expiracao por zona — ai ha declaracao a confrontar com fato, que e como todos os outros funcionam. Buraco honesto e melhor que check que nao verifica nada real. |

## Densidade por dominio

O numero sozinho engana: o que interessa e se o check NASCEU do estrato ou
foi etiquetado depois. Densidade por heranca nao e cobertura — e um numero
que engana quem le o mapa.

| Dominio | Checks | Leitura |
|---|---|---|
| `frontend` | 6 | Primeiro dominio cujos checks foram desenhados OLHANDO para ele (P-13, P-14, S-09 nasceram do estrato) e o UNICO auditado nas duas camadas: **P-22, S-17 e P-23 sao dinamicos** — carregam a pagina num navegador e observam o que so o navegador ve. E aqui que contrato e observacao se encontram, e por isso e aqui que moram os pares de correlacao estatico x dinamico (P-14 x P-23, S-09 x S-17). |
| `api` | 15 | **S-12, P-17 e S-13 nasceram do estrato** — do contrato, do filtro de busca e do payload de erro. Os demais continuam sendo classificacao a posteriori: vieram do Trabalho A e do inventario e foram etiquetados depois. Era a leitura critica que a propria matriz fazia deste dominio, e ela deixou de valer para o pacote fundador. |
| `backend` | 16 | **S-14, S-15, P-18, P-19 e S-16 nasceram do estrato** — do dump que viaja entre ambientes, da role do banco, da coluna cifrada, do topico imutavel e da regiao onde o byte pousa. Nenhum desses vetores tem equivalente em outro dominio. Os demais seguem sendo os estaticos do inventario, reclassificados. |
| `data` | 15 | Aqui a densidade nunca foi heranca preguicosa: `data` e o estrato ONDE A SUITE NASCEU — catalogo, retencao, k-anonimato e lineage vieram olhando para ele. Sobrou um buraco, e **P-20 o fecha**: hash deterministico sem chave tratado como anonimizacao, o risco que engana por parecer resolvido. S-15, P-18 e P-19 aparecem nesta coluna por inspecionarem artefato de dados (catalogo, schema, log de eventos), mas nasceram olhando o BACKEND — sao multi-dominio, nao fundadores daqui. |
| `ai` | 15 | Os quatro mais novos (S-10, S-11, P-15, P-16) nasceram do estrato; os demais foram etiquetados a posteriori. Primeiro dominio herdado a receber checks proprios. |

## Os 52, um por linha

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
| `P-18` | privacy | backend, data | Campo sensivel persistido sem cifra de aplicacao com chave gerenciada |
| `P-19` | privacy | backend, data | Log de eventos com PII sem crypto-shredding |
| `P-20` | privacy | data | Hash determinístico sem chave tratado como anonimizacao |
| `P-22` | privacy | frontend | Rastreador ou cookie nao essencial antes de qualquer consentimento |
| `P-23` | privacy | frontend | PII em transito na URL, no formulario GET ou no Referer |
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
| `S-14` | security | backend | Dump de producao restaurado em ambiente inferior sem descaracterizar |
| `S-15` | security | backend, data | Role de banco com privilegio excessivo |
| `S-16` | security | backend | Persistencia fora da residencia de dados declarada |
| `S-17` | security | frontend | Cookie de sessao sem HttpOnly, Secure ou SameSite |

Todo check tem ao menos um dominio, e todo prefixo corresponde ao pilar —
as duas coisas sao verificadas em `tests/test_dominio.py`.
