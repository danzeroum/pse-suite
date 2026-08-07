# Triagem dos achados `.rs` no `danzeroum/btv`

> Escrito a mao, e nao gerado — triagem e julgamento, e julgamento precisa de
> assinatura. Os NUMEROS vieram de instrumentacao reproduzivel; a
> classificacao de cada caso e leitura do contexto.
>
> **Alvo:** `danzeroum/btv` @ `a3e14f45` (clone limpo) · **suite:** 0.14.0 →
> 0.14.2 · **data:** 2026-08-07 · **duas rodadas de triagem**
>
> **A PSE aponta; o dono valida.** Este documento nao decide nada sobre o
> btv. Ele separa o que a suite afirma do que ela nao consegue afirmar, e
> devolve a lista para julgamento.

---

## Resumo: a premissa da rodada nao se confirmou

A tarefa partia de que os quatro checks *acharam algo* contra o btv. Nao
acharam. **Zero achados `.rs`, e dois dos quatro nem chegaram a rodar.**

| Check | Estado no laudo | Achados `.rs` |
|---|---|---|
| `S-06` chave hardcoded | **executou** | 0 |
| `P-19` evento sem crypto-shredding | **executou** | 0 |
| `P-18` campo sensivel sem cifra | **pulado** — btv nao tem catalogo de dados | — |
| `S-16` persistencia fora da jurisdicao | **pulado** — btv nao declara `data_residency` | — |

Zero achado nao e um resultado; e uma afirmacao, e uma afirmacao precisa de
prova. A triagem virou, entao, duas perguntas:

1. **Os checks realmente olharam?** (senao "zero" e falha silenciosa)
2. **O que eles CONSIDERARAM e descartaram?** (e ali que o grep fragil erra)

A segunda pergunta e a que deu retorno: **nenhum achado, mas quatro padroes
de falso-positivo latentes** — formas que os checks consideravam candidatas e
nao deveriam. Nenhuma virou achado no btv **por sorte**, porque nenhum nome
de PII caiu no span. Sorte nao e controle.

### Contagem honesta dos tres grupos

| Classificacao | Quantidade |
|---|---|
| **VIOLACAO PROVAVEL** | **0** |
| **FALSO-POSITIVO PROVAVEL** | **0** achados · **7 padroes latentes corrigidos** |
| **INCERTO — precisa do dono** | **4** (2 checks pulados + 2 sondas hipoteticas) |

Zero incerto seria suspeito num grep fragil. Nao ha zero incerto: ha quatro,
listados no fim, e dois deles so o dono resolve.

---

## 1. A prova de que os checks olharam

Sem isto, "zero achados" e indistinguivel de "o scanner nunca alcancou os
arquivos" — a mesma familia de defeito que o bloco `alcance` existe para
impedir, um nivel abaixo.

### `S-06` — instrumentacao do funil

```
arquivos .rs varridos : 137
ligacoes encontradas  : 3225
  nome de credencial  :    5
  com literal         :    1
  literal >= 16 chars :    0   <- por isso zero achados
```

O scanner leu 137 arquivos e reconheceu 3.225 ligacoes `let`/`const`/
`static`. O funil fecha por um motivo verificavel, nao por ausencia de
leitura.

### `S-06` — sonda cega, para testar se a REGUA e o gargalo

A lista de nomes de credencial poderia ser o limitador: uma chave numa
ligacao chamada `chave_do_parceiro` escaparia. Entao rodei uma varredura
**sem filtro de nome** — todo literal de 16+ caracteres em qualquer ligacao
`.rs`, procurando formato conhecido de credencial ou alta entropia:

```
resultado: 0
```

**Nao ha literal com forma de segredo em nenhuma ligacao Rust do btv, com
nome nenhum.** O zero de S-06 e real, e nao um artefato da regua.

### `P-19` — alcance

```
chamadas de producao consideradas: 161, em 18 arquivos
```

O check considerou 161 chamadas e descartou todas por ausencia de nome de
PII no span. Olhou de verdade.

### `S-16` — sonda com politica HIPOTETICA

S-16 pulou porque o btv nao declara `data_residency`, e supor uma jurisdicao
seria a suite decidindo pelo consumidor. Para a triagem, rodei com
`data_residency: BR` **hipotetico**:

```
achados S-16 (sonda, NAO e laudo): 0
```

Nao ha literal de regiao em chamada de conexao no `.rs` do btv. Se o dono
declarar a politica, o check continua limpo — **mas essa afirmacao vale
para `.rs`, nao para o Terraform**, que segue fora de alcance.

---

## 2. Os quatro padroes de falso-positivo — corrigidos no CHECK

Nenhum destes gerou achado no btv. Todos eram candidatos considerados, e
**num repositorio cujo canal carregasse uma struct com `cpf`, os quatro
teriam disparado.** Corrigidos na regua e no scanner — vale para todo Rust
futuro, nao so para o btv.

### (a) DEFINICAO de funcao tratada como chamada — *o mais grave*

**Evidencia** — `crates/btv-cli/src/session.rs:37`:

```rust
fn append(&mut self, kind: &str, payload: Value) -> anyhow::Result<()> {
```

O regex de chamada casava `append(` e varria a **assinatura** como se fosse
um span de argumento. Num arquivo com `fn append(&mut self, cpf: &str)`, o
check acusaria a **propria declaracao da funcao** — um achado que nao tem
como ser corrigido, porque nao ha defeito nenhum ali.

Afeta os quatro checks: `fn connect(...)` viraria chamada de persistencia em
S-16 pelo mesmo caminho.

**Correcao:** `rustscan.chamadas()` nao devolve mais definicoes.
**Caso permanente:** `consumidor_rust_bom/src/barramento.rs` e o `fn connect`
acrescentado a `persistencia.rs`.

### (b) Canal tokio contado como barramento append-only

**Evidencia** — `crates/btv-cli/src/squad_agent.rs:178`:

```rust
let _ = tx.send(event);
```

O btv tem um **ledger no dominio**, entao a marca `ledger` aparece em 18
arquivos — e a regra *"o modulo fala com barramento"* tornava elegivel todo
`send` daqueles arquivos. **142 dos 161 candidatos eram elegiveis SO pelo
modulo.** Um `send` de canal nao e escrita em registro imutavel: o Art. 18 VI
nao tem nada a dizer sobre ele.

**Correcao:** o fallback pelo modulo passou a exigir receptor, e a excluir
receptores reconhecidamente nao-barramento (`tx`, `sender`, `builder`,
`responder`, `stream`, …), em regua — nunca no `.py`.

### (c) Canal com nome sufixado sobreviveu ao primeiro refino

**Evidencia** — `crates/btv-cli/src/squad_agent.rs` e outros:

```rust
let _ = agent_evt_tx.send(event);
```

O casamento por token exato (`tx`) nao alcanca o sufixo em `agent_evt_tx`.
**Oito destes sobreviveram** ao refino (b). Achado porque eu remedi de novo
depois de corrigir — nao porque o primeiro refino pareceu suficiente.

**Correcao:** casamento por token com prefixo (`nome_casa_tokens`).

### (d) Variante de enum contada como chamada de metodo

**Evidencia** — `crates/btv-cli/src/tui_app.rs`:

```rust
let _cmd = UiCommand::Send(payload);
```

Construcao de variante, nao chamada. Em Rust idiomatico metodo e
`snake_case` e variante e `CamelCase`.

**Correcao:** P-19 ignora chamada cujo ultimo segmento comeca com maiuscula.

### Efeito medido dos quatro refinos

```
candidatos P-19 no btv:  161  ->  114  ->  98
achados P-19 no btv:       0  ->    0  ->   0   (inalterado)
achados na fixture ruim:   1  ->    1  ->   1   (inalterado)
```

O refino cortou 39% dos candidatos **sem trocar falso-positivo por
falso-negativo** — ha teste-mordida provando que o produtor legitimo
(`ledger.append`) continua mordendo.

---

## 2b. SEGUNDA RODADA — os candidatos de `P-18`

A primeira rodada olhou os candidatos de `P-19`. A segunda olhou os de
`P-18`, e achou o falso-positivo **mais numeroso** do alcance inteiro.

### (e) LEITURA contada como persistencia — 10 dos 17 sites

**Evidencia** — `crates/btv-store/src/btv.rs:556`:

```rust
self.conn.query_row(
    "SELECT created_ts, email, nome FROM users WHERE id = ?1",
    params![id],
    |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?)),
)
```

P-18 pergunta se um campo sensivel e **GRAVADO** sem cifra. Um `SELECT` nao
grava nada. Acusar este site produziria um achado que o time nao consegue
corrigir — nao ha escrita ali para consertar.

**Correcao:** `query_row`, `query_map`, `query_as`, `query_scalar`,
`fetch_*`, `recall` e afins deixam de contar como escrita.

### (f) …mas o NOME nao pode decidir sozinho — e o btv provou

**Evidencia** — `crates/btv-store/src/pg.rs:715`:

```rust
let id: i64 = sqlx::query_scalar(
    "INSERT INTO users (tenant_id, nome, email, papel, ativo, created_ts, pin_hash)
     VALUES ($1, $2, $3, $4, true, $5, $6) RETURNING id",
)
```

Nome de **leitura**, SQL de **escrita**. Uma lista de nomes proibidos,
sozinha, teria produzido **falso-negativo no site que mais importa** —
trocando um defeito por outro pior.

**Correcao:** o verbo do SQL vence o nome da chamada; o nome so decide
quando nao ha SQL no span. Ha teste-guarda na regua contra esvaziar
`verbos_sql_de_escrita`.

### (g) `PASSWORD` como palavra-chave do SQL, nao como coluna

**Evidencia** — `crates/btv-store/src/pg.rs:1276`:

```rust
sqlx::query(
    "DO $$ BEGIN
         CREATE ROLE btv_app_teste LOGIN PASSWORD '<mascarado>'
             NOSUPERUSER NOBYPASSRLS;
     EXCEPTION WHEN duplicate_object THEN NULL; END $$",
)
```

`password` casou como campo sensivel estando ali como **palavra-chave do
SQL**. Administrar role de banco e assunto de S-15; um achado de P-18 aqui
mandaria o time cifrar uma keyword.

**Correcao:** DDL de role/user (`CREATE ROLE`, `ALTER USER`, `GRANT`, …)
sai do escopo de P-18.

### O embrulho de cifra opaco — INDETERMINADO, nao achado nem verde

A triagem nomeou *"cifra em outra linha"*. As duas formas realistas ja eram
suprimidas pela varredura de cifra do repositorio inteiro (ha teste). Sobrou
uma terceira, que **nao e decidivel**:

```rust
let blob = to_ciphertext(&t.cpf);            // embrulho da casa, fora da regua
sqlx::query("INSERT INTO t (cpf) VALUES ($1)").bind(&blob).execute(p);
```

A coluna esta no literal e o valor vem de um identificador que a regua nao
reconhece como cifra. **A regua nao e editavel pelo consumidor** — entao
inventar achado puniria quem cifrou, e inventar verde absolveria quem nao
cifrou. Terceira saida, a mesma de `env!` em S-06: **CheckIndeterminado com
motivo**, dizendo o que torna o site decidivel.

Quando o campo aparece FORA do literal (`.bind(&t.cpf)`), o valor cru esta
ali e nao ha ambiguidade — vira achado. Ha teste-mordida dos dois lados.

### Efeito medido da segunda rodada

```
sonda P-18 no btv (sem o portao do catalogo):
  candidatos     17
  ELIMINADOS     11   10 leituras + 1 DDL de role
  SOBREVIVEM      6   escritas de verdade
```

Os seis sobreviventes, todos gravando `email`:

| Arquivo | Linha | Chamada |
|---|---|---|
| `crates/btv-store/src/btv.rs` | 64 | `conn.execute_batch` |
| `crates/btv-store/src/btv.rs` | 521 | `self.conn.execute` |
| `crates/btv-store/src/btv.rs` | 1142 | `self.conn.execute` |
| `crates/btv-store/src/pg.rs` | 715 | `sqlx::query_scalar` (INSERT) |
| `crates/btv-store/src/pg.rs` | 721 | `bind` |
| `crates/btv-store/tests/migracao_pre_tenant.rs` | 75 | `conn.execute_batch` |

**Estes seis NAO sao achados.** P-18 esta pulado no btv, e continua pulado —
sem catalogo nao ha promessa a confrontar. Eles sao a resposta a pergunta
*"o que P-18 olharia se o btv declarasse catalogo"*, e ficam como **INCERTO
(i)**, nao como violacao.

---

## 2c. O laudo do btv, estabilizado

Reprocessado apos as duas rodadas de refino:

| | v0.14.0 (antes) | v0.14.2 (depois) |
|---|---|---|
| exit code | 20 | 20 |
| checks executados | 29 | 29 |
| achados totais | 6 | 6 |
| **achados `.rs`** | **0** | **0** |

**O laudo nao mudou uma virgula.** Os refinos cortaram CANDIDATOS, nao
achados — porque o btv nao tinha nenhum. O ganho e para o proximo alvo Rust,
nao para este:

```
candidatos P-19:  161 -> 98   (-39%)
candidatos P-18:   17 ->  6   (-65%)
achados no btv:     0 ->  0   (inalterado)
achados na fixture ruim: os 4 continuam disparando
```

Essa ultima linha e a trava contra o modo de falhar obvio de um refino:
cortar demais e trocar falso-positivo por falso-negativo.

---

## 3. INCERTO — o que so o dono resolve

### (i) `P-18` nunca rodou: o btv nao tem catalogo de dados

O check e ancorado no catalogo por construcao — sem inventario declarado nao
ha campo sensivel a confrontar, e inventar um seria a suite decidindo pelo
consumidor. **Pulado com motivo, cobrado por P-04.**

Para dimensionar o que ele encontraria, rodei a metade mecanica **sem o
portao do catalogo** (isto NAO e laudo):

```
persistencia .rs carregando nome de campo sensivel/PII no span: 17 sites
```

**Evidencia representativa** — `crates/btv-store/src/btv.rs:521`:

```rust
self.conn.execute(
    "INSERT INTO users (nome, email, papel, ativo, created_ts, pin_hash)
     VALUES (?1, ?2, ?3, 1, ?4, ?5)",
    params![nome, email, papel, now, pin_hash],
)?;
```

`email` e `nome` sao gravados em claro. **Isto pode ou nao ser violacao** —
depende de o btv classificar `email` como pessoal comum ou sensivel, e de
haver ou nao promessa de cifra. Sem catalogo, nao ha promessa a confrontar.

**Pergunta ao dono:** o btv vai declarar `tests/qa/catalog.yaml`? Se sim,
P-18 passa a decidir esses 17 sites; se nao, ele continua pulando com motivo
— e essa e uma resposta legitima, nao uma lacuna.

Um dos 17 e ruido demonstravel — `crates/btv-sidecar/src/service.rs:512`:

```rust
let recall = client1
    .recall("problema de login e senha", 3)
```

`senha` aparece dentro de uma **string de teste em portugues**, nao como
nome de campo. Nao virou achado porque a sonda foi rodada sem o portao do
catalogo; **o check real, gated pelo catalogo, nunca consideraria este
site.** Fica registrado como evidencia de que o portao e o que da precisao a
P-18 — nao um defeito a corrigir.

### (ii) `S-16` nunca rodou: o btv nao declara `data_residency`

Mesma natureza. A sonda com politica hipotetica `BR` deu zero em `.rs`, mas
a jurisdicao do btv pode estar declarada fora do repositorio, e a
infraestrutura vive em **Terraform, que segue fora de alcance**.

**Pergunta ao dono:** qual e a residencia declarada do btv, e onde ela vive?

### (iii) `const TOKEN_OK: &str = "btvs_valido"` — descartado por tamanho

**Evidencia** — `crates/btv-cli/src/tenant_border_sweep.rs:37`:

```rust
const TENANT_OK: &str = "00000000-0000-0000-0000-00000000e154";
const TOKEN_OK: &str = "btvs_valido";
```

Nome de credencial (`TOKEN_OK`) com literal de 11 caracteres — **abaixo do
minimo de 16**, entao nao virou achado. Lendo o contexto: e um `MockResolver`
de teste de fronteira de tenant, e o valor e obviamente sintetico. Classifico
como **falso-positivo evitado corretamente**, nao como achado perdido.

Fica listado como INCERTO por honestidade sobre o mecanismo: ele foi
descartado por **tamanho**, nao por a suite ter entendido que e teste. Um
token real de 11 caracteres escaparia pela mesma porta. O dono decide se
esse limiar e aceitavel.

### (iv) `token_hash = sha256_hex(&token)` — fora do escopo destes quatro

**Evidencia** — `crates/btv-store/src/pg.rs:1065`:

```rust
let token = format!("btvs_{}", URL_SAFE_NO_PAD.encode(bytes));
let token_hash = btv_schemas::sha256_hex(&token);
```

Token gerado em execucao por CSPRNG e guardado so como hash — **o
comportamento correto**, e S-06 acertou em nao acusar.

Registro porque toca o vetor de **P-20** (hash deterministico sem chave
tratado como anonimizacao), e P-20 **nao tem alcance a `.rs`**. Aqui o hash
e de um segredo aleatorio de 256 bits, nao de um identificador de titular —
provavelmente correto. Mas quem afirma isso sou eu lendo, nao um check.
**Fica para o dono, e para uma eventual rodada que estenda P-20.**

---

## 4. Nenhum segredo replicado

Nenhum trecho acima carrega credencial em claro, porque **nao havia
nenhuma**: a sonda cega deu zero. Os unicos literais citados sao um UUID de
tenant de teste (`0000…e154`) e um token de fixture (`btvs_valido`), ambos
sinteticos e ja publicos no repositorio do btv. Ha teste que reprova este
documento se algum trecho com forma de credencial entrar nele.

---

## 5. O que a suite afirma, e o que ela nao afirma

**Afirma, com prova de leitura:**

* nao ha credencial hardcoded em ligacao Rust do btv (137 arquivos, 3.225
  ligacoes, sonda cega tambem zerada);
* nao ha producao de evento carregando nome de PII no payload (98 chamadas
  consideradas apos o refino);
* nao ha literal de regiao em chamada de conexao `.rs`.

**Nao afirma:**

* nada sobre cifra de campo sensivel — P-18 nao rodou (sem catalogo);
* nada sobre jurisdicao declarada — S-16 nao rodou (sem politica), e o
  Terraform segue fora de alcance;
* nada sobre os outros 53 checks no Rust do btv — 13 seguem meio-cegos la,
  como `docs/cobertura-btv.md` registra;
* nada sobre PII que chegue ao payload por **dois** saltos, campo de struct
  ou outro modulo — o alcance textual resolve UM salto, e isso e lacuna
  conhecida.

**O btv nao foi alterado.** Nenhum achado foi descartado sem classificacao.
