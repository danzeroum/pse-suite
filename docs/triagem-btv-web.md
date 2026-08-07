# Triagem do estrato web (`.ts` / `.tsx`) no `danzeroum/btv`

> Escrito a mao. Os NUMEROS vieram de instrumentacao reproduzivel; a
> classificacao e leitura de contexto.
>
> **Alvo:** `danzeroum/btv` @ `a3e14f45` (clone limpo) · **suite:** 0.15.1 ·
> **data:** 2026-08-07 · **duas superficies medidas**
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
| **VIOLACAO PROVAVEL** | **0** |
| **FALSO-POSITIVO PROVAVEL** | **2** (S-21 nas duas superficies — ver 4b) |
| **INCERTO — precisa do dono** | **5** (3 arquivos + S-19 + arranjo de `/dev`) |

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

### Limite desta medicao, declarado

O console foi servido em **porta propria** (Vite em `127.0.0.1:5179`), e nao
aninhado em `/dev` atras do servidor Rust. Origem separada em vez de origem
compartilhada: cookie, `SameSite` e cabecalho podem diferir do arranjo real.
Para medir o arranjo de producao seria preciso subir a imagem Docker com as
duas `dist` buildadas — **pendencia registrada, nao presumida limpa**.

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
postura de PRODUCAO das duas SPAs (o que foi observado foi dev server);
nada sobre `/dev` no arranjo real (origem compartilhada atras do servidor
Rust); nada sobre exposicao ou risco de `/dev` — isso e veredito do dono;
nada sobre os `.rs`, que tem alcance proprio e limitado.

**O btv nao foi alterado.**
