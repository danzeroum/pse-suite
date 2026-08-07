# Cobertura real da PSE contra `danzeroum/btv`

> **Gerado**, nunca escrito a mao:
> `python -m pse.cobertura aceites/btv-medicao.json > docs/cobertura-btv.md`.
> O instantaneo e datado e vive no repositorio; o cruzamento com o
> substrato de cada check acontece na geracao, contra o codigo. Ha
> teste que reprova se este arquivo divergir de qualquer um dos dois.

Este documento responde uma pergunta que o laudo sozinho nao responde:
**do que a suite ficou cega, e isso importa?**

Nao e para inflar cobertura nem para pedir desculpa por ela. E para que a
decisao de escopo — *a PSE deveria aprender Rust?* — seja tomada com numero,
nao com impressao.

## Delta desta medicao

O que mudou desde `pse-suite 0.16.0`, e por que. A rodada anterior mediu que
53% do alvo estava cego e recomendou o degrau `literal`: quatro vetores
alcancaveis sem gramatica nenhuma. Esta rodada implementou exatamente isso —
nenhum parser, nenhum check novo, quatro checks existentes passando a
reconhecer `.rs` por padrao textual ancorado.

| | antes | agora |
|---|---|---|
| Linhas lidas por parser | 47.0% | **51.6%** |
| Linhas em alcance parcial (4 vetores) | — | **46.4%** |
| Linhas cegas para TODO check | 53.0% | **2.0%** |
| Checks auditados de verdade | 16 | **16** |
| Checks meio-cegos em Rust | 13 | **13** |

**A leitura honesta do delta.** O numero que encolheu de verdade foi o de linhas
invisiveis para QUALQUER check — de 53.0% para 2.0%. Mas ele encolheu porque
38 mil linhas sairam de *cegas* e entraram em *alcance parcial*, nao em *lidas*:
quatro checks passaram a olha-las e treze continuam sem ver nada ali. Ler a
primeira linha da tabela como se fosse cobertura seria exatamente a fachada
que esta serie de rodadas existe para impedir.

## Procedencia da medicao

| | |
|---|---|
| Alvo | `danzeroum/btv` |
| Commit do alvo | `a3e14f4568da95cf021206aec4816815efbd303a` |
| Medido em | 2026-08-07 |
| Suite | `pse-suite 0.17.0 @ c6efa04a4b1b` |
| Modo | pse_passive (Trabalho B estatico + camada dinamica passiva) |
| Alvo no ar | sim — artefato de PRODUCAO: binario `btv dashboard` servindo btv-web na raiz e web em /dev, mesma origem, `http://127.0.0.1:7878`, atestado `artefato: producao`. SEM container e SEM ingress — ver docs/triagem-btv-web.md 4d |

## Os estados, e por que nenhum colapsa no outro

Colapsar *fora de alcance* em *sem achado* e o verde falso que este
documento existe para impedir. Sao coisas diferentes e ficam diferentes:

| Estado | Significado |
|---|---|
| **AUDITADO** | a suite leu o substrato onde o vetor deste check vive. *Sem achado* aqui significa **olhei e esta limpo**. |
| **AUDITADO PARCIAL** | o substrato existe em mais de uma linguagem do alvo e a suite leu parte. *Sem achado* significa **olhei metade** — e a metade nao olhada esta nomeada na linha. |
| **FORA DE ALCANCE** | o vetor EXISTE no alvo, numa linguagem sem parser. *Sem achado* significa **nao olhei**. |
| **NAO APLICAVEL** | o vetor nao existe neste alvo. Nao ha o que ler nem o que perder. |
| **INDETERMINADO** | tentou e nao decidiu. O laudo ja diz isso, e bloqueia. |
| **NAO HABILITADO** | Trabalho A sem alvo declarado: nao foi executado. |

`AUDITADO PARCIAL` foi acrescentado por causa deste alvo. O btv e poliglota:
a orquestracao e Python, o motor e Rust. Chamar P-01 de *auditado* porque a
metade Python foi lida esconderia 38 mil linhas nao olhadas; chamar de *fora de
alcance* apagaria o que ele de fato achou. Sao tres estados na pergunta e
quatro na resposta porque o alvo real e poliglota — e fingir que nao e seria
inventar uma simplicidade que os dados nao tem.

## Alcance parcial: as linguagens que a suite NAO le e mesmo assim alcanca

Terceira categoria, e ela existe para nao virar mentira nos dois sentidos.
Dizer *lido* faria um leitor concluir que os 57 checks olharam o motor; dizer
*nao lido* esconderia o alcance que existe, e o consumidor que corrigisse uma
chave hardcoded no `.rs` nao entenderia de onde veio o achado.

| Linguagem | Arquivos | Tecnica | Checks que alcancam |
|---|---|---|---|
| Rust | 137 | padrao textual ancorado (sem parser) | `S-06` `P-18` `P-19` `S-16` |

**Ausencia de achado destes quatro significa *olhei e esta limpo*. Ausencia de
achado de QUALQUER OUTRO check nestes arquivos nao significa nada** — eles nao
foram olhados. E a mesma distincao do resto do documento, um nivel abaixo: o
alcance textual nao le a linguagem, alcanca quatro vetores dela.

## Duas reguas de tamanho, e elas discordam

**Nao ha uma resposta so para *qual e a maior fatia do alvo*, e escolher a que
convem e como um mapa de cobertura mente sem dizer nada falso.**

| Estrato | Arquivos | Linhas |
|---|---|---|
| web (JS/TS/JSX/TSX) | 174 | 19040 |
| Rust (motor) | 137 | 38096 |
| Python (orquestracao) | 88 | 8506 |
| declaracao (YAML/JSON) | 65 | 7194 |
| outros | 53 | 9322 |

**Por ARQUIVOS o maior estrato e `web (JS/TS/JSX/TSX)`, com 174. Por LINHAS e**
**`Rust (motor)`, com 38096.** As duas leituras sao verdadeiras e servem a
perguntas diferentes.

*Linhas* diz quanto CODIGO ficou sem parser — e a pergunta que decidiu nao
escrever um parser de Rust. *Arquivos* diz quantas UNIDADES a suite examinou —
e a pergunta certa para saber se o front foi auditado. Um `.rs` de motor e denso
e um componente de tela e curto, entao o mesmo alvo troca de "maior fatia"
conforme a regua.

O documento passou a trazer as duas porque trazer so a primeira deixava a
impressao de que o alvo era pouco auditavel — e isso nao e verdade. Rotulos de
linguagem tambem eram somados errado: `TypeScript` e `TypeScript/TSX` aparecem
separados no bloco `alcance` (ferramentas diferentes), e compara-los um a um
contra `Rust` dividia o front em dois e fazia o motor parecer maior em numero
de arquivos do que e.

### Ter parser nao e ter lido

Dos **174** arquivos JS/TS do alvo, a suite analisou **171** (**98.3%**)
e nao conseguiu ler **3**:

  * `btv-web/src/api/squad.ts`
  * `web/src/api/squad.ts`
  * `web/src/components/screens/user/Designer/PropertiesPanel.tsx`

Ter parser para a linguagem e ter conseguido ler o arquivo sao coisas diferentes. Arquivo nao analisado nao produz achado e nao produz conformidade — ele nao produz nada, e por isso o check que o encontrou segue indeterminado mesmo tendo lido todos os outros.

**Isto era um buraco de cobertura, e foi consertado.** Os checks de frontend
chamavam o parser dentro do laco, e o primeiro arquivo ilegivel derrubava o
check INTEIRO — os outros arquivos, que parseavam sem problema nenhum, ficavam
sem veredito. O gate funcionava (exit 20) e a informacao se perdia: uma
violacao real nos arquivos legiveis nunca seria reportada. Agora o arquivo
ilegivel e contabilizado, os demais sao auditados, e os achados deles vao no
laudo junto com a indeterminacao.

## Proporcao do alvo que a suite consegue ler

**51.6% lido, 46.4% em alcance parcial (4 vetores), 2.0% cego** — em linhas, nao em arquivos.

As tres fatias sao separadas de proposito. Somar o alcance parcial ao lido faria
a proporcao saltar de 51.6% para 98.0% e a suite passaria a mentir por
arredondamento: aquelas linhas sao olhadas por quatro checks e invisiveis para
os outros treze que tem vetor la.

Linhas de proposito: `alcance` conta arquivos (contar linhas do que nao se leu
seria incoerente com o que aquele bloco diz), mas proporcao em arquivo engana
quando um `.rs` tem 300 linhas e um `.json` tem 4. Contar `\n` nao e ler: nao ha
parser, nao ha decisao, e nenhum achado sai daqui.

| Linguagem | Arquivos | Linhas | A suite le? |
|---|---|---|---|
| Rust | 137 | 38096 | **parcial** (4 vetores) |
| Python | 88 | 8506 | sim |
| TypeScript/TSX | 77 | 8184 | sim |
| HTML | 10 | 7097 | sim |
| JavaScript | 9 | 6000 | sim |
| TypeScript | 88 | 4856 | sim |
| YAML | 9 | 3978 | sim |
| JSON | 56 | 3216 | sim |
| TOML | 24 | 604 | **nao** |
| .pyi (nao reconhecida) | 5 | 484 | **nao** |
| Protobuf | 5 | 412 | **nao** |
| shell | 3 | 346 | sim |
| SQL | 4 | 204 | sim |
| .jsonl (nao reconhecida) | 1 | 144 | **nao** |
| Terraform | 1 | 31 | **nao** |
| **total** | | 82158 | 51.6% lido |

## Por dominio

A soma de cada linha fecha o total de checks daquele dominio. Um check aparece
em mais de uma linha quando examina mais de um estrato — e a mesma
multiplicidade da matriz, nao erro de contagem.

| Dominio | AUDITADO | AUDITADO PARCIAL | FORA DE ALCANCE | NAO APLICAVEL | INDETERMINADO | NAO HABILITADO | total |
|---|---|---|---|---|---|---|---|
| `frontend` | 8 | 0 | 0 | 0 | 3 | 0 | 11 |
| `api` | 2 | 3 | 0 | 0 | 2 | 8 | 15 |
| `backend` | 9 | 5 | 0 | 0 | 1 | 1 | 16 |
| `data` | 12 | 2 | 0 | 0 | 1 | 0 | 15 |
| `ai` | 5 | 6 | 0 | 0 | 3 | 1 | 15 |

| Estado | Checks | |
|---|---|---|
| **AUDITADO** | 29 | `E-05` `E-07` `E-08` `E-10` `E-13` `P-02` `P-03` `P-04` `P-07` `P-08` `P-09` `P-15` `P-16` `P-18` `P-19` `P-22` `P-23` `P-24` `S-05` `S-06` `S-08` `S-14` `S-15` `S-16` `S-17` `S-18` `S-19` `S-20` `S-21` |
| **AUDITADO PARCIAL** | 13 | `E-00` `E-04` `E-11` `E-12` `P-01` `P-06` `P-17` `P-20` `S-04` `S-10` `S-11` `S-12` `S-13` |
| **FORA DE ALCANCE** | 0 | — |
| **NAO APLICAVEL** | 0 | — |
| **INDETERMINADO** | 7 | `E-01` `E-02` `E-06` `P-13` `P-14` `S-03` `S-09` |
| **NAO HABILITADO** | 8 | `E-03` `E-09` `P-05` `P-10` `P-11` `S-01` `S-02` `S-07` |
| **total** | 57 | |

A soma fecha 57/57. Nenhum check fica sem estado: um check silencioso
num mapa de cobertura e indistinguivel de um check que passou.

### O numero que interessa

**16 dos 57 checks foram auditados DE VERDADE** — rodaram ate um
veredito E tiveram todo o substrato lido. Sao os unicos em que *sem achado*
significa mesmo *olhei e esta limpo*:

`E-05` `E-07` `E-10` `P-03` `P-04` `P-19` `P-22` `P-23` `P-24` `S-06` `S-14` `S-15` `S-17` `S-19` `S-20` `S-21`

Os outros 41 se dividem entre os que leram metade do substrato, os que
foram pulados com motivo, os indeterminados e os que nem foram habilitados.
Cada um desses e uma resposta legitima; nenhum deles e conformidade.

**FORA DE ALCANCE e NAO APLICAVEL deram zero neste alvo, e isso nao torna o estado decorativo.**

`FORA DE ALCANCE` exige que TODA linguagem do substrato de um check esteja
cega. No btv nenhum chega la porque a orquestracao Python e o front em TS
foram lidos — o mesmo check contra um servico Rust puro sairia fora de
alcance, e ha teste que prova exatamente isso com um alvo sintetico.
`NAO APLICAVEL` exige que o substrato nao exista: o btv tem web, tem Python,
tem SQL e esta no ar, entao nenhum dos cinco substratos falta. Um estado que
so aparece quando e verdade e a unica forma dele valer alguma coisa.

### Nao-aplicavel MEDIDO, e nao alegado

Alegar que um vetor nao existe e a forma mais confortavel de inflar cobertura,
e seria exatamente o que este mapa foi criado para impedir. Entao a suite
SONDA: para cada check com vetor em backend, procura no codigo efetivo dos
`.rs` — sem comentario e sem literal — as marcas daquele vetor. Ausencia de
todas elas e a prova de que o vetor nao esta la.

A sonda so empurra para *nao aplicavel*. Presenca de marca NAO e achado:
significa que o vetor existe e que o check segue cego naquela metade — e por
isso o resultado abaixo e pequeno, e nao grande.

| Check | Vetor ausente em |
|---|---|
| `P-02` | Rust |
| `P-03` | Rust |

Apenas 2 dos checks tiveram o vetor efetivamente ausente do Rust do alvo.
A expectativa que originou a rodada era de que o Rust do btv fosse *majoritariamente*
nao-aplicavel — motor de execucao, sem consentimento nem dark pattern. A medicao
**nao confirma isso**: logger, hash, serde, tratamento de erro e cliente HTTP
estao todos presentes no motor, entao os vetores de P-01, S-13, P-20, S-12 e S-04
existem la e seguem sem ser olhados. Registrar a divergencia e o ponto de medir.

### Extensoes que o mapa nao sabe classificar

A suite nao reconhece estas extensoes, e por isso nao as atribui a familia de
substrato nenhuma. Some do mapa por check; reaparece aqui, porque sumir em
silencio seria a mesma omissao que este documento combate.

| Extensao | Arquivos |
|---|---|
| .pyi (linguagem nao reconhecida) | 5 |
| .jsonl (linguagem nao reconhecida) | 1 |

## Check a check

**Duas colunas de estado, e junta-las seria refazer o mesmo erro em outra escala.**
`Alcance do substrato` responde *a suite leu o codigo onde o vetor vive*;
`No laudo` responde *o check chegou a decidir alguma coisa*. Sao independentes:
um check pode ter substrato plenamente alcancado e mesmo assim ter sido PULADO
com motivo declarado — S-18 nao tem manifesto de terceiros para comparar, e
mostra-lo so como `AUDITADO` diria *olhei e esta limpo* sobre um check que
nao olhou coisa alguma.

Sao 13 pulados neste alvo: `E-08` `E-12` `E-13` `P-02` `P-08` `P-15` `P-16` `P-18` `S-05` `S-08` `S-12` `S-16` `S-18`. Pular com motivo nao bloqueia — mas nao e conformidade, e por isso nao pode
desaparecer dentro do estado de alcance.

A ultima coluna e a que decide escopo: ela nao pergunta se o check ficou cego
neste alvo, e sim se o vetor dele existiria num backend escrito em Rust, Go ou
Java. Sao perguntas diferentes, e so a segunda diz se um parser novo compra
alguma coisa.

| Check | Dominio(s) | Alcance do substrato | No laudo | Leu | Cego em | Vetor em backend nao-Python? |
|---|---|---|---|---|---|---|
| `E-00` | ai | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `E-01` | ai, api | INDETERMINADO | INDETERMINADO | — | — | **sim** |
| `E-02` | ai, backend | INDETERMINADO | INDETERMINADO | — | — | **sim** |
| `E-03` | api | NAO HABILITADO | NAO HABILITADO | — | — | nao |
| `E-04` | ai, backend | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `E-05` | ai | AUDITADO | executou | Python | — | nao |
| `E-06` | ai, data | INDETERMINADO | INDETERMINADO | — | — | nao |
| `E-07` | ai | AUDITADO | executou | JSON, YAML | — | nao |
| `E-08` | data | AUDITADO | **pulado** — nenhum tratamento de dado pessoal a rastrear: o catalogo nao declara campo personal/sensitive (catalogo em si e cobrado por P-04) | JSON, YAML | — | nao |
| `E-09` | ai, api | NAO HABILITADO | NAO HABILITADO | — | — | nao |
| `E-10` | ai | AUDITADO | executou | Python | — | nao |
| `E-11` | ai, backend | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `E-12` | ai, data | AUDITADO PARCIAL | **pulado** — nenhuma exportacao de embedding/hash derivado no codigo | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `E-13` | backend | AUDITADO | **pulado** — manifesto de terceiros ausente — sem ele todo host de dependencia seria achado, e ruido nao e evidencia (a ausencia do manifesto e cobrada por S-04) | JSON, YAML | — | nao |
| `P-01` | backend | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `P-02` | data | AUDITADO | **pulado** — catalogo de dados ausente — cobrado por P-04 | JSON, JavaScript, Python, TypeScript, TypeScript/TSX, YAML | — | **sim** |
| `P-03` | data | AUDITADO | executou | JavaScript, Python, SQL, TypeScript, TypeScript/TSX | — | **sim** |
| `P-04` | data | AUDITADO | executou | JSON, YAML | — | nao |
| `P-05` | api | NAO HABILITADO | NAO HABILITADO | — | — | nao |
| `P-06` | backend | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `P-07` | api, data | AUDITADO | **so metade** — metade runtime nao executada: check de modo `active` nao e disparado por `pse_passive` — rode com --modo apropriado e atestacao no escopo | (aplicacao no ar), JSON, YAML | — | nao |
| `P-08` | data | AUDITADO | **pulado** — catalogo de dados ausente — cobrado por P-04 | JSON, YAML | — | nao |
| `P-09` | data, api | AUDITADO | **so metade** — metade runtime nao executada: check de modo `active` nao e disparado por `pse_passive` — rode com --modo apropriado e atestacao no escopo | (aplicacao no ar) | — | nao |
| `P-10` | api | NAO HABILITADO | NAO HABILITADO | — | — | nao |
| `P-11` | api | NAO HABILITADO | NAO HABILITADO | — | — | nao |
| `P-13` | frontend | INDETERMINADO | INDETERMINADO | — | — | nao |
| `P-14` | frontend | INDETERMINADO | INDETERMINADO | — | — | nao |
| `P-15` | ai | AUDITADO | **pulado** — nenhuma chamada de treino no codigo — nao ha feature a confrontar com o catalogo | Python | — | nao |
| `P-16` | ai | AUDITADO | **pulado** — nenhuma chamada de treino no codigo — nao ha dataset de treino a inventariar | JSON, Python, YAML | — | nao |
| `P-17` | api | AUDITADO PARCIAL | executou | JSON, JavaScript, Python, TypeScript, TypeScript/TSX, YAML | Rust | **sim** |
| `P-18` | backend, data | AUDITADO | **pulado** — catalogo de dados ausente — cobrado por P-04; sem inventario nao ha campo sensivel a confrontar | JSON, JavaScript, Python, Rust, TypeScript, TypeScript/TSX, YAML | — | **sim** |
| `P-19` | backend, data | AUDITADO | executou | JavaScript, Python, Rust, TypeScript, TypeScript/TSX | — | **sim** |
| `P-20` | data | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `P-22` | frontend | AUDITADO | executou | (aplicacao no ar) | — | nao |
| `P-23` | frontend | AUDITADO | executou | (aplicacao no ar) | — | nao |
| `P-24` | frontend | AUDITADO | executou | (aplicacao no ar) | — | nao |
| `S-01` | api | NAO HABILITADO | NAO HABILITADO | — | — | nao |
| `S-02` | api | NAO HABILITADO | NAO HABILITADO | — | — | nao |
| `S-03` | api | INDETERMINADO | INDETERMINADO | — | — | nao |
| `S-04` | backend | AUDITADO PARCIAL | executou | JSON, JavaScript, Python, TypeScript, TypeScript/TSX, YAML | Rust | **sim** |
| `S-05` | backend, data | AUDITADO | **pulado** — manifesto de terceiros ausente — cobrado por S-04 | JSON, YAML | — | nao |
| `S-06` | backend | AUDITADO | executou | JavaScript, Python, Rust, TypeScript, TypeScript/TSX | — | **sim** |
| `S-07` | api, backend | NAO HABILITADO | NAO HABILITADO | — | — | nao |
| `S-08` | data, backend | AUDITADO | **pulado** — manifesto de terceiros ausente — cobrado por S-04 | JSON, YAML | — | nao |
| `S-09` | frontend | INDETERMINADO | INDETERMINADO | — | — | nao |
| `S-10` | ai | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `S-11` | ai | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `S-12` | api | AUDITADO PARCIAL | **pulado** — nenhum arquivo se declara contrato de API (sem chave `openapi` nem `swagger` de topo) — nao ha contrato a confrontar | JSON, JavaScript, Python, TypeScript, TypeScript/TSX, YAML | Rust | **sim** |
| `S-13` | api | AUDITADO PARCIAL | executou | JavaScript, Python, TypeScript, TypeScript/TSX | Rust | **sim** |
| `S-14` | backend | AUDITADO | executou | YAML, shell | — | nao |
| `S-15` | backend, data | AUDITADO | executou | SQL | — | nao |
| `S-16` | backend | AUDITADO | **pulado** — nenhuma politica de residencia de dados declarada (`data_residency` na config ou no manifesto) — sem promessa nao ha o que confrontar, e supor uma jurisdicao seria a suite decidindo pelo consumidor | JavaScript, Python, Rust, TypeScript, TypeScript/TSX | — | **sim** |
| `S-17` | frontend | AUDITADO | executou | (aplicacao no ar) | — | nao |
| `S-18` | frontend | AUDITADO | **pulado** — manifesto de terceiros ausente — cobrado por S-04; sem declaracao nao ha o que confrontar com o que foi observado | (aplicacao no ar) | — | nao |
| `S-19` | frontend | AUDITADO | executou | (aplicacao no ar) | — | nao |
| `S-20` | frontend | AUDITADO | executou | (aplicacao no ar) | — | nao |
| `S-21` | frontend | AUDITADO | executou | (aplicacao no ar) | — | nao |

## Recomendacao de escopo

Nao ha decisao aqui: esta rodada foi de MEDICAO. O que segue e a leitura dos
numeros acima, assinada, para que a decisao seja tomada sobre dados.

**O degrau `literal` compra 2 checks por um custo que nao e de
parser.** P-06, S-04 dependem apenas de literais de string com posicao.
Rust comenta como JavaScript, e `scan.codigo_efetivo` ja apaga comentario
preservando literal — a extensao `.rs` entraria nesse caminho sem gramatica
nenhuma. Sao os de vetor mais universal, e aqueles cuja ausencia hoje e mais
enganosa: `S-06` existe justamente para achar chave em codigo, e as 38 mil
linhas de Rust do btv nunca foram olhadas por ele.

**O degrau `chamada` compra 8, e ai o custo e real.** Precisa de
`tree-sitter-rust` e — o que costuma ser esquecido — de tratar MACRO como
chamada: o logger de Rust e `tracing::info!`, nao `logger.info()`, e um check
que so olhe `call_expression` acha zero e diz que esta limpo. Esse e o modo
de falhar que esta suite menos pode se permitir, porque produz verde.

**O degrau `estrutura` compra 3, e nao se recomenda agora.**
E-04, P-17, S-12 dependem de derive e de macro de rota; o custo deixa de ser
o parser e passa a ser conhecer axum, Diesel e serde um a um. Cobertura de
fachada nasce exatamente assim — de um parser que le a arvore mas nao entende
o framework, nao acha nada, e parece verde.

**36 dos checks nunca precisariam de parser de
Rust.** Os de `runtime` observam a aplicacao no ar e nao leem fonte; os de
`declaracao` leem catalogo, manifesto e contrato; os de `web` (P-13, P-14,
S-09) tem vetor que nao existe fora do navegador. Nenhum parser move um
milimetro nesses — e sabe-lo e o que impede de vender um parser como se ele
resolvesse a cobertura inteira.


| Degrau | Custo | Cegos AGORA | Mesmo vetor, mas nao executaram |
|---|---|---|---|
| `literal` | Nenhuma gramatica. Basta varrer literais de string do `.rs` ignorando comentario — a mesma coisa que `codigo_efetivo` ja faz para `.js`, e Rust comenta igual (`//`, `/* */`). | `P-06` `S-04` | `S-06` `S-16` |
| `chamada` | `tree-sitter-rust`, que existe e e mantido. O trabalho real nao e o parser: e que macro (`tracing::info!`) e chamada nao sao o mesmo NO de arvore, e cada check teria de olhar os dois. | `E-00` `E-11` `E-12` `P-01` `P-20` `S-10` `S-11` `S-13` | `E-01` `E-02` `P-02` `P-18` `P-19` |
| `estrutura` | `tree-sitter-rust` MAIS um modelo de atributo e derive — `#[derive(Serialize)]`, `#[serde(rename)]`, as macros de rota do axum. E aqui que o custo deixa de ser do parser e passa a ser de conhecer cada framework. | `E-04` `P-17` `S-12` | `P-03` |

A ultima coluna nao entra na conta do ganho: sao checks que sequer rodaram
neste alvo, e somar os dois inflaria o que o parser compra. Ficam a vista
porque no dia em que a causa da indeterminacao for resolvida — identidade
declarada, dataset de fairness — eles caem no mesmo buraco.

### O que um parser de Rust NAO compra

36 dos 57 checks nao tem vetor em linguagem de servidor nenhuma:

`E-03` `E-05` `E-06` `E-07` `E-08` `E-09` `E-10` `E-13` `P-04` `P-05` `P-07` `P-08` `P-09` `P-10` `P-11` `P-13` `P-14` `P-15` `P-16` `P-22` `P-23` `P-24` `S-01` `S-02` `S-03` `S-05` `S-07` `S-08` `S-09` `S-14` `S-15` `S-17` `S-18` `S-19` `S-20` `S-21`

Sao os de `runtime` (observam a aplicacao no ar, nao leem fonte), os de
`declaracao` (catalogo, manifesto, contrato) e os de `web` (P-13, P-14, S-09,
cujo vetor nao existe fora do navegador). Nenhum parser move um milimetro
nesses — e sabe-lo e o que impede de vender um parser como se ele resolvesse
a cobertura inteira.

## A camada dinamica

Cobertura estatica e cobertura dinamica nao se substituem, e o btv mostra por
que: os checks de `runtime` foram os UNICOS que a cegueira de Rust nao
tocou. O navegador ve a aplicacao, nao o codigo-fonte — e por isso essa metade
da suite e a que um alvo poliglota nunca perde.

| | |
|---|---|
| URL observada | `http://127.0.0.1:7878` |
| Engine | chromium |
| Requisicoes | 7 |
| Hosts contactados | `127.0.0.1`, `fonts.googleapis.com` |
| Cookies | nenhum |

O front do btv contacta `fonts.googleapis.com` no carregamento — um terceiro que
recebe o IP de todo visitante. S-18 o denunciaria; ele foi PULADO porque nao ha manifesto
de terceiros no alvo para comparar, e S-04 ja cobra a ausencia do manifesto.
E um exemplo exato de por que `pulado` nao pode virar `auditado` no mapa.

## O laudo que originou este mapa

Veredito **indeterminado**, exit `20`. Achados:

| Check | Severidade | Titulo |
|---|---|---|
| `P-04` | ALTO | Catalogo de dados ausente |
| `P-07` | ALTO | Modelo de consentimento ausente |
| `S-04` | ALTO | Host externo nao registrado no manifesto: exemplo.com |
| `S-04` | ALTO | Host externo nao registrado no manifesto: fonts.googleapis.com |
| `S-04` | ALTO | Host externo nao registrado no manifesto: fonts.gstatic.com |
| `S-04` | ALTO | Host externo nao registrado no manifesto: github.com |
| `S-04` | ALTO | Host externo nao registrado no manifesto: reactjs.org |
| `S-04` | ALTO | Host externo nao registrado no manifesto: unpkg.com |
| `S-19` | ALTO | Documento sem content-security-policy, x-content-type-options, referrer-policy |

O laudo NAO foi tocado para produzir este documento. Ele continua indeterminado,
com os mesmos achados e o mesmo exit code — cobertura de fachada comeca
exatamente quando o mapa melhora o laudo que o originou.

