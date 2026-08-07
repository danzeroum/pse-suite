# Manifesto de release — pse-suite v0.15.0

> Gerado por `pse --manifesto`. Tag anotada `v0.15.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.14.2` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.15.0 — um arquivo ilegivel apagava o veredito de 171

Manifesto de release
--------------------
suite_version   : 0.15.0
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos   (NENHUM check novo)

Autoprova
---------
resultado       : OK
mutacoes        : 57 declaradas, 0 falhas

A SUSPEITA, E O QUE A MEDICAO ACHOU
-----------------------------------
A suspeita era que o mapa tivesse subcontado o TypeScript por focar no Rust,
e que metade do front pudesse estar cega por `.tsx` nao ser parseado.

  `.tsx` nao e parseado      FALSA. E parseado, e ha tres testes provando
                             com violacao REAL em `.tsx` — P-13, P-14, S-09.
  o mapa subcontou o TS      VERDADEIRA, e a causa era simples.
  o front pode estar cego    VERDADEIRA, e por um motivo muito pior.

O DEFEITO DE VERDADE — FALSO-NEGATIVO PRODUZIDO POR FAIL-CLOSED
----------------------------------------------------------------
Os checks de frontend chamavam o parser DENTRO do laco. O primeiro arquivo
que nenhuma gramatica alcancasse derrubava o check INTEIRO.

No btv sao TRES arquivos. Os outros 171 — que parseavam sem problema nenhum
— ficavam SEM VEREDITO.

O gate funcionava: exit 20, nunca verde. E a informacao se perdia. Uma
violacao real em qualquer um dos 171 NUNCA SERIA REPORTADA, porque o check
morria antes de chegar nela. Nem verde honesto, nem informacao: o pior dos
dois mundos, e a unica vez nesta suite em que fail-closed produziu
falso-negativo.

  CORRECAO. `pse/engine/jsast.por_arquivo` contabiliza o arquivo ilegivel
  em vez de morrer nele. `CheckIndeterminado` ganhou `achados`, e o runner
  os emite junto com a indeterminacao. Bloquear e emitir NAO sao opostos: o
  veredito segue indeterminado (o check nao viu tudo), e o que ele viu vai
  no laudo.

  Os tres do btv, nomeados:
    btv-web/src/api/squad.ts
    web/src/api/squad.ts
    web/src/components/screens/user/Designer/PropertiesPanel.tsx

DUAS REGUAS DE TAMANHO, E ELAS DISCORDAM
-----------------------------------------
O mapa comparava ROTULOS DE LINGUAGEM, e `TypeScript` (88) e
`TypeScript/TSX` (77) sao rotulos separados no bloco `alcance` porque
carregam ferramentas diferentes. Comparados um a um contra `Rust` (137), o
motor parecia a maior fatia por numero de arquivos. Somando o ESTRATO:

  estrato                   arquivos    linhas
  web (JS/TS/JSX/TSX)          174      19.040
  Rust (motor)                 137      38.096
  Python (orquestracao)         88       8.506
  declaracao (YAML/JSON)        65       7.194

POR ARQUIVOS o front e a maior fatia. POR LINHAS e o motor. As duas sao
verdadeiras — `.rs` de motor e denso, componente de tela e curto — e servem
a perguntas diferentes: linhas diz quanto CODIGO ficou sem parser (a
pergunta que decidiu nao escrever um parser de Rust); arquivos diz quantas
UNIDADES a suite examinou (a pergunta certa para saber se o front foi
auditado).

O documento passou a trazer as duas. Trazer so linhas deixava a impressao de
que o alvo era pouco auditavel, e nao e.

  Isto NAO aumenta cobertura nenhuma. So para de esconder a que ja existia.
  O Rust segue com alcance a quatro vetores, e 13 checks seguem meio-cegos
  la.

TER PARSER NAO E TER LIDO — CENSO NOVO NO MAPA
------------------------------------------------
  arquivos JS/TS do btv    : 174
    ANALISADOS             : 171   (98,3%)
    nao analisados         :   3   (nomeados)

  elementos JSX percorridos: 1.159   <- superficie de P-13
  chamadas percorridas     : 5.797   <- superficie de P-14 e S-09

Arquivo nao analisado nao produz achado e nao produz conformidade: ele nao
produz NADA. Por isso o check que o encontrou segue indeterminado mesmo
tendo lido todos os outros.

TRIAGEM DO ESTRATO WEB: ZERO ACHADO, TRES INCERTOS
----------------------------------------------------
  VIOLACAO PROVAVEL        0
  FALSO-POSITIVO PROVAVEL  0
  INCERTO                  3   (os tres arquivos nao analisados)

Nao ha lista de violacoes a devolver e nao ha falso-positivo a triar: os
checks de frontend nao produziram achado nenhum contra o btv, nem antes nem
depois da correcao. Rodado tambem com recorte em `btv-web/src/` (51
arquivos): mesmo zero.

Perguntas ao dono, em `docs/triagem-btv-web.md`:
  * vale reduzir a construcao da linha 56 de `squad.ts` a uma forma que a
    gramatica 0.23.2 alcance, ou a suite deve atualizar a gramatica?
  * ha DUAS arvores de front (`btv-web/` e `web/`), as duas com
    `api/squad.ts`. `web/` esta ativo ou e resto de migracao?

O btv NAO FOI ALTERADO.

POR QUE MINOR E NAO PATCH
--------------------------
A tarefa previa patch, "a menos que `.tsx` nao fosse parseado". `.tsx` era
parseado — mas o que mudou e maior que o previsto: um check agora pode
EMITIR ACHADO E SER INDETERMINADO ao mesmo tempo. Isso e comportamento
visivel ao consumidor, nao correcao interna.

IMPACTO NO CONSUMIDOR
---------------------
  * Repositorio com arquivo JS/TS ilegivel passa a RECEBER os achados dos
    demais arquivos. O exit code nao muda (segue 20), mas o laudo passa a
    ter findings que antes se perdiam — pode parecer regressao e e o
    contrario.
  * `CheckIndeterminado(msg, achados=[...])` — parametro novo, opcional.
  * Laudo/medicao ganham o censo `parse`. Campo novo; nenhum existente mudou.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma. IDs INTACTOS.
Catalogo 57/57 — nenhum check novo.

VALIDACAO
---------
  * 634 passed com navegador real; clone limpo verde.
  * btv reprocessado com o front no ar: exit 20, 29 executados, 6 achados,
    zero em `.ts`/`.tsx`.
  * 20 testes novos, entre eles os tres que provam `.tsx` por COMPORTAMENTO
    (violacao real dispara), nao por lista de extensoes.

PENDENCIAS DE RATIFICACAO
-------------------------
  1. Achado emitido junto com indeterminacao (novo nesta versao).
  2. Os tres INCERTOS do estrato web — perguntas diretas ao dono.
  3. O embrulho de cifra opaco -> exit 20, de v0.14.2.
  4. A regra `env!` -> exit 20, de v0.14.0.
  5. A severidade assimetrica em Rust, de v0.14.0.
  6. Identidade dos SHAs do cockpit, de v0.13.0.
  7. `local_target`, de v0.13.0.
  8. P-24 em `privacy`, de v0.12.0.
  9. S-14 e S-15 como candidatos a CRITICO, de v0.9.0.
```
