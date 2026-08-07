# Manifesto de release — pse-suite v0.16.0

> Gerado por `pse --manifesto`. Tag anotada `v0.16.0` local.

```
pse-suite v0.16.0 — medido contra o artefato, e ele decidiu

Manifesto de release
--------------------
suite_version   : 0.16.0
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos   (NENHUM check novo)

Autoprova       : OK · 57 mutacoes declaradas, 0 falhas

O ARTEFATO DE PRODUCAO VIROU ALVO
---------------------------------
`cargo build --release -p btv-cli` + `vite build` nas duas SPAs + o binario
subido com `BTV_WEB_DIR` e `BTV_DEV_WEB_DIR` — UM processo, MESMA origem,
raiz e `/dev`, exatamente como o `Dockerfile` os monta.

  O QUE DIFERE DO CONTAINER, DECLARADO. O daemon Docker nao esta disponivel
  neste ambiente. O que subiu foi o MESMO binario com as MESMAS duas `dist`
  e as MESMAS duas variaveis; o arranjo de servico e identico. Falta o
  isolamento do container e o INGRESS. Declarado, nao presumido.

O VEREDITO QUE SO O ARTEFATO PODIA DAR
---------------------------------------
                              dev server        PRODUCAO
  requisicoes (raiz / /dev)   119 / 93          7 / 4
  S-21 sourcemap              MEDIO 107 / 84    0 / 0
  S-19 cabecalhos             ALTO / ALTO       ALTO / ALTO
  P-22 P-23 P-24 S-17 S-20    sem achado        sem achado
  cookies                     nenhum            nenhum
  hosts (raiz)                fonts.googleapis  fonts.googleapis

  S-21 ERA ANDAIME — CONFIRMADO. Contra o bundle real os 107 e os 84
  sourcemaps viraram ZERO. O que o check via era `/@vite/client` e
  `node_modules/.vite/deps/*`. Reclassificado de "falso-positivo provavel"
  para FALSO-POSITIVO CONFIRMADO sobre o artefato.

  S-19 ERA REAL — CONFIRMADO. Persistiu em ALTO nas duas superficies contra
  o artefato: o binario nao define `content-security-policy`,
  `x-content-type-options` nem `referrer-policy`. Reclassificado de
  "incerto" para ACHADO REAL sobre o dashboard — com a ressalva de que a
  BORDA nao foi observada.

  `fonts.googleapis.com` SOBREVIVE AO BUILD. Nao era artefato de dev: o
  produto contacta o terceiro tambem em producao. O console `/dev` nao
  contacta nenhum.

Os dois estavam entre os cinco INCERTOS da v0.15.1, e a medicao os resolveu
em direcoes OPOSTAS. Nenhum dos dois teria sido decidido por argumento.

`artefato` — O CAMPO QUE EVITA A CONFUSAO VIRAR ROTINA
--------------------------------------------------------
`target.artefato: producao | desenvolvimento`, opcional. A suite NAO
consegue descobrir isso sozinha: um `vite preview` e um deploy real servem
bundle igualmente minificado, e inferir "producao" da ausencia de indicios
seria inventar um fato sobre o alvo. O operador declara, a suite observa, e
o laudo CRUZA:

  declarado producao + indicio de dev observado -> `contradicao_de_artefato`
    em voz alta. Ha teste-mordida: apontar a atestacao de producao para o
    Vite dispara.
  declarado producao sem indicio contrario -> nota dizendo que a suite NAO
    verificou a declaracao, so nao viu indicio contra.
  nada declarado -> o laudo diz o que observou e nao afirma se e o artefato.

Valor fora da lista e exit 30, antes de qualquer byte: um typo (`prod`)
passando em silencio faria a declaracao virar decoracao.

O BASIC AUTH: DECLARADO, NAO OBSERVADO
----------------------------------------
A PSE mediu `127.0.0.1:7878` DIRETO, sem ingress. Fato observado: o
dashboard responde 200 na raiz e em `/dev` sem pedir credencial propria. O
`docker-compose.prod.yml` declara que autenticacao e responsabilidade do
ingress, e o ingress NAO FOI OBSERVADO — e infra externa ao artefato.

Isto e registro de fato, nao veredito. A suite nao afirma que `/dev` esta
exposto: afirma o que viu (dashboard sem auth propria) e o que nao viu (a
borda). Se a composicao das duas coisas e adequada e JULGAMENTO DO DONO.

O btv NAO FOI ALTERADO.

POR QUE MINOR
-------------
`target.artefato` e campo novo de contrato, e `observacao_de_rede` ganhou
quatro campos. Nenhum existente mudou de forma ou de valor, e config sem
`artefato` continua valida — mas contrato que cresce e minor.

IMPACTO NO CONSUMIDOR
---------------------
  * `target.artefato` opcional; valor invalido e exit 30.
  * `observacao_de_rede` ganha `artefato_declarado`, e conforme o caso
    `contradicao_de_artefato`, `nota_de_producao` ou `nota_de_artefato`.
  * Consumidor que media contra dev server e lia S-21 como propriedade do
    produto passa a ver a qualificacao. NENHUM achado some por conta disso —
    o que muda e o que o laudo diz sobre o que mediu.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma. IDs INTACTOS.
Catalogo 57/57.

VALIDACAO
---------
  * 670 passed com navegador real; clone limpo verde.
  * Producao medida ao vivo nas duas superficies, mesma origem.
  * 9 testes novos, entre eles a mordida da contradicao e a prova de que
    config sem `artefato` continua valida.

PENDENCIAS DE RATIFICACAO
-------------------------
  1. `target.artefato` e o cruzamento declarado-x-observado (novo aqui).
  2. A gramatica dos 3 arquivos .ts/.tsx servidos.
  3. Identidade dos SHAs do cockpit.
  4. O btv declarar catalogo (P-18) e data_residency (S-16).
  5. Medir dentro do container e com o ingress na frente — o que sobrou.
```
