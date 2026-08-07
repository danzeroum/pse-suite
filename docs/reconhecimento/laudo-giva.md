# Laudo de reconhecimento — `danzeroum/giva`

**Setor:** legaltech / fiscal — validação e enriquecimento de planilhas NCM/ICMS.
**Commit auditado:** `6daea35fc1a6de5aabea91ae2a57712551244c7b` (clone raso)
**Suíte:** pse-suite `0.3.0` · `catalog_hash 33d5be7e…20e3` · modo `pse_inventory`
**Laudo bruto:** [`laudos/laudo-giva.json`](laudos/laudo-giva.json)

> A PSE afirma; o dono valida. Nenhum arquivo deste repositório foi alterado.

---

## 1. Veredito

| | |
|---|---|
| **veredito** | `indeterminado` |
| **exit_code** | **20** (bloqueia igual a violação) |
| findings | 2 — 0 CRÍTICO, 2 ALTO |
| duração | 1,01 s |

**Este é o laudo mais silencioso da rodada — e o que mais exige cuidado de leitura.**
Dois achados, ambos de "artefato declarativo ausente", zero CRÍTICO. A tentação é
ler isso como "está limpo". Não é o que o laudo diz. Ver §3.

---

## 2. Os três estados

**AUDITADO (13):** `E-00, E-04, E-05, E-07, E-10, P-01, P-03, P-04, P-06, P-07, P-09, S-04, S-06`

**NÃO-APLICÁVEL (4):** P-02, P-08 (catálogo ausente → P-04) · S-05, S-08 (manifesto ausente → S-04)

**FORA-DE-ALCANCE / INDETERMINADO (1):** E-06 — nenhum `fairness_dataset` declarado.
É este check, sozinho, que faz o alvo sair em **exit 20** em vez de 11.

**NÃO-HABILITADO (10):** todo o Trabalho A. **PREVISTO (1):** E-08.

### FORA-DE-ALCANCE por linguagem

| Superfície | Volume | Estado |
|---|---|---|
| `.py` | 79 | **auditado** (AST) |
| `.ts` | 17 | auditado — heurística, severidade rebaixada |
| **`.tsx`** | **25** | **FORA-DE-ALCANCE** |

Sem `.java` / `.dart` / `.ex` / `.php`. Sem `.sql` — logo P-02/P-03/P-09 tiveram
apenas os `.py` para olhar.

**Proporção que importa:** 25 `.tsx` fora de alcance contra 79 `.py` auditados.
Aproximadamente **um quarto da superfície de código** do alvo não foi olhado.
Num laudo com só 2 achados, isso deixa de ser rodapé e vira a informação principal.

---

## 3. Como ler um laudo quase vazio

O `exit 20` está correto e é o desfecho mais informativo aqui. Decomposto:

- **13 checks rodaram e decidiram** — houve auditoria de verdade sobre 79 `.py`.
  P-01, P-06, S-06, E-04, E-05, P-03 executaram e **não acharam nada**. Isso é
  AUDITADO com resultado negativo, e é uma afirmação positiva sobre o alvo: não há
  PII crua em log, não há chave literal, não há decisão de alto impacto sem rota
  humana, não há proxy de discriminação em score, não há soft-delete.
- **4 checks são N/A declarado** — em cascata, por falta de catálogo e manifesto.
- **1 check é indeterminado** — e é o que bloqueia.
- **25 arquivos não foram olhados por ninguém.**

> "Poucos achados" ≠ "conforme". O laudo diz `indeterminado`, não `conforme`, e a
> diferença entre os dois é exatamente a doutrina desta suíte.

**Contexto do domínio, que sustenta a leitura otimista:** o README descreve GIVA
como validação de **planilha fiscal (NCM · Período · Descrição · UF)** com
proveniência auditável. O insumo primário é **classificação fiscal de mercadoria**,
não dado de pessoa natural. Se essa leitura estiver certa, boa parte do pacote de
privacidade é legitimamente inaplicável aqui — mas essa é uma conclusão do **dono**,
não da suíte. → PENDÊNCIA D-03.

---

## 4. Triagem dos achados

### 4.1 VIOLAÇÃO-PROVÁVEL (0)

Nenhuma. Nenhum achado deste alvo aponta para um fato do código.

### 4.2 FALSO-POSITIVO-PROVÁVEL (0)

Nenhum. Os dois achados são apontamentos legítimos de artefato ausente — a régua
não errou, ela cobrou algo que de fato não existe.

### 4.3 INCERTO (2)

| # | Achado | Arquivo:linha | Por que não decido |
|---|---|---|---|
| 1 | **P-04 ALTO** — catálogo de dados ausente | `tests/qa/catalog.yaml:1` | O caminho é o **default da suíte**, não uma declaração deste repositório — ele nunca se propôs a ser consumidor da PSE. Cobrar o Art. 37 de quem não adotou o padrão é cobrar adoção, não conformidade. Só vira violação se o alvo tratar dado pessoal, e o domínio (NCM/ICMS) sugere que talvez não trate |
| 2 | **P-07 ALTO** — modelo de consentimento ausente | `tests/qa/consent-model.yaml:1` | Idem. E com um argumento de mérito adicional: validação fiscal opera sobre **obrigação legal / execução de contrato**, bases em que consentimento pode corretamente não existir |

**Zero incerto seria suspeito.** Aqui o incerto é 100% — e é honesto: os dois
únicos achados dependem de uma resposta que não está no repositório.

---

## 5. Achado sobre a suíte, não sobre o alvo

Este alvo expõe uma característica estrutural que vale registrar:

**P-04 e P-07 disparam ALTO em todos os 6 alvos, sempre com a mesma mensagem, e em
nenhum deles por mérito do alvo.** Eles apontam o *caminho default* da suíte
(`tests/qa/catalog.yaml`, `tests/qa/consent-model.yaml`) em repositórios que não
declararam ser consumidores. São 12 dos 148 achados da rodada — ~8% do volume,
com informação zero sobre o código auditado.

Não proponho mudança nesta rodada (a régua está fazendo o que foi escrita para
fazer, e "ausência de catálogo" é uma verdade sobre o alvo). Registro como
PENDÊNCIA D-02, porque a decisão é de política de adoção, não de código.

---

## 6. Resumo da triagem

| Classe | Qtd. | % |
|---|---|---|
| VIOLAÇÃO-PROVÁVEL | 0 | 0% |
| FALSO-POSITIVO-PROVÁVEL | 0 | 0% |
| INCERTO | 2 | 100% |
| **Total** | **2** | |

Conferência: `python scripts/verificar_triagem.py`.

**O que este laudo autoriza dizer:** os 79 arquivos Python de GIVA passaram por
13 checks estáticos sem produzir um único achado ancorado em fato.
**O que ele não autoriza dizer:** que GIVA está conforme. Um quarto do código não
foi lido, o pack de ética não pôde ser medido, e a aplicabilidade do pack de
privacidade depende de uma resposta do dono.
