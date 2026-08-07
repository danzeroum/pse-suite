# Rodada de reconhecimento — 6 alvos de fintech e legaltech

**Data:** 2026-08-07 · **Suíte:** pse-suite `0.3.0` ·
`catalog_hash 33d5be7e85777045d0088c3f5f7a91e394c83c4be33cfeda519b6073be0420e3`
**Modo:** `pse_inventory` (Trabalho B, estático, sem rede) · sem `--config`

> **Nenhum dos 6 repositórios-alvo foi alterado.** Clones rasos, somente leitura.
> **Nenhum check novo foi implementado.** **Nenhum bump.** A suíte segue com
> **144 testes verdes** e `--self-test` ok em clone limpo.

---

## Leia nesta ordem

| # | Documento | O que é |
|---|---|---|
| 0 | [`../ONBOARDING-NOTES.md`](../ONBOARDING-NOTES.md) | **Etapa 0** — os 29+1 checks, os 5 exit codes, os 3 estados, a doutrina. Lê-se sem conhecer o projeto |
| 1 | os 6 laudos abaixo | **Etapas 1 e 2** — reconhecimento + triagem |
| 2 | [`PROVA-NAO-FALSO-POSITIVO.md`](PROVA-NAO-FALSO-POSITIVO.md) | **Etapa 2b** — a régua não pune o crypto-shredding correto. O artefato mais importante da rodada |
| 3 | [`PROPOSTA-CHECK-PAN-PCI.md`](PROPOSTA-CHECK-PAN-PCI.md) · [`PROPOSTA-CHECK-SIGILO-LLM.md`](PROPOSTA-CHECK-SIGILO-LLM.md) | **Etapa 3** — especificação dos 2 checks. Não implementados |
| 4 | [`PENDENCIAS-DO-DONO.md`](PENDENCIAS-DO-DONO.md) | O que a PSE não pode decidir |
| 5 | [`delta-conserto.md`](delta-conserto.md) | **Rodada de conserto (v0.4.0)** — os 3 refinos que esta rodada expôs, remedidos contra os mesmos 6 alvos e os mesmos commits |

**Nota de premissa:** o enunciado descreve uma suíte de 58 checks, ~713 testes,
`RATIFICACOES.md`, `docs/matriz-dominio.md`, `E-11` e `P-18/19/20`. Nada disso
existe neste repositório — o real é v0.3.0 com 30 checks catalogados e 144 testes.
A divergência está medida e o mapeamento declarado em
[`ONBOARDING-NOTES.md`](../ONBOARDING-NOTES.md) §0. Auditei a suíte que existe.

---

## Os 6 laudos

| Alvo | Setor | Veredito | exit | Achados | CRÍT | ALTO | MÉD |
|---|---|---|---|---|---|---|---|
| [reconcilia](laudo-reconcilia.md) | fintech — reconciliação de adquirentes | `violacao` | **10** | 30 | 16 | 14 | 0 |
| [Criptotrade](laudo-Criptotrade.md) | fintech — trading cripto com agentes | `violacao` | **10** | 25 | 14 | 11 | 0 |
| [juridico-platform](laudo-juridico-platform.md) | legaltech — LegalScore / compliance | `indeterminado` | **20** | 36 | 0 | 27 | 9 |
| [Central_Inteligencia_Juridica](laudo-Central_Inteligencia_Juridica.md) | legaltech — agentes jurídicos + LLM | `violacao` | **10** | 27 | 3 | 20 | 4 |
| [giva](laudo-giva.md) | fiscal — validação NCM/ICMS | `indeterminado` | **20** | 2 | 0 | 2 | 0 |
| [dadosabedoria](laudo-dadosabedoria.md) | dados públicos / cívico | `indeterminado` | **20** | 28 | 0 | 28 | 0 |
| | | | | **148** | **33** | **102** | **13** |

Laudos brutos (JSON, evidência já sanitizada pela suíte) em [`laudos/`](laudos/).
Verificado: **zero** ocorrências de e-mail, CPF, PAN ou segredo não mascarado nos
seis arquivos.

**Nenhum alvo saiu em `0`.** Três em `10` (CRÍTICO), três em `20` (indeterminado).
Os três `20` são todos o mesmo check: **E-06 sem `fairness_dataset` declarado** —
a suíte dizendo "não consigo medir justiça aqui", e bloqueando por isso.

---

## Triagem consolidada

| Classe | Total | % |
|---|---|---|
| VIOLAÇÃO-PROVÁVEL | 52 | 35% |
| FALSO-POSITIVO-PROVÁVEL | 54 | 36% |
| INCERTO | 42 | 28% |

A atribuição é **por achado** e verificável: [`triagem.json`](triagem.json) mapeia
cada índice de finding a uma classe, e `python scripts/verificar_triagem.py`
recusa qualquer sobra, repetição ou índice inventado.

| Alvo | achados | V | F | I |
|---|---|---|---|---|
| reconcilia | 30 | 7 | 14 | 9 |
| Criptotrade | 25 | 4 | 14 | 7 |
| juridico-platform | 36 | 14 | 7 | 15 |
| Central_Inteligencia_Juridica | 27 | 10 | 10 | 7 |
| giva | 2 | 0 | 0 | 2 |
| dadosabedoria | 28 | 17 | 9 | 2 |
| **Total** | **148** | **52** | **54** | **42** |

> **Zero incerto seria suspeito.** 28% de incerto é o que sobra depois de olhar
> honestamente: agregações que talvez individualizem processo, motores de score
> cuja incerteza pode estar uma camada acima, artefatos que só são exigíveis de
> quem adotou o padrão. Nenhuma dessas perguntas se responde de fora do repositório.

Distribuição por check (`S-04` sozinho é **52% do volume** da rodada):

| Check | Achados |
|---|---|
| S-04 terceiro sem manifesto | 77 |
| P-01 PII em log | 20 |
| P-06 chave em claro | 15 |
| E-10 incerteza | 13 |
| P-04 catálogo · P-07 consentimento · P-09 k-anonimato | 6 cada |
| S-06 credencial hardcoded | 4 |
| E-07 Model Card | 1 |

---

## Fora de alcance — declarado, nunca silenciado

**Nenhum alvo tem `.java`, `.dart`, `.ex` ou `.php`.** O que ficou de fora foi outra coisa:

| Superfície | Volume | Situação |
|---|---|---|
| **`.tsx` / `.jsx`** | **281 arquivos** | **fora de alcance** — não estão em nenhum conjunto de extensões da suíte |
| `.graphql`, `.mako`, `.jsonl` | 3 | fora de alcance |

| Alvo | `.tsx`/`.jsx` não auditados |
|---|---|
| dadosabedoria | 88 |
| juridico-platform | 66 |
| reconcilia | 43 |
| Central_Inteligencia_Juridica | 33 |
| Criptotrade | 26 |
| giva | 25 |

`.ts` **está** no alcance (heurística de linha, severidade rebaixada); `.tsx` não.
Um `console.log(user.cpf)` num componente React é invisível para a suíte inteira.
Isso **não é "sem achado"** — é ausência de alcance, e está em cada laudo e em
PENDÊNCIA D-01.

---

## Etapa 2b — o resultado que mais importa

`juridico-platform/services/shared/lgpd_crypto.py` implementa crypto-shredding
AES-256-GCM por titular. **A PSE produziu zero achados nele.**

E provei que isso é decisão, não cegueira: a mesma lógica com o controle quebrado
(chave literal no lugar de `os.urandom`, mais um `deleted_at`) produz
`P-06 CRÍTICO` + `P-03 ALTO` na mesma linha.

| | arquivo certo | arquivo mutado |
|---|---|---|
| findings em `lgpd_crypto.py` | **0** | **2** |
| exit_code | 11 | **10** |

**Consequência:** nenhum check refinado, nenhum caso adicionado ao
`consumidor_bom`, nenhum bump — a condição que autorizaria alterar a suíte não se
realizou. Método completo em [`PROVA-NAO-FALSO-POSITIVO.md`](PROVA-NAO-FALSO-POSITIVO.md).

**Achado incidental, reportado honestamente:** a Etapa 2b revelou um
falso-**negativo** em P-01 — `logging.getLogger(__name__).info(...)` inline não é
detectado, porque `scan.nome_chamado` não atravessa um nó `ast.Call`. Impacto
medido nesta rodada: **zero** (o padrão ocorre 0 vezes nos 6 alvos). Registrado
em PENDÊNCIA S-04, não corrigido aqui.

---

## Etapa 3 — os dois checks propostos (especificação apenas)

Ambos nasceram do estrato: o vetor foi visto no alvo real, não deduzido de norma.

### S-09 · PAN não mascarado — `reconcilia`

A régua não tem número de cartão. A PSE auditou um sistema que processa PAN em 5
arquivos e **não disse uma palavra sobre cartão**.

**Luhn é o núcleo da especificação, e o alvo prova por quê:** as fixtures de
`test_cielo_integration.py` usam `1234567890123456789` e `9876543210987654321` —
19 dígitos, **ambos Luhn-inválidos**. Um check de "13-19 dígitos" produziria 2
CRÍTICOs falsos só ali. A régua proposta exige **Luhn + faixa de BIN + comprimento
coerente com a bandeira** — três condições independentes.

E o cuidado D-08 é literal: o alvo faz certo (`card_last_4`, fixtures
`************1234`), então **o veredito esperado hoje é zero achados**. Um check
que nasce reconhecendo o tratamento correto e fica de guarda é o que esta suíte quer.

→ [`PROPOSTA-CHECK-PAN-PCI.md`](PROPOSTA-CHECK-PAN-PCI.md)

### E-11 · Sigilo jurídico em LLM — `juridico-platform`, `Central`

`defensor/orchestrator.py:78-84` interpola nome do reclamante, nome da reclamada e
a narrativa dos fatos num prompt → `generate_text()` (sem nenhuma redação) →
`api.openai.com` **por default** (`config.py:102`).

S-04 pegou o **host**. Ninguém olha o **conteúdo do prompt**. E `pii-patterns.yaml`
não tem uma linha sobre segredo de justiça ou sigilo da advocacia.

O contraste que define a especificação está em `Central`: `redact_pii()` existe e
é chamado de verdade — em persistência e trilha de auditoria — mas **não** em
`llm_client.py:35`. O alvo protege o que armazena e não o que envia ao modelo.
Um check de "existe redação no repositório?" ficaria verde e estaria errado.

E o check **não pode escolher** entre os ramos `openai`/`ollama` decididos em
runtime: fica `CheckIndeterminado`, que bloqueia — nem verde falso, nem CRÍTICO forçado.

→ [`PROPOSTA-CHECK-SIGILO-LLM.md`](PROPOSTA-CHECK-SIGILO-LLM.md)

---

## O que fica para o dono

12 pendências em [`PENDENCIAS-DO-DONO.md`](PENDENCIAS-DO-DONO.md), mais 5 refinos
candidatos da própria suíte. Ordem recomendada:

1. **S-01** — 18 dos 19 CRÍTICOs de credencial estão sob `tests/`. Em `Central`, os
   3 CRÍTICOs que produzem o `exit 10` são **todos** fixtures: o veredito do laudo
   está sendo dirigido por falso-positivo. É o cenário D-08 acontecendo agora.
2. **D-01** — 281 arquivos de frontend invisíveis.
3. **A-01 / A-02** — destravam a implementação dos dois checks propostos.

---

## Reprodução

```bash
pip install -e ".[dev]" && pytest                 # 144 verdes
pse --self-test                                   # 29 mutações canônicas reprovam

for r in reconcilia Criptotrade juridico-platform \
         Central_Inteligencia_Juridica giva dadosabedoria; do
  git clone --depth 1 "https://github.com/danzeroum/$r.git" "alvos/$r"
  pse --path "alvos/$r" --output "laudos/laudo-$r.json"
done
```
