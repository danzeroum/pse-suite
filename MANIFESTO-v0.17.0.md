# Manifesto de release — pse-suite v0.17.0

> Gerado por `pse --manifesto`. Tag anotada `v0.17.0` local.

```
pse-suite v0.17.0 — HTML era "irrelevante", e escondia egresso a terceiro

suite_version   : 0.17.0
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos   (NENHUM check novo)
Autoprova       : OK · 57 mutacoes declaradas, 0 falhas

O ACHADO QUE VIROU DEFEITO DA SUITE
-----------------------------------
O btv contacta `fonts.googleapis.com` em producao. A camada DINAMICA viu; a
ESTATICA nao. A triagem perguntou por que, e a resposta nao foi "o check e
fraco":

  `.html` estava em `alcance.IRRELEVANTES` — a lista de "nem codigo nem
  declaracao" — e S-04 NUNCA ABRIA UM `.html`.

Mas `index.html` e o unico arquivo do bundle que o navegador carrega SEMPRE,
e e exatamente onde mora `<link href="https://fonts.googleapis.com/...">`.
Um arquivo que DECLARA PARA ONDE O NAVEGADOR VAI nao e irrelevante — chamar
de irrelevante era a lacuna se escondendo atras de uma palavra. O mesmo
padrao de todas as rodadas anteriores: nao um erro de logica, e um silencio
com aparencia de decisao.

  CORRIGIDO NA SUITE, NAO NO ALVO. `.html`/`.htm` entraram em COM_PARSER,
  S-04 passou a le-los, e `codigo_efetivo` ganhou tratamento de `<!-- -->` —
  sem ele o apagador generico usaria `#`, que em HTML nao comenta nada, e um
  host dentro de comentario valeria como fato. Teste-mordida dos dois lados.
  O valor do atributo NAO e apagado: em HTML o `href` E o fato.

O QUE O btv PASSOU A MOSTRAR
-----------------------------
  fonts.googleapis.com  btv-web/index.html   VIOLACAO PROVAVEL (produto)
  fonts.gstatic.com     btv-web/index.html   VIOLACAO PROVAVEL (produto)
  reactjs.org           docs/roadmap-forge   documentacao — do dono
  github.com            docs/design_handoff  documentacao — do dono

Os dois primeiros sao o MESMO host que a camada dinamica ja observava, agora
CORROBORADO PELAS DUAS CAMADAS. Antes, um leitor podia concluir que o
egresso era coisa do navegador; ele esta declarado no artefato entregue.

FATO, NAO VEREDITO: carregar fonte do Google envia o IP de todo visitante ao
Google, sem que o visitante escolha. Se o remedio e auto-hospedar, declarar
no manifesto com DPA, ou nada — E DECISAO DO DONO.

A BORDA: POR QUE NAO FOI MEDIDA
--------------------------------
Duas razoes, e a segunda importa mais que a primeira.

  (1) O daemon Docker nao esta disponivel. `docker info` falha, nao ha
      socket. A imagem nao pode ser buildada.

  (2) O INGRESS NAO ESTA NO REPOSITORIO — e isso nao muda com Docker.
      Procurei em todo o clone por `server_name`, `proxy_pass`,
      `auth_basic`, `listen 443` e `htpasswd`: os unicos arquivos que casam
      sao o proprio compose e o README, e os dois so MENCIONAM o ingress em
      prosa. O compose diz, na linha 17, que a rede e criada pelo compose do
      `global-ingress` — OUTRO PROJETO.

Subir um nginx configurado por mim e medi-lo provaria alguma coisa sobre o
MEU nginx e nada sobre o btv. Seria a fachada que esta serie inteira existe
para evitar, na forma mais convincente: um numero verde produzido por um
arranjo inventado.

  COBERTURA COM BORDA: INDETERMINADA, com motivo nomeado. Nao presumida
  protegida, nao presumida exposta — as duas presuncoes sao erros opostos.

  Registrado como fato: o `btv dashboard` direto responde 200 na raiz e em
  `/dev` sem credencial propria; `BTV_TRUSTED_ORIGINS` vem vazio no compose,
  cujo proprio comentario diz que a origem publica "SO funciona combinada
  com basic auth no ingress". O artefato DECLARA DEPENDER DE UM CONTROLE QUE
  NAO ESTA NELE. Observacao sobre a fronteira do que a PSE audita, nao
  veredito.

MEDICAO DE PRODUCAO, AS DUAS SUPERFICIES
------------------------------------------
                      raiz              /dev
  requisicoes         7                 4
  hosts               fonts.googleapis  (nenhum terceiro)
  cookies             nenhum            nenhum
  artefato declarado  producao          producao
  dev-server observado nao               nao
  S-19                ALTO              ALTO
  S-21                sem achado        sem achado

PENDENCIAS DO DONO, NOMEADAS E DATADAS (2026-08-07)
-----------------------------------------------------
  * o `global-ingress` e versionado? sem ele a borda fica declarada e nao
    verificada
  * a gramatica dos 3 arquivos .ts/.tsx servidos
  * identidade dos SHAs `d6ae70ea` / `1da4d51`
  * o btv declarar `tests/qa/catalog.yaml` (destrava P-18)
  * o btv declarar `data_residency` (destrava S-16)
  * o remedio para Google Fonts (auto-hospedar / manifesto+DPA / nada)
  * documentacao entra no escopo de S-04? (`docs/*.html`, `docs/*.js`)

O btv NAO FOI ALTERADO.

IMPACTO NO CONSUMIDOR
---------------------
  * S-04 passa a ler `.html`/`.htm`. Repositorio com `<link>` ou
    `<script src>` a terceiro nao registrado ve achados NOVOS — legitimos: o
    arquivo nunca tinha sido olhado.
  * `alcance` conta HTML como lido; `.html` sai de IRRELEVANTES.
Exit codes INTACTOS. Schema sem mudanca de forma. IDs INTACTOS. 57/57.

VALIDACAO
---------
  * 684 passed com navegador real; clone limpo verde.
  * 10 testes novos so para HTML, incluindo D-01 (`<!-- -->`) e a prova de
    que o valor do atributo NAO e apagado.

PENDENCIAS DE RATIFICACAO
-------------------------
  1. `.html` no alcance estatico e S-04 lendo HTML (novo aqui).
  2. Medir a borda — bloqueada por (2) acima, nao por falta de tentativa.
```
