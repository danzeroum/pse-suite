# Delta do conserto — os 6 alvos, remedidos

**Antes:** pse-suite `0.3.0` · `catalog_hash 33d5be7e…` · laudos em [`laudos/`](laudos/)
**Depois:** pse-suite `0.4.0` · `catalog_hash 0654bdc1…` · laudos em [`laudos-pos-conserto/`](laudos-pos-conserto/)

> **Os 6 repositórios-alvo não foram alterados, e não se moveram.** As duas
> medições rodaram contra o **mesmo `repo_commit`** em todos os seis — está
> nos dois conjuntos de laudo, campo `artifact.repo_commit`. O delta abaixo é
> **inteiramente da suíte**. Se um alvo tivesse recebido um commit entre as
> duas rodadas, o número misturaria conserto com mudança de código alheio, e
> não diria nada.
>
> **Os achados continuam sendo veredito do dono.** Esta rodada consertou a
> régua (verificação); classificar cada achado segue sendo validação, e não
> foi tocada.

---

## O quadro

| Alvo | Antes | Depois |
|---|---|---|
| reconcilia | `violacao` **10** · C16 A14 M0 · n=30 | `violacao` **10** · C7 A14 M6 · n=27 |
| Criptotrade | `violacao` **10** · C14 A11 M0 · n=25 | `violacao` **10** · C5 A12 M9 · n=26 |
| juridico-platform | `indeterminado` **20** · C0 A27 M9 · n=36 | `indeterminado` **20** · C0 A28 M9 · n=37 |
| **Central_Inteligencia_Juridica** | `violacao` **10** · C3 A20 M4 · n=27 | **`indeterminado` 20** · C0 A20 M7 · n=27 |
| giva | `indeterminado` **20** · C0 A2 M0 · n=2 | `indeterminado` **20** · C0 A2 M0 · n=2 |
| dadosabedoria | `indeterminado` **20** · C0 A28 M0 · n=28 | `indeterminado` **20** · C0 A31 M0 · n=31 |
| **TOTAL** | **C33** A102 M13 · n=148 | **C12** A107 M31 · n=150 |

**21 CRÍTICOs a menos. Nenhum achado perdido** — 18 foram rebaixados para
MÉDIO e continuam no laudo; 3 eram e-mail de domínio reservado e deixaram de
ser acusados.

---

## Refino 1 — credencial em caminho de teste (S-01)

**18 CRÍTICOs rebaixados para MÉDIO** — 14 de P-06 e 4 de S-06 — e **nenhum
suprimido**. Todos continuam no laudo, com a descrição dizendo por que foram
rebaixados.

| Alvo | Rebaixados |
|---|---|
| Criptotrade | 9 |
| reconcilia | 6 |
| Central_Inteligencia_Juridica | 3 |

### O caso que mais importa

**`reconcilia/scripts/generate_test_password.py:9` continua em `CRITICO`.**

É o 19º dos 19 — o único fora de `tests/`, com valor não-sintético. Ele foi
cegado **duas vezes** durante esta rodada, e as duas só apareceram porque os
alvos foram remedidos:

1. a marca `test_` casava em qualquer posição do nome do arquivo, e
   `generate_test_password.py` virava "arquivo de teste". A régua passou a
   declarar a posição: `/x/` diretório, `^x` prefixo, `x$` sufixo do radical.
2. corrigido isso, a marca `password` casava **dentro** do valor real
   `SecurePassword123!`. A marca passou a exigir fronteira — `_` e `-` são
   fronteira, letra e dígito não.

O teste que guardava esse caso passava nas duas vezes, porque usava um literal
inventado. Fixture inventada prova o que quem a escreveu já imaginava; o valor
que está lá agora é o verdadeiro, copiado do alvo.

### Central_Inteligencia_Juridica: `10` → `20`

Os três CRÍTICOs que produziam o exit 10 eram **todos fixtures**. Com eles em
MÉDIO, o veredito passou a ser `indeterminado` — e o motivo é **E-06 sem
`fairness_dataset` declarado**, que é a suíte dizendo "não consigo medir
justiça aqui".

O alvo não ficou verde. Ele passou a bloquear **pelo motivo certo**, e esse é
o resultado da rodada inteira: antes, o CI parava por causa de um
`test-secret`; agora para porque a suíte não conseguiu decidir uma coisa que
importa.

---

## Refino 2 — `.tsx` e `.jsx` (D-01)

**281 arquivos saíram da invisibilidade.** O censo bate exatamente com o que a
rodada de reconhecimento mediu.

| Alvo | `.tsx` | `.jsx` | (já cobertos: `.ts` / `.js`) |
|---|---|---|---|
| dadosabedoria | 81 | 7 | 29 / 2 |
| juridico-platform | 66 | 0 | 31 / 3 |
| reconcilia | 43 | 0 | 35 / 1 |
| Central_Inteligencia_Juridica | 0 | 33 | 0 / 12 |
| Criptotrade | 0 | 26 | 1 / 21 |
| giva | 25 | 0 | 17 / 0 |
| **TOTAL** | **215** | **66** | 113 / 39 |

**5 achados novos**, todos S-04 (host de terceiro), todos em arquivos que a
suíte nunca tinha aberto:

| Alvo | Arquivo |
|---|---|
| dadosabedoria | `web/components/AcoesIVM.tsx` · `web/app/desenvolvedores/page.tsx` |
| juridico-platform | `frontend/apps/platform/app/(shell)/defensor/page.tsx` |
| Criptotrade | `docs/design/pages/screen_notifications.jsx` |

**Cinco achados em 281 arquivos é pouco, e não é o ponto.** O valor não está
nos 5: está em que "nenhum achado de P-01 nos componentes" passou a significar
*olhei e está limpo*, quando antes significava *não abri nenhum*. Silêncio que
parece verde é o pior defeito que um laudo pode ter — e este era da própria
suíte.

### O que segue invisível, nomeado

**6 arquivos `.mjs`/`.cjs`** (juridico-platform 2, dadosabedoria 2, Criptotrade
1, giva 1). Mesma linguagem, mesma heurística, e fora do pedido desta rodada.
Entram em `scan.ECMASCRIPT` no dia em que alguém decidir — não em silêncio.

---

## Refino 3 — domínio reservado (S-02)

**3 achados de P-01 deixaram de ser emitidos**, todos `test@example.com`
literal em script de seed, todos em `reconcilia`:

| Arquivo | Linha |
|---|---|
| `scripts/seed_mvp.py` | 96 |
| `scripts/seed_mvp.py` | 105 |
| `scripts/seed_test_user.py` | 83 |

E `example.com` **já estava** na lista `ignorar` de
`third-party-endpoints.yaml` desde sempre, consultada por S-04. A régua dizia
coisas opostas sobre o mesmo domínio, dependendo de qual check a lia.

**Nada de PII real foi afrouxado**, e é o que os testes de mordida guardam:
`user.email` vindo de variável segue em CRÍTICO; CPF e telefone não têm
equivalente reservado; e um payload com um e-mail reservado **e** um vivo
continua sendo achado — senão a forma mais fácil de esconder um e-mail real
seria pôr um `@example.com` ao lado.

---

## O que a medição corrigiu no próprio conserto

Vale registrar, porque é o argumento para remedir sempre:

- o **19º caso** foi cegado duas vezes, e nenhuma das duas apareceu na suíte
  de testes — só no reprocessamento;
- **S-04 pareceu perder 5 achados** numa primeira leitura do delta. Não
  perdeu: o check deduplica por host e guarda o **primeiro** arquivo em ordem;
  com `.tsx`/`.jsx` no alcance, a âncora de alguns hosts mudou de arquivo. A
  comparação por `(check, arquivo, linha)` leu isso como perda. Refeita por
  identidade de host: **zero hosts perdidos**.

---

## Reprodução

```bash
pip install -e ".[dev]" && pytest        # 188 verdes
pse --self-test                          # 30 mutações canônicas reprovam

for r in reconcilia Criptotrade juridico-platform \
         Central_Inteligencia_Juridica giva dadosabedoria; do
  git clone --depth 1 "https://github.com/danzeroum/$r.git" "alvos/$r"
  pse --path "alvos/$r" --output "laudos-pos-conserto/laudo-$r.json"
done
```

Confira `artifact.repo_commit` contra [`laudos/`](laudos/) antes de comparar:
se um alvo se moveu, o delta deixou de ser da suíte.
