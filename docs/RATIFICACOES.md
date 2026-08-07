# Ratificações

> **O que este documento é.** O registro das decisões de contrato que o dono
> aprovou. Cada uma nasceu de um caso real, ficou pendente, e foi selada aqui.
>
> **O que ele não é.** Não é changelog nem justificativa retroativa. Uma
> ratificação não muda comportamento: ela sela o comportamento que já existia,
> e que já tinha teste. Se selar exigisse mexer em código, a decisão não estava
> madura para ser selada.
>
> **Quem sela de verdade é `tests/test_ratificacao.py`.** Este documento torna
> a decisão localizável; o teste a torna verdadeira. Uma linha desta tabela que
> deixe de valer vira uma tabela falsa, e tabela falsa é pior que ausente.

---

## Seladas em 2026-08-07 — a rodada de conserto

| # | Decisão | Nasceu de | Comportamento selado |
|---|---|---|---|
| 1 | Credencial em caminho de teste é **MÉDIO** | 18 dos 19 CRÍTICOs de credencial eram fixtures | P-06/S-06 rebaixam para MÉDIO quando o caminho é de teste **ou** o literal é sintético. **Nunca suprimem** — o achado continua no laudo, com o motivo do rebaixamento escrito na descrição |
| 2 | Valor **que existe para ser rejeitado** num teste é **MÉDIO** | `Central/tests/unit/test_api_security.py:47` | Token propositalmente inválido recebe o mesmo tratamento de qualquer credencial em teste. A PSE **mostra a dúvida**, não a resolve por intenção declarada |
| 3 | A marca casa **delimitada**, e a posição é declarada | `reconcilia/scripts/generate_test_password.py:9` | `^x` prefixo, `x$` sufixo do radical, `/x/` diretório; no valor, `_` e `-` são fronteira e letra/dígito não. Sem isso o único CRÍTICO **real** dos 19 caía junto com os falsos |
| 4 | `.tsx` e `.jsx` no alcance, mesma heurística de `.ts` | 281 arquivos React invisíveis nos 6 alvos | Entram em `scan.ECMASCRIPT`, um lugar só, com a severidade rebaixada que `.ts` já tinha fora do Python. Não há parser de JSX |
| 5 | Domínio reservado (RFC 2606/6761) não é PII | `test@example.com` em script de seed produzia 3 CRÍTICOs | P-01 e S-03 leem a mesma lista `ignorar` que S-04 sempre leu, **só para valor literal de e-mail**. Variável de usuário, CPF e telefone seguem valendo |

---

## A segunda, em detalhe — porque é a que parece uma exceção e não é

Um teste que prova que a API recusa token inválido **precisa** de um token
inválido escrito ali. É o caso mais simpático que existe: quem o escreveu
estava fazendo teste de segurança, e a suíte o reprovava por isso.

A tentação é criar uma terceira categoria — *não-credencial* — e tirar o
achado do laudo. **Isso seria o D-01 ao contrário.**

A PSE não distingue estaticamente `token = "abc123"` que existe para ser
rejeitado de `token = "abc123"` que é real e foi comentado como teste. As duas
formas são idênticas na árvore sintática. Reconhecer a primeira exigiria crer
na **intenção declarada** — no nome do teste, no comentário ao lado, na pasta
onde está. E crer na menção é exatamente o que a suíte cobra dos outros que
não se faça.

**MÉDIO é o veredito honesto para a ambiguidade.** Ele diz: *isto é uma
credencial em texto claro, e o contexto sugere que não é viva — confira*. Não
diz "está tudo bem", e não para o CI. A dúvida fica visível para quem pode
resolvê-la, que é o dono do código, não a suíte.

O que **não** rebaixa nada, e tem teste: comentário. `# intentionally invalid`
ao lado de uma chave da AWS num arquivo de produção continua em CRÍTICO.

---

## O que segue pendente — nada foi implementado no escuro

Dois checks estão especificados e **não implementados**, cada um esperando uma
resposta que só o dono tem. Implementá-los agora seria presumir o alvo.

| Check | Bloqueado por | O que exatamente falta |
|---|---|---|
| **PAN / PCI** (`P-12` ou `S-09`) | **A-01** | Os arquivos EDI de Cielo/Rede/Stone em produção trazem PAN completo ou já vêm truncados pela adquirente? Há retenção do arquivo bruto? Sem isso o check nasce sem alvo real provando que dispara, e a severidade é chute |
| **Sigilo em LLM** (refino de `E-11`) | **A-02** + **D-07** | A-02: `LLM_PROVIDER` em produção é `openai` ou `ollama`? Decide entre ALTO (egresso externo sem redação) e MÉDIO (local). D-07: introduzir `llm_egress: external\|local` no `pse-config.yaml`, com omissão → INDETERMINADO? Exige entrada no schema e em `COMO-ADOTAR.md` |

`D-05` (PAN é `P-12` ou `S-09`) e `D-06` (sigilo é `E-11`, `S-09` ou `P-12`)
têm recomendação registrada do arquiteto — `P-12`/`privacy` e refino de `E-11`
— e ficam prontas para selar **no mesmo commit em que A-01/A-02/D-07 forem
respondidas**. Sozinhas elas não destravam nada: saber o ID de um check que
não se sabe se dispara não é progresso.

`tests/test_ratificacao.py` reprova se algum dos dois for implementado sem que
esta tabela mude — a garantia de que "não implementado no escuro" é fato
verificável, e não promessa.

---

## Como uma pendência vira ratificação

1. Nasce de um caso real, medido, e entra em
   [`reconhecimento/PENDENCIAS-DO-DONO.md`](reconhecimento/PENDENCIAS-DO-DONO.md).
2. Fica lá enquanto o dono não decide. Pendência sem data não vence sozinha.
3. Ratificada, entra na tabela acima com a origem preservada.
4. `tests/test_ratificacao.py` reprova se o comportamento selado deixar de
   valer.
