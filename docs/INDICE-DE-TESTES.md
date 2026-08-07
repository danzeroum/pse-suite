# Indice de testes — check a check

> **Este documento e GERADO.** Nao edite: rode
> `python -m pse.testes --indice > docs/INDICE-DE-TESTES.md`.

Para cada check: o modulo que o implementa, os arquivos de teste que o
exercitam, a mutacao canonica que ele tem de reprovar, as reguas que
consome e o substrato onde o vetor vive.

A coluna **Como** diz de que evidencia a cobertura foi deduzida —
`import` (o teste importa o modulo do check) ou `id` (o ID aparece
como literal na arvore do teste). As duas sao ancoradas no fato: um
comentario citando o check nao chega a arvore sintatica, e portanto
nao cobre nada (D-01).

## Pacote P — Privacidade

| Check | Modulo | Testes que cobrem | Como | Mutacao canonica (espera) | Reguas | Substrato |
|---|---|---|---|---|---|---|
| **P-01** | `pse/checks/privacy/p01_pii_em_logs.py` | `test_aceite.py`, `test_contrato.py`, `test_dinamico.py`, `test_dominio.py`, `test_indice.py`, `test_mordida.py`, `test_mutacao.py`, `test_rust.py`, `test_trabalho_b.py` | id | CRITICO: valor de PII vai cru para a chamada de log | `pii-patterns` | python, qualquer_backend |
| **P-02** | `pse/checks/privacy/p02_retencao.py` | `test_contrato.py`, `test_dominio.py`, `test_mordida.py`, `test_trabalho_b.py` | id | ALTO: catalogo declara retencao e nao ha job de purga que apague | — | declaracao, python, qualquer_backend |
| **P-03** | `pse/checks/privacy/p03_soft_delete.py` | `test_dominio.py`, `test_trabalho_b.py` | id | ALTO: soft-delete sem eliminacao definitiva | — | python, qualquer_backend, sql |
| **P-04** | `pse/checks/privacy/p04_catalogo.py` | `test_backend_estrato.py`, `test_cobertura.py`, `test_contrato.py`, `test_dominio.py`, `test_trabalho_b.py` | id | MEDIO: campo do catalogo sem dono, base legal e retencao | `sensitive-fields` | declaracao |
| **P-05** | `pse/checks/privacy/p05_minimizacao.py` | `helpers_alvo.py`, `test_cobertura.py`, `test_trabalho_a.py` | id | ALTO: POST com campo fora da allowlist e aceito | — | runtime |
| **P-06** | `pse/checks/privacy/p06_chave_segregada.py` | `test_contrato.py`, `test_dinamico_fase2.py`, `test_mordida.py`, `test_mutacao.py`, `test_trabalho_b.py` | id | CRITICO: chave de pseudonimizacao em texto claro na fonte | — | python, qualquer_backend |
| **P-07** | `pse/checks/privacy/p07_consentimento.py` | `test_dominio.py`, `test_fase3.py` | id | CRITICO: rota protegida por consentimento responde 200 sem consentimento | — | declaracao, runtime |
| **P-08** | `pse/checks/privacy/p08_sensivel_li.py` | `test_contrato.py`, `test_dominio.py`, `test_trabalho_b.py` | id | CRITICO: dado sensivel com base legal legitimo interesse | — | declaracao |
| **P-09** | `pse/checks/privacy/p09_k_anonimato.py` | `test_dominio.py`, `test_fase3.py` | id | ALTO: agregacao exposta devolve celula com 2 titulares | — | runtime |
| **P-10** | `pse/checks/privacy/p10_portabilidade.py` | `test_fase3.py` | id | ALTO: exportacao responde sem hash e sem estrutura declarada | — | runtime |
| **P-11** | `pse/checks/privacy/p11_oraculo.py` | `helpers_alvo.py`, `test_trabalho_a.py` | id | CRITICO: recurso alheio responde 403 e inexistente responde 404 | — | runtime |
| **P-13** | `pse/checks/privacy/p13_consentimento_pre_marcado.py` | `test_catalogo.py`, `test_cobertura.py`, `test_cobertura_web.py`, `test_dominio.py`, `test_frontend.py` | id | CRITICO: checkbox de consentimento com checked literal e sem handler | `frontend-terms` | web |
| **P-14** | `pse/checks/privacy/p14_pii_no_cliente.py` | `test_catalogo.py`, `test_cobertura.py`, `test_cobertura_web.py`, `test_dinamico.py`, `test_dominio.py`, `test_frontend.py`, `test_ratificacao.py` | id | CRITICO: CPF gravado no localStorage e e-mail montado em query string | `frontend-terms`, `pii-patterns` | web |
| **P-15** | `pse/checks/privacy/p15_pii_como_feature.py` | `test_catalogo.py`, `test_ia_estrato.py` | id | ALTO: CPF vira feature de treino com finalidade de cobranca no catalogo | `adversarial-patterns`, `pii-patterns`, `sensitive-fields` | python |
| **P-16** | `pse/checks/privacy/p16_dataset_sem_governanca.py` | `test_catalogo.py`, `test_ia_estrato.py` | id | ALTO: dataset carregado para treino sem entrada em `datasets` | `adversarial-patterns` | declaracao, python |
| **P-17** | `pse/checks/privacy/p17_filtro_sensivel_na_busca.py` | `test_api_estrato.py`, `test_catalogo.py` | id | ALTO: rota de busca aceita ?raca= sem allowlist de filtros | `api-contract`, `prohibited-filters`, `sensitive-fields` | declaracao, python, qualquer_backend |
| **P-18** | `pse/checks/privacy/p18_sensivel_sem_cifra.py` | `test_aceite.py`, `test_backend_estrato.py`, `test_catalogo.py`, `test_cobertura.py`, `test_dominio.py`, `test_ratificacao.py`, `test_regua.py`, `test_rust.py` | id | ALTO: campo sensivel no catalogo sem cifra nem gerencia de chave | `backend-infra`, `sensitive-fields` | declaracao, python, qualquer_backend |
| **P-19** | `pse/checks/privacy/p19_evento_sem_crypto_shredding.py` | `test_aceite.py`, `test_backend_estrato.py`, `test_catalogo.py`, `test_cobertura.py`, `test_dominio.py`, `test_regua.py`, `test_rust.py` | id | ALTO: CPF publicado em topico append-only sem chave por titular | `backend-infra`, `pii-patterns`, `sensitive-fields` | python, qualquer_backend |
| **P-20** | `pse/checks/privacy/p20_hash_como_anonimizacao.py` | `test_catalogo.py`, `test_data_estrato.py`, `test_dominio.py`, `test_indice.py` | id | ALTO: sha256 nu de CPF gravado em coluna declarada anonima | `anonimizacao`, `pii-patterns`, `sensitive-fields` | python, qualquer_backend |
| **P-22** | `pse/checks/privacy/p22_consentimento_observavel.py` | `test_catalogo.py`, `test_dinamico.py` | id | ALTO: tag de analytics dispara no primeiro load, antes de qualquer aceite | `rastreadores` | runtime |
| **P-23** | `pse/checks/privacy/p23_pii_em_transito.py` | `test_catalogo.py`, `test_dinamico.py` | id | ALTO: link publica CPF na query string da propria pagina | `pii-patterns`, `rastreadores`, `sensitive-fields` | runtime |
| **P-24** | `pse/checks/privacy/p24_metadado_publicado.py` | `test_catalogo.py`, `test_dinamico_fase2.py`, `test_ratificacao.py` | id | ALTO: imagem publicada com IFD de GPS no EXIF | `servido-ao-cliente` | runtime |

## Pacote S — Seguranca

| Check | Modulo | Testes que cobrem | Como | Mutacao canonica (espera) | Reguas | Substrato |
|---|---|---|---|---|---|---|
| **S-01** | `pse/checks/security/s01_bola.py` | `helpers_alvo.py`, `test_trabalho_a.py` | id | CRITICO: token de A obtem 200 num recurso declarado do titular B | — | runtime |
| **S-02** | `pse/checks/security/s02_rate_limit.py` | `helpers_alvo.py`, `test_trabalho_a.py` | id | ALTO: listagem responde 200 indefinidamente, sem bloqueio | — | runtime |
| **S-03** | `pse/checks/security/s03_erro_com_pii.py` | `helpers_alvo.py`, `test_trabalho_a.py` | id | ALTO: payload de erro devolve CPF e e-mail do titular | `pii-patterns` | runtime |
| **S-04** | `pse/checks/security/s04_manifesto_terceiros.py` | `test_aceite.py`, `test_backend_estrato.py`, `test_dinamico_fase2.py`, `test_html_no_alcance.py`, `test_ia_terceiros.py`, `test_trabalho_b.py` | id | ALTO: host de terceiro no codigo sem entrada no manifesto | `third-party-endpoints` | declaracao, python, qualquer_backend, web |
| **S-05** | `pse/checks/security/s05_egresso.py` | `test_fase3.py` | id | ALTO: integracao no manifesto sem egress_fields declarados | `sensitive-fields` | declaracao |
| **S-06** | `pse/checks/security/s06_chave_global.py` | `test_aceite.py`, `test_cobertura.py`, `test_dominio.py`, `test_mordida.py`, `test_ratificacao.py`, `test_regua.py`, `test_rust.py`, `test_trabalho_b.py` | id | CRITICO: credencial de parceiro hardcoded | — | python, qualquer_backend, web |
| **S-07** | `pse/checks/security/s07_finalidade.py` | `test_fase3.py` | id | ALTO: requisicao sem X-Purpose e atendida com 200 | — | runtime |
| **S-08** | `pse/checks/security/s08_transferencia_internacional.py` | `test_backend_estrato.py` | id | ALTO: destino fora do BR sem base de transferencia declarada | — | declaracao |
| **S-09** | `pse/checks/security/s09_token_no_cliente.py` | `test_catalogo.py`, `test_cobertura.py`, `test_cobertura_web.py`, `test_dinamico.py`, `test_frontend.py` | id | ALTO: token de sessao guardado no localStorage | `frontend-terms` | web |
| **S-10** | `pse/checks/security/s10_injecao_de_prompt.py` | `test_catalogo.py`, `test_ia_estrato.py` | import+id | CRITICO: entrada do usuario concatenada no prompt sem tratamento | `adversarial-patterns` | python, qualquer_backend |
| **S-11** | `pse/checks/security/s11_saida_do_modelo_em_sink.py` | `test_catalogo.py`, `test_ia_estrato.py` | id | CRITICO: resposta do modelo executada sem validacao | `adversarial-patterns` | python, qualquer_backend |
| **S-12** | `pse/checks/security/s12_ontologia_no_contrato.py` | `test_api_estrato.py`, `test_catalogo.py` | id | ALTO: schema OpenAPI expoe CPF e nao declara ontologia x-ethics | `api-contract`, `pii-patterns`, `sensitive-fields` | declaracao, python, qualquer_backend |
| **S-13** | `pse/checks/security/s13_erro_expoe_internals.py` | `test_api_estrato.py`, `test_catalogo.py` | id | ALTO: handler de erro devolve traceback ao cliente | `api-contract` | python, qualquer_backend |
| **S-14** | `pse/checks/security/s14_dump_de_producao.py` | `test_aceite.py`, `test_backend_estrato.py`, `test_catalogo.py` | id | ALTO: dump de producao restaurado em staging sem pseudonimizacao | `backend-infra` | infra |
| **S-15** | `pse/checks/security/s15_grant_excessivo.py` | `test_backend_estrato.py`, `test_catalogo.py` | id | ALTO: GRANT SELECT ON ALL TABLES em vez de concessao por coluna | `backend-infra` | sql |
| **S-16** | `pse/checks/security/s16_residencia_na_escrita.py` | `test_aceite.py`, `test_backend_estrato.py`, `test_catalogo.py`, `test_cobertura.py`, `test_regua.py`, `test_rust.py` | id | ALTO: politica declara BR e a escrita vai para regiao dos EUA | `backend-infra` | python, qualquer_backend |
| **S-17** | `pse/checks/security/s17_cookie_de_sessao.py` | `test_catalogo.py`, `test_dinamico.py` | id | ALTO: cookie de sessao entregue sem atributo de protecao nenhum | `rastreadores` | runtime |
| **S-18** | `pse/checks/security/s18_terceiro_observado.py` | `test_catalogo.py`, `test_dinamico_fase2.py` | id | ALTO: host de terceiro contactado no load sem constar do manifesto | `third-party-endpoints` | runtime |
| **S-19** | `pse/checks/security/s19_cabecalhos_e_conteudo.py` | `test_catalogo.py`, `test_dinamico_fase2.py` | id | ALTO: documento servido sem CSP nem nosniff | `servido-ao-cliente` | runtime |
| **S-20** | `pse/checks/security/s20_segredo_servido.py` | `test_catalogo.py`, `test_dinamico_fase2.py` | id | CRITICO: chave de AWS publicada no bundle do proprio alvo | `servido-ao-cliente` | runtime |
| **S-21** | `pse/checks/security/s21_sourcemap_em_producao.py` | `test_catalogo.py`, `test_dinamico_fase2.py` | id | MEDIO: bundle declara sourceMappingURL na resposta servida | `servido-ao-cliente` | runtime |

## Pacote E — Etica

| Check | Modulo | Testes que cobrem | Como | Mutacao canonica (espera) | Reguas | Substrato |
|---|---|---|---|---|---|---|
| **E-00** | `pse/checks/ethics/e00_escopo.py` | `test_catalogo.py`, `test_dominio.py` | id | ALTO: codigo mostra modelo de ML e o consumidor declara decision_making none | — | python, qualquer_backend |
| **E-01** | `pse/checks/ethics/e01_explicacao.py` | `helpers_alvo.py`, `test_dominio.py`, `test_trabalho_a.py` | id | ALTO: decisao devolvida sem motivo nem fatores | — | python, qualquer_backend |
| **E-02** | `pse/checks/ethics/e02_decision_log.py` | `helpers_alvo.py`, `test_trabalho_a.py` | id | ALTO: decisao sem modelo, features, score, limiar e revisor | — | python, qualquer_backend |
| **E-03** | `pse/checks/ethics/e03_contestacao.py` | `helpers_alvo.py`, `test_dominio.py`, `test_trabalho_a.py` | id | ALTO: contestacao aceita sem protocolo e sem prazo | — | runtime |
| **E-04** | `pse/checks/ethics/e04_hitl.py` | `test_catalogo.py`, `test_contrato.py`, `test_mordida.py`, `test_trabalho_b.py` | id | CRITICO: decisao de alto impacto sem nenhuma rota de revisao humana | — | python, qualquer_backend |
| **E-05** | `pse/checks/ethics/e05_proxy_discriminacao.py` | `test_catalogo.py`, `test_mordida.py`, `test_trabalho_b.py` | id | ALTO: proxy de discriminacao no score sem ajuste de fairness | `prohibited-filters` | python |
| **E-06** | `pse/checks/ethics/e06_fairness.py` | `test_fase3.py` | id | ALTO: dataset de avaliacao declarado sem relatorio de fairness | — | declaracao |
| **E-07** | `pse/checks/ethics/e07_model_card.py` | `test_catalogo.py`, `test_trabalho_b.py` | id | ALTO: codigo de ML sem Model Card versionado | — | declaracao |
| **E-08** | `pse/checks/ethics/e08_lineage.py` | `test_catalogo.py`, `test_lineage.py` | id | ALTO: catalogo com dado pessoal e nenhuma trilha de proveniencia | `sensitive-fields` | declaracao |
| **E-09** | `pse/checks/ethics/e09_kill_switch.py` | `test_dominio.py`, `test_fase3.py` | id | ALTO: kill switch aceita e confirma simulacao, mas nao declara o efeito | — | runtime |
| **E-10** | `pse/checks/ethics/e10_incerteza.py` | `test_fase3.py` | id | MEDIO: inferencia pontual sem nenhuma medida de confianca | — | python |
| **E-11** | `pse/checks/ethics/e11_pii_em_prompt.py` | `test_catalogo.py`, `test_ia_terceiros.py`, `test_rust.py` | import+id | CRITICO: dado pessoal interpolado cru em chamada a modelo de linguagem | `pii-patterns` | python, qualquer_backend |
| **E-12** | `pse/checks/ethics/e12_derivado_anonimo.py` | `test_catalogo.py`, `test_ia_terceiros.py` | id | ALTO: derivado exportado com campo de origem ausente do catalogo | — | python, qualquer_backend |
| **E-13** | `pse/checks/ethics/e13_dependencia_exfiltra.py` | `test_catalogo.py`, `test_ia_terceiros.py` | id | ALTO: host dentro de node_modules ausente do manifesto de terceiros | `third-party-endpoints` | declaracao |

---

## Os dois defeitos que a trava reprova

### Checks orfaos — sem teste que os cubra

Nenhum. Todo check do catalogo e exercitado por pelo menos um
arquivo de teste.


### Referencias fantasma — teste citando check inexistente

Nenhuma nao declarada.


### Excecoes declaradas

ID fora do catalogo que um teste precisa citar de proposito. Vive em
`CHECKS_FORA_DO_CATALOGO` no proprio modulo de teste, com motivo:
declarada, aparece aqui; calada, reprova.

| Arquivo | ID | Motivo |
|---|---|---|
| `test_data_estrato.py` | `P-21` | investigado e deliberadamente não implementado; este arquivo é onde a decisão está assinada, e citar o ID é o teste |
| `test_dominio.py` | `P-99` | ID hipotético com prefixo de privacidade registrado no pack de segurança — existe só para provar que o registro o rejeita |

---

## O caminho inverso — de cada teste aos checks

| Arquivo | Checks que exercita |
|---|---|
| `test_aceite.py` | `P-01`, `P-18`, `P-19`, `S-04`, `S-06`, `S-14`, `S-16` |
| `test_alvo_local.py` | — |
| `test_api_estrato.py` | `P-17`, `S-12`, `S-13` |
| `test_backend_estrato.py` | `P-04`, `P-18`, `P-19`, `S-04`, `S-08`, `S-14`, `S-15`, `S-16` |
| `test_catalogo.py` | `E-00`, `E-04`, `E-05`, `E-07`, `E-08`, `E-11`, `E-12`, `E-13`, `P-13`, `P-14`, `P-15`, `P-16`, `P-17`, `P-18`, `P-19`, `P-20`, `P-22`, `P-23`, `P-24`, `S-09`, `S-10`, `S-11`, `S-12`, `S-13`, `S-14`, `S-15`, `S-16`, `S-17`, `S-18`, `S-19`, `S-20`, `S-21` |
| `test_cobertura.py` | `P-04`, `P-05`, `P-13`, `P-14`, `P-18`, `P-19`, `S-06`, `S-09`, `S-16` |
| `test_cobertura_web.py` | `P-13`, `P-14`, `S-09` |
| `test_contrato.py` | `E-04`, `P-01`, `P-02`, `P-04`, `P-06`, `P-08` |
| `test_data_estrato.py` | `P-20` |
| `test_dinamico.py` | `P-01`, `P-14`, `P-22`, `P-23`, `S-09`, `S-17` |
| `test_dinamico_fase2.py` | `P-06`, `P-24`, `S-04`, `S-18`, `S-19`, `S-20`, `S-21` |
| `test_dominio.py` | `E-00`, `E-01`, `E-03`, `E-09`, `P-01`, `P-02`, `P-03`, `P-04`, `P-07`, `P-08`, `P-09`, `P-13`, `P-14`, `P-18`, `P-19`, `P-20`, `S-06` |
| `test_fase3.py` | `E-06`, `E-09`, `E-10`, `P-07`, `P-09`, `P-10`, `S-05`, `S-07` |
| `test_frontend.py` | `P-13`, `P-14`, `S-09` |
| `test_html_no_alcance.py` | `S-04` |
| `test_ia_estrato.py` | `P-15`, `P-16`, `S-10`, `S-11` |
| `test_ia_terceiros.py` | `E-11`, `E-12`, `E-13`, `S-04` |
| `test_indice.py` | `P-01`, `P-20` |
| `test_lineage.py` | `E-08` |
| `test_mordida.py` | `E-04`, `E-05`, `P-01`, `P-02`, `P-06`, `S-06` |
| `test_mutacao.py` | `P-01`, `P-06` |
| `test_navegador.py` | — |
| `test_ratificacao.py` | `P-14`, `P-18`, `P-24`, `S-06` |
| `test_regua.py` | `P-18`, `P-19`, `S-06`, `S-16` |
| `test_reprodutibilidade.py` | — |
| `test_rust.py` | `E-11`, `P-01`, `P-18`, `P-19`, `S-06`, `S-16` |
| `test_superficie_dinamica.py` | — |
| `test_trabalho_a.py` | `E-01`, `E-02`, `E-03`, `P-05`, `P-11`, `S-01`, `S-02`, `S-03` |
| `test_trabalho_b.py` | `E-04`, `E-05`, `E-07`, `P-01`, `P-02`, `P-03`, `P-04`, `P-06`, `P-08`, `S-04`, `S-06` |
| `test_versao.py` | — |

<!-- fim-do-corpo-comparado -->

> Tudo acima desta marca e comparado byte a byte pela trava de CI.
> O que vier abaixo dela e volatil de proposito e nao reprova merge.

- pacote: `pse-suite 0.18.0`
- regenerar: `python -m pse.testes > docs/TESTES.md`
- regenerar indice: `python -m pse.testes --indice > docs/INDICE-DE-TESTES.md`
