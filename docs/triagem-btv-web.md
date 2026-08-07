# Triagem do estrato web (`.ts` / `.tsx`) no `danzeroum/btv`

> Escrito a mao. Os NUMEROS vieram de instrumentacao reproduzivel; a
> classificacao e leitura de contexto.
>
> **Alvo:** `danzeroum/btv` @ `a3e14f45` (clone limpo) · **suite:** 0.17.0 ·
> **data:** 2026-08-07 · **dev, producao — e a borda, que nao existe no repo**
>
> **A PSE aponta; o dono valida.** O btv nao foi alterado.

---

## O que a suspeita era, e o que a medicao achou

A suspeita: o mapa de cobertura teria **subcontado o TypeScript** por focar
no Rust, e metade do front poderia estar cega por `.tsx` nao ser parseado.

**As duas partes se confirmaram em graus muito diferentes.**

| Suspeita | Veredito |
|---|---|
| `.tsx` nao e parseado | **FALSA.** E parseado, e ha tres testes provando com violacao real em `.tsx` |
| O mapa subcontou o TS | **VERDADEIRA, mas nao como se pensava** — ver abaixo |
| O front pode estar cego | **VERDADEIRA, e por um motivo pior** — 171 arquivos ficavam sem veredito |

---

## 1. `.tsx` e parseado — provado com violacao, nao com lista

Um teste que apenas verificasse `".tsx" in EXTS` passaria mesmo se a
gramatica de TSX nunca carregasse. Entao a prova e por comportamento: um
`.tsx` com violacao **de verdade** tem de disparar.

```tsx
export function Tela({ cpf }: { cpf: string }) {
  const url = `/api/busca?cpf=${cpf}`;   // P-14 dispara
  fetch(url);
  return <div>{cpf}</div>;
}
```

Os tres checks de frontend disparam em `.tsx`: **P-14** (PII na URL),
**S-09** (token em `localStorage`), **P-13** (checkbox pre-marcado). Ha
teste para cada um.

`.ts` e `.tsx` sao gramaticas **diferentes** no tree-sitter e nenhuma e
superconjunto da outra — a de tsx trata `<T>` como JSX, a de typescript nao
conhece JSX. A suite tenta as duas, e isso ja estava certo desde a v0.13.0.

---

## 2. O defeito de verdade: um arquivo ilegivel apagava 171

Os checks de frontend chamavam o parser **dentro do laco**:

```python
for p in scan.arquivos(ctx.repo, _ast.EXTS):
    raiz = _ast.arvore(p, texto)      # levanta CheckIndeterminado
```

O primeiro arquivo que nenhuma gramatica alcancasse derrubava o check
**inteiro**. No btv sao **tres** arquivos — e os outros **171**, que
parseavam sem problema nenhum, **ficavam sem veredito**.

O gate funcionava: exit 20, nunca verde. Mas a informacao se perdia. **Uma
violacao real nos 171 arquivos legiveis nunca seria reportada**, porque o
check morria antes de chegar nela.

Isso e falso-negativo produzido por fail-closed — nem verde honesto, nem
informacao. O pior dos dois mundos.

**Correcao.** O arquivo ilegivel passa a ser **contabilizado**, nao fatal. O
check audita os demais, e `CheckIndeterminado` carrega os achados do que
leu. O veredito segue indeterminado — o check nao viu tudo e nao vai fingir
que viu — e o que ele viu vai no laudo junto.

Os tres arquivos que nenhuma gramatica alcanca no btv:

```
btv-web/src/api/squad.ts
web/src/api/squad.ts
web/src/components/screens/user/Designer/PropertiesPanel.tsx
```

A mensagem nao acusa o alvo: pode ser construcao valida que a gramatica
instalada (`tree-sitter-typescript` 0.23.2) nao alcanca. A suite nao
distingue os dois casos e nao finge que distingue.

---

## 3. Prova de que os checks olharam — e quanto

Zero achado so vale como afirmacao se houver prova de leitura.

```
arquivos JS/TS do alvo   : 174
  ANALISADOS             : 171   (98,3%)
  nao analisados          :   3   (nomeados acima)

elementos JSX examinados : 1.159   <- superficie de P-13
chamadas examinadas      : 5.797   <- superficie de P-14 e S-09
```

Mil e cento e cinquenta e nove elementos JSX e quase seis mil chamadas
foram efetivamente percorridos. O zero e real.

---

## 4. Achados em TS: contagem honesta

| Classificacao | Quantidade |
|---|---|
| **VIOLACAO PROVAVEL** | **4** — `S-19` nas duas superficies (4c) + 2 hosts de terceiro no `index.html` (4e) |
| **FALSO-POSITIVO CONFIRMADO** | **2** — `S-21` nas duas, era andaime de dev server |
| **INCERTO — precisa do dono** | **6** — 3 arquivos nao analisados, 2 hosts em HTML de documentacao, e a borda nao observada (4d) |

A medicao contra o artefato de producao (4c) resolveu dois dos cinco
incertos anteriores em direcoes OPOSTAS: `S-21` caiu para zero e `S-19`
persistiu. Nenhum dos dois teria sido decidido sem medir o artefato.

Nao ha lista de violacoes a devolver, e nao ha falso-positivo a triar: **os
checks de frontend nao produziram achado nenhum contra o btv**, nem antes
nem depois da correcao.

Rodados tambem com recorte em `btv-web/src/` (51 arquivos JS/TS): mesmo
resultado — zero.

### Os tres INCERTOS

**(i) `btv-web/src/api/squad.ts` — nao analisado.** E o cliente da API do
squad, exatamente o tipo de arquivo que trata estado e chamada de API. **A
suite nao afirma nada sobre ele.** Nao ha achado e nao ha conformidade: ele
nao produziu nada.
*Pergunta ao dono:* vale reduzir a construcao da linha 56 a uma forma que a
gramatica 0.23.2 alcance, ou preferem que a suite atualize a gramatica?

**(ii) `web/src/api/squad.ts`** — mesma situacao. Ha **duas** arvores de front
no repositorio (`btv-web/` e `web/`), e as duas tem `api/squad.ts`.

*A pergunta foi respondida pelo dono, e a resposta muda a prioridade.*
`web/` **NAO e resto de migracao**: e o console de desenvolvedor, buildado e
servido. Confirmado em `infra/docker/Dockerfile` — dois estagios (`web-build`
e `btvweb-build`), `BTV_DEV_WEB_DIR=/src/web/dist` e
`BTV_WEB_DIR=/src/btv-web/dist` — e em `crates/btv-server/src/lib.rs`, que
monta `router.nest_service("/dev", svc)`.

| Arvore | Servida em | Variavel |
|---|---|---|
| `btv-web/` | `/` (raiz) — o produto | `BTV_WEB_DIR` |
| `web/` | `/dev` — console de desenvolvedor | `BTV_DEV_WEB_DIR` |

Os tres arquivos ilegiveis sao **codigo embarcado e servido nas duas SPAs**,
nao sobra. A lacuna da gramatica vale para o produto E para o console.

**(iii) `web/src/components/screens/user/Designer/PropertiesPanel.tsx`** —
nao analisado. Tela de designer; a gramatica falha na linha 35 pela versao
tsx e na linha 1 pela de typescript.

Nenhum dos tres e achado. Sao **lacunas nomeadas** — a diferenca entre
"olhei e esta limpo" e "nao olhei" continua sendo o ponto.

---

## 4b. Duas superficies dinamicas — e uma delas nunca tinha sido observada

**A lacuna.** Todas as medicoes dinamicas anteriores carregaram a **raiz**.
O console em `/dev` nunca foi observado por navegador nenhum, e o laudo nao
registrava esse silencio: os sete checks dinamicos afirmavam algo sobre uma
superficie e **nada** sobre a outra, sem distinguir as duas. E o mesmo verde
falso que o bloco `alcance` impede no estatico, uma camada acima.

**Corrigido nos dois sentidos.** O laudo passou a NOMEAR a superficie
observada (`superficie_observada` + nota dizendo que nenhuma outra rota da
mesma origem foi carregada), e as duas superficies foram medidas.

### Medicao das duas

| | raiz (`btv-web`) | console (`web`) |
|---|---|---|
| Requisicoes | 119 | 93 |
| Hosts contactados | `127.0.0.1`, **`fonts.googleapis.com`** | `127.0.0.1` |
| Cookies | nenhum | nenhum |
| S-19 cabecalhos | ALTO | ALTO |
| S-21 sourcemap | MEDIO (107) | MEDIO (84) |
| P-22 · P-23 · P-24 · S-17 · S-20 | sem achado | sem achado |
| S-18 terceiros | pulado (sem manifesto) | pulado (sem manifesto) |

**Observacao factual, sem veredito:** o console **nao** contacta terceiro
nenhum; a raiz contacta `fonts.googleapis.com`. Nenhuma das duas depositou
cookie durante a carga. O que isso significa para a exposicao de `/dev` **e
julgamento do dono** — a PSE observa carga, cabecalho e cookie; nao conclui
risco. Registro tambem, como fato: o `docker-compose.prod.yml` declara que
autenticacao e responsabilidade do ingress, e o servidor Rust nao define
`content-security-policy`, `x-content-type-options` nem `referrer-policy`
(procurados em `crates/btv-server/src/*.rs`, ausentes).

### E uma correcao que a segunda medicao expos: **contra o que se mediu**

As duas superficies foram observadas em **servidor de desenvolvimento**
(Vite), nao no `btv dashboard` de producao. Isso muda o que os achados
significam:

* **S-21 (sourcemap) — FALSO-POSITIVO PROVAVEL sobre o artefato.** Os
  "bundles" sao `/@vite/client` (com `sourceMappingURL=data:…base64`),
  `/@react-refresh` e `node_modules/.vite/deps/*`. Nada disso e o que o
  `vite build` produz: e modo de desenvolvimento, que serve sem minificar e
  com sourcemap embutido **por design**. O check nao errou — a referencia
  existe mesmo, e ele so afirma que existe. Errado era o laudo nao dizer
  contra o que mediu.
* **S-19 (cabecalhos) — INCERTO.** Um dev server nao poe cabecalho de borda,
  entao o achado nao prova a postura de producao. *Porem* o servidor Rust
  tambem nao os define, e o compose delega isso ao ingress: o achado
  **pode** valer em producao, e so observando o ingress se sabe.

**Correcao na suite.** O relatorio de observacao passou a declarar
`servidor_de_desenvolvimento` com os indicios que o denunciaram, em regua
(`pse/data/servido-ao-cliente.yaml`), com nota dizendo que o comportamento e
normal do modo e nao propriedade do artefato publicado. Nenhum veredito
mudou — mudou o que o leitor entende do veredito.

### Limite desta medicao — e ele foi levantado

O console foi servido em porta propria (Vite em `127.0.0.1:5179`), nao
aninhado em `/dev`. **Essa pendencia esta fechada:** ver 4c.

---

## 4c. A medicao contra o ARTEFATO, e o que ela decidiu

O `btv dashboard` foi compilado (`cargo build --release -p btv-cli`), as duas
SPAs buildadas (`vite build`), e o binario subido com
`BTV_WEB_DIR=btv-web/dist` e `BTV_DEV_WEB_DIR=web/dist` — **um processo,
mesma origem, raiz e `/dev`**, exatamente como o `Dockerfile` os monta.

> **O que difere do container.** O daemon Docker nao esta disponivel neste
> ambiente, entao a imagem nao foi buildada. O que subiu foi o MESMO binario
> com as MESMAS duas `dist` e as MESMAS duas variaveis que o Dockerfile
> define — o arranjo de servico e identico; o que falta e o isolamento do
> container e o **ingress**. Declarado, nao presumido.

### O veredito que so o artefato podia dar

| | dev server | **producao** |
|---|---|---|
| Requisicoes (raiz / `/dev`) | 119 / 93 | **7 / 4** |
| `S-21` sourcemap | MEDIO (107) / MEDIO (84) | **0 / 0** |
| `S-19` cabecalhos | ALTO / ALTO | **ALTO / ALTO** |
| `P-22` `P-23` `P-24` `S-17` `S-20` | sem achado | sem achado |
| Cookies | nenhum | nenhum |
| Hosts (raiz) | `fonts.googleapis.com` | `fonts.googleapis.com` |

**`S-21` era andaime — confirmado.** Contra o bundle real, os 107 e os 84
sourcemaps viraram **zero**. A suspeita de 4b estava certa, e agora esta
medida: o que S-21 via era `/@vite/client` e `node_modules/.vite/deps/*`,
encanamento do modo de desenvolvimento. Reclassificado de *falso-positivo
provavel* para **falso-positivo confirmado sobre o artefato**.

**`S-19` era real — confirmado.** Persistiu em ALTO nas duas superficies
contra o artefato. Nao era ausencia de cabecalho de dev server: o binario
`btv dashboard` nao define `content-security-policy`,
`x-content-type-options` nem `referrer-policy` (ja verificado no codigo, e
agora observado no ar). Reclassificado de *incerto* para **achado real sobre
o dashboard**, com uma ressalva que segue valendo: **a borda nao foi
observada**. Se um ingress poe esses cabecalhos, o usuario final nao os
perde. A PSE mediu o dashboard direto, sem ingress na frente.

**`fonts.googleapis.com` sobrevive ao build.** Nao era artefato de dev: o
produto contacta o terceiro tambem em producao. O console `/dev` nao
contacta nenhum.

### O basic auth: declarado, nao observado

A PSE mediu `127.0.0.1:7878` **direto**, sem o ingress. Fato observado: o
dashboard responde `200` na raiz e em `/dev` sem pedir credencial nenhuma.
O `docker-compose.prod.yml` declara que autenticacao e responsabilidade do
ingress (basic auth com `.htpasswd`), e o ingress **nao foi observado** —
e infra externa ao artefato.

**Isto e registro de fato, nao veredito.** A suite nao afirma que `/dev`
esta exposto: ela afirma o que viu (dashboard sem auth propria) e o que nao
viu (a borda). Se a composicao das duas coisas e adequada **e julgamento do
dono**.

### `artefato` — o campo que evita a confusao virar rotina

A atestacao ganhou `target.artefato: producao | desenvolvimento`. A suite
**nao consegue** descobrir isso sozinha — um `vite preview` e um deploy real
servem bundle igualmente minificado, e inferir "producao" da ausencia de
indicios seria inventar um fato sobre o alvo. Entao o operador declara, a
suite observa, e o laudo cruza os dois:

* declarado `producao` + indicios de dev server observados →
  **`contradicao_de_artefato`**, em voz alta. Ha teste-mordida: apontar a
  atestacao de producao para o Vite dispara.
* declarado `producao` sem indicio contrario → nota dizendo que a suite
  **nao verificou** a declaracao, so nao viu indicio contra.
* nada declarado → o laudo diz o que observou e nao afirma se e o artefato.

---

## 4d. A borda: por que ela NAO foi medida, e nao e falta de tentativa

A pendencia da v0.16.0 era medir com o **ingress** na frente — a camada onde
o basic auth existe de verdade. Duas coisas impediram, e a segunda e mais
importante que a primeira.

**(1) O daemon Docker nao esta disponivel neste ambiente.** `docker info`
falha; nao ha `/var/run/docker.sock`. A imagem nao pode ser buildada.

**(2) O ingress NAO ESTA NO REPOSITORIO — e isso nao muda com Docker.**

Procurei em todo o clone por `server_name`, `proxy_pass`, `auth_basic`,
`listen 443` e `htpasswd`. Os unicos arquivos que casam sao o proprio
`docker-compose.prod.yml` e o `infra/docker/README.md`, e os dois so
**mencionam** o ingress em prosa. O compose diz, na linha 17:

> A rede `btv-prod-net` e criada pelo compose do ingress (**global-ingress**);
> aqui ela e referenciada como externa.

O ingress e **outro projeto**. Nao ha `nginx.conf`, nao ha `.htpasswd`, nao
ha nada a reproduzir. Subir um nginx configurado por mim e medi-lo provaria
alguma coisa sobre o *meu* nginx e **nada** sobre o btv — seria a fachada
que esta serie inteira de rodadas existe para evitar, na sua forma mais
convincente: um numero verde produzido por um arranjo inventado.

### O que isso deixa registrado, como fato

| | |
|---|---|
| Arranjo medido | binario `btv dashboard` + duas `dist`, **sem container, sem borda** |
| `btv dashboard` direto (`:7878`) | responde **200** na raiz e em `/dev`, **sem credencial propria** |
| Basic auth | **NAO OBSERVADO** — vive no `global-ingress`, fora do artefato |
| `BTV_TRUSTED_ORIGINS` | vazio no compose (`${BTV_TRUSTED_ORIGINS:-}`); o proprio comentario diz que a origem publica *"SO funciona combinada com basic auth no ingress"* |

**O artefato declara depender de um controle que nao esta nele.** Isso e uma
observacao factual sobre a fronteira do que a PSE consegue auditar, nao um
veredito: a suite audita o repositorio, e o controle mora fora dele.

**Cobertura com borda: INDETERMINADA**, com motivo nomeado — nao presumida
protegida, nao presumida exposta. As duas presuncoes seriam erros opostos, e
a honesta e dizer que a camada nao foi observada.

*Pergunta ao dono:* o `global-ingress` e versionado em algum lugar? Se sim,
apontar o repositorio torna a borda auditavel; enquanto nao, ela fica
declarada e nao verificada.

---

## 4e. `fonts.googleapis.com` — o achado que virou defeito da SUITE

O produto contacta o Google Fonts em producao. A camada **dinamica** viu; a
**estatica** nao. A triagem perguntou por que, e a resposta nao foi "o check
e fraco":

`.html` estava em `alcance.IRRELEVANTES` — a lista de "nem codigo nem
declaracao" — e **S-04 nunca abria um `.html`**. Mas `index.html` e o unico
arquivo do bundle que o navegador carrega SEMPRE, e e exatamente onde mora:

```html
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque…" />
```

Um arquivo que **declara para onde o navegador vai** nao e irrelevante.
Chamar de irrelevante era a lacuna se escondendo atras de uma palavra — o
mesmo padrao de todas as rodadas anteriores: nao um erro de logica, e um
silencio com aparencia de decisao.

**Corrigido na suite**, nao no alvo: `.html` e `.htm` entraram em
`COM_PARSER`, S-04 passou a le-los, e `codigo_efetivo` ganhou tratamento de
`<!-- -->` — sem ele, o apagador generico usaria `#`, que em HTML nao
comenta nada, e um host dentro de um comentario valeria como fato. Ha
teste-mordida dos dois lados.

### O que o btv passou a mostrar

| Achado | Arquivo | Classificacao |
|---|---|---|
| `fonts.googleapis.com` | `btv-web/index.html` | **VIOLACAO PROVAVEL** — egresso do PRODUTO |
| `fonts.gstatic.com` | `btv-web/index.html` | **VIOLACAO PROVAVEL** — egresso do PRODUTO |
| `reactjs.org` | `docs/roadmap-forge.html` | documentacao, nao produto — **do dono** |
| `github.com` | `docs/design_handoff…/*.html` | documentacao, nao produto — **do dono** |

Os dois primeiros sao o mesmo host que a camada dinamica ja tinha
observado, **agora corroborado pelas duas camadas**. Antes, um leitor podia
concluir que o egresso era coisa do navegador; ele esta declarado no
artefato entregue.

**Fato, nao veredito:** carregar fonte do Google envia o IP de todo visitante
ao Google, sem que o visitante escolha. Se o remedio e auto-hospedar a fonte,
declarar a integracao no manifesto com DPA, ou nada — **e decisao do dono**.
A suite aponta o egresso e a ausencia de registro; nao decide o remedio.

Os dois ultimos sao HTML de documentacao, e a PSE ja tratava `docs/*.js`
desse jeito (`support.js` -> `unpkg.com` ja era achado). Consistente, e
igualmente do dono decidir se documentacao entra no escopo.

---

## 5. Sobre o mapa ter "subcontado o TS"

Subcontou, e a causa era mais simples do que parecia: o documento comparava
**rotulos de linguagem**, e `TypeScript` (88) e `TypeScript/TSX` (77) sao
rotulos separados no bloco `alcance`, porque carregam ferramentas
diferentes. Comparados um a um contra `Rust` (137), o motor parecia a maior
fatia por numero de arquivos.

Somando o **estrato**:

| Estrato | Arquivos | Linhas |
|---|---|---|
| **web (JS/TS/JSX/TSX)** | **174** | 19.040 |
| Rust (motor) | 137 | **38.096** |
| Python (orquestracao) | 88 | 8.506 |
| declaracao (YAML/JSON) | 65 | 7.194 |

**Por ARQUIVOS o front e a maior fatia. Por LINHAS e o motor.** As duas sao
verdadeiras: `.rs` de motor e denso, componente de tela e curto. O mapa
passou a trazer as duas, porque trazer so linhas deixava a impressao de que
o alvo era pouco auditavel — e nao e.

O que **nao** mudou: o Rust segue com alcance a quatro vetores apenas, e 13
checks seguem meio-cegos la. Corrigir a regua de tamanho nao aumenta
cobertura nenhuma; so para de esconder a que ja existia.

---

## 6. O que a suite afirma sobre o estrato web do btv

**Afirma, com prova de leitura:** nao ha checkbox de consentimento
pre-marcado, nem PII em `localStorage`/`sessionStorage`/URL, nem token de
sessao guardado pelo cliente — em **171 dos 174** arquivos, percorrendo
1.159 elementos JSX e 5.797 chamadas. As **duas** arvores foram auditadas, e
`web/` e a maior: **104 arquivos analisados** contra 61 de `btv-web/`.

**Afirma, sobre a carga observada:** as duas SPAs carregam sem depositar
cookie; o console nao contacta terceiro; a raiz contacta
`fonts.googleapis.com`.

**Nao afirma:** nada sobre os tres arquivos nao analisados; nada sobre a
BORDA (ingress, basic auth, proxy, WAF, CDN) — o dashboard foi medido
direto; nada sobre exposicao ou risco de `/dev`, que e veredito do dono;
nada sobre o comportamento dentro do container (a imagem Docker nao pode ser
buildada neste ambiente); nada sobre os `.rs`, que tem alcance proprio e
limitado.

**O btv nao foi alterado.**
