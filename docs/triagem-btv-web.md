# Triagem do estrato web (`.ts` / `.tsx`) no `danzeroum/btv`

> Escrito a mao. Os NUMEROS vieram de instrumentacao reproduzivel; a
> classificacao e leitura de contexto.
>
> **Alvo:** `danzeroum/btv` @ `a3e14f45` (clone limpo) · **suite:** 0.15.0 ·
> **data:** 2026-08-07
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
| **FALSO-POSITIVO PROVAVEL** | **0** |
| **INCERTO — precisa do dono** | **3** |

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

**(ii) `web/src/api/squad.ts`** — mesma situacao. Note que ha **duas** arvores
de front no repositorio (`btv-web/` e `web/`), e as duas tem `api/squad.ts`.
*Pergunta ao dono:* `web/` esta ativo ou e resto de migracao? Se for resto,
sai do alvo e a lacuna some sozinha.

**(iii) `web/src/components/screens/user/Designer/PropertiesPanel.tsx`** —
nao analisado. Tela de designer; a gramatica falha na linha 35 pela versao
tsx e na linha 1 pela de typescript.

Nenhum dos tres e achado. Sao **lacunas nomeadas** — a diferenca entre
"olhei e esta limpo" e "nao olhei" continua sendo o ponto.

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
1.159 elementos JSX e 5.797 chamadas.

**Nao afirma:** nada sobre os tres arquivos nao analisados; nada sobre
comportamento que so aparece em execucao (isso e a camada dinamica); nada
sobre os `.rs`, que tem alcance proprio e limitado.

**O btv nao foi alterado.**
