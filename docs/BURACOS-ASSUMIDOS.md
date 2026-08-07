# Buracos assumidos

> **O que este documento é.** O registro dos vetores que foram investigados,
> considerados reais, e **deliberadamente não implementados** como check —
> porque o check possível verificaria a fachada, não o direito.
>
> **O que ele não é.** Não é backlog. Um item aqui não está esperando alguém
> ter tempo: está esperando um artefato verificável aparecer. Enquanto não
> aparecer, a decisão certa é esta — nomear o buraco.
>
> **Por que existe.** `P-21` já tinha esta forma, e a decisão vivia dentro de
> um teste que só quem procurasse encontraria. Uma decisão que ninguém acha
> não foi tomada. Aqui ela fica localizável, e o gerador de `docs/TESTES.md`
> lê esta tabela para a seção de lacunas — fechado um buraco, ele some dos
> dois documentos no mesmo commit.

---

## A regra que produz esta lista

Um vetor vira check quando existe um **artefato verificável** que separa o
sistema que cumpre do que finge cumprir. Quando o único teste possível é
*"existe?"*, o check nasce fraco: ele dá a impressão de cobrir um direito sem
provar que o direito funciona, e essa impressão é pior que o silêncio —
porque o laudo passa a afirmar cobertura onde não há.

Buraco honesto é melhor que check de fachada. É a mesma regra que matou P-21.

---

## Os buracos

| # | Vetor | Por que não virou check | Nasceu em |
|---|---|---|---|
| 1 | Zona bruta de data lake sem restrição (`P-21`) | Não há artefato versionado que distinga a zona bruta restrita da irrestrita: a decisão vive em IAM e em política de bucket, fora do repositório | v0.9.0 |
| 2 | Endpoint de acesso do titular (Art. 18 II) | *"O endpoint existe"* é fraco e *"responde em tempo hábil, com o dado certo, para o titular certo"* é o que a lei pede — e isso não é verificável estaticamente nem por sonda sem impersonar um titular real | v0.19.0 |
| 3 | Efeito downstream de revogação (Art. 18 IX) | Revogar consentimento tem de parar o processamento **em todos os sistemas a jusante** — filas, réplicas, data lake, parceiros. É comportamento distribuído: nenhum repositório contém a prova, e observar o efeito exigiria acesso a sistemas que não são o alvo | v0.19.0 |

---

## A leitura assinada de cada um

### 1. Zona bruta de data lake (`P-21`)

Investigado na fase 9, quando `data` ganhou o seu fundador (P-20). Três
razões, e a terceira é a que decide: a restrição da zona bruta é configuração
de nuvem, não código; o repositório contém no máximo um Terraform que pode
não ser o que está aplicado; e um check que lesse o Terraform afirmaria sobre
o estado desejado enquanto o laudo seria lido como afirmação sobre o estado
real.

A decisão está assinada em `tests/test_data_estrato.py`, que **reprova se
`P-21` entrar no catálogo** sem que ela seja revista.

### 2. Endpoint de acesso do titular

O material de security pedia um check para o Art. 18 II — o titular pede os
seus dados e o controlador entrega. O check possível seria: existe rota de
exportação declarada? Mas isso **já é P-10**, que roda no ar e confirma que a
rota responde e devolve conteúdo íntegro.

O que P-10 não faz — e o que faria deste um check novo — é verificar que a
resposta contém *os dados daquele titular*, *todos eles*, *dentro do prazo
legal*. Nenhuma das três é verificável sem: (a) conhecer o conjunto correto de
dados do titular, que só o alvo sabe; (b) impersonar um titular real, o que a
suíte proíbe (identidades sintéticas são obrigatórias no Trabalho A); (c)
medir prazo, que é propriedade do processo e não do sistema.

Um check que checasse só *"existe rota"* duplicaria P-10 com nome novo, e o
laudo passaria a exibir dois verdes onde há uma única verificação. Dois verdes
pela mesma evidência é inflação de cobertura.

### 3. Efeito downstream de revogação

O material descrevia o caso corretamente: o titular revoga, o sistema
principal para, e o dado continua sendo processado no data lake, na fila de
eventos e no parceiro que recebeu uma cópia na semana passada.

O vetor é real e grave. Ele também é, por construção, **não observável a
partir do alvo**. A prova exigiria: enumerar os sistemas a jusante (não estão
no repositório), acessá-los (não são o alvo declarado, e sondar terceiro sem
autorização é exatamente o que o contrato do Trabalho A proíbe) e correlacionar
um evento de revogação com a ausência de processamento posterior (janela de
tempo indeterminada).

Existe uma metade verificável, e ela **já tem dono**: P-19 exige
crypto-shredding no log de eventos — o mecanismo que torna a revogação
*efetiva* num registro append-only. P-07 exige que a revogação exista e que a
retenção pós-revogação esteja declarada. O que sobra é o efeito distribuído, e
sobre esse a suíte não afirma nada.

---

## O que faria cada um nascer

| # | O artefato que falta |
|---|---|
| 1 | Policy-as-code da zona bruta versionado no repositório, com a prova de que é o que está aplicado |
| 2 | Contrato declarado do conjunto de dados do titular (o catálogo já declara campos — falta a ligação campo → resposta de exportação), que tornaria verificável *"todos eles"* |
| 3 | Manifesto de sistemas a jusante por finalidade, declarado pelo alvo, que tornaria a enumeração um fato e não uma descoberta |

Enquanto o artefato não existe, o item fica aqui. Um buraco que sabe o que
precisa para fechar não é o mesmo que um buraco.
