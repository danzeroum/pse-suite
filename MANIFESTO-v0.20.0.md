# Manifesto de release — pse-suite v0.20.0

> Gerado por `pse --manifesto`. Sem tag: o proxy de git deste ambiente recusa
> push de tag. O manifesto versionado no repositorio e o registro.

```
pse-suite v0.20.0 — as duas linhagens viram uma

Manifesto de release
--------------------
suite_version   : 0.20.0
schema_version  : laudo-pse-1.0
catalog_hash    : 4682a4ae1115e577...
checks          : 58 implementados, 0 previstos

Autoprova       : OK · 58 mutacoes declaradas, 0 falhas
Suite           : 798 passaram, 8 puladas

O QUE ACONTECEU
---------------
O repositorio tinha DUAS linhagens divergentes apontando para `main`, e elas
nao conviviam:

  arquitetura (v0.19.0)     58 checks, 732 testes, 217 arquivos
  reconhecimento (v0.4.1)   30 checks, 210 testes, evidencia de campo

`main` estava em v0.3.0 porque o merge da PR #1 tem como pais `1eb616b` e
`0820f92` — o conteudo da branch de arquitetura nunca entrou. Os 30 checks do
reconhecimento eram subconjunto EXATO dos 58; o que ele tinha de proprio eram
os tres refinos que consertaram a credibilidade do gate, e os laudos contra 6
repositorios reais.

Esta versao e a uniao. Dez conflitos, todos resolvidos por UNIAO e nenhum por
escolha de lado — nada das duas linhagens foi descartado.

O QUE A UNIAO PRECISOU DECIDIR
------------------------------
1. S-06 — as tres perguntas empilhadas, em ordem
   A arquitetura trouxe o alcance textual a Rust com assimetria propria
   (CRITICO so com formato conhecido, ALTO caso contrario). O reconhecimento
   trouxe a severidade por contexto (teste/valor sintetico -> MEDIO). As duas
   valem, e a ordem importa: `_credencial.rebaixar` decide POR CIMA da
   assimetria de formato, entao um `.rs` sob `tests/` nao dirige o gate nem
   quando o literal casa com AKIA. `rebaixar` so DESCE, e nunca abaixo de
   MEDIO — a garantia de que rebaixar nao vira suprimir vale igual em Rust.

2. P-06 — o risco nao tem gradacao, a severidade emitida tem
   A arquitetura afirmava "CRITICO sem gradacao"; o reconhecimento rebaixa por
   contexto. Nao e contradicao, sao duas perguntas: o RISCO de uma chave de
   pseudonimizacao exposta continua sem gradacao (e reidentificacao consumada,
   nao incidente de acesso); a pergunta do contexto e outra — aquela chave
   esta VIVA? A docstring diz as duas.

3. `example.net` — a colisao que quase apagou tres mutacoes canonicas
   O reconhecimento pos `example.net` em `ignorar` por coerencia com a RFC
   2606. A arquitetura usa `example.net` como host de terceiro "real" em 34
   fixtures. Resultado medido: E-13, S-18 e o teste de egresso real de S-04
   PARARAM de morder.

   Resolvido separando as listas, com a assimetria declarada na regua:

     num E-MAIL, dominio reservado PROVA que nao ha titular — `test@example.net`
     nao pertence a ninguem, e acusa-lo e falso-positivo em CRITICO.

     numa URL, dominio reservado NAO prova que nao ha egresso — um placeholder
     apontado para `api.x.example.net` vira endereco real no deploy seguinte,
     e S-04 emite ALTO, visivel e nao bloqueante.

   Custo assimetrico, tratamento assimetrico. `_dominio` le `ignorar` TAMBEM,
   que e o que fecha a incoerencia originalmente medida (`test@example.com`).

4. D-05 decidido por FATO, nao por presuncao
   `S-09` ja existe nesta linhagem (token no cliente). O ID esta ocupado, e o
   check de PAN — quando A-01 for respondida — so pode ser `P-12`. Isto nao
   antecipa A-01 nem implementa nada: registra que a alternativa sumiu.

O QUE A UNIAO ENCONTROU
-----------------------
A trava do refino D-01 (conjunto de extensao com `.js` e sem `.jsx`/`.tsx`)
pegou um check da arquitetura: E-13 tinha lista propria e nao veria um
componente React dentro de `node_modules`. Corrigido para `scan.ECMASCRIPT`.

E-11 chamava `_valor_pii_literal` com a assinatura antiga e virava
INDETERMINADO na fixture conforme. Corrigido — e o refino do dominio
reservado passa a valer para ele tambem: `test@example.com` num prompt de
exemplo nao e PII de titular.

O LEDGER
--------
`docs/RATIFICACOES.md` passou de 10 para 15 ratificacoes. As dez primeiras
nasceram do desenvolvimento contra o `btv`; as cinco novas nasceram da rodada
de reconhecimento contra 6 alvos reais — defeitos da PROPRIA suite que
nenhuma fixture pegaria. `tests/test_ratificacao.py` sela as 15, e reprova se
o ledger ganhar linha sem teste.

AS DUAS TRAVAS DE MERGE, AGORA JUNTAS
-------------------------------------
  doc de testes gerada    `pse/testes.py` + `tests/test_indice.py` — o CI
                          regenera e compara byte a byte
  check-orfao             `tests/test_orfao.py` (reconhecimento) convive com
                          a trava equivalente de `test_indice.py`

CAPACIDADES PRESERVADAS DAS DUAS
--------------------------------
Da arquitetura: camada dinamica por navegador (8 checks), AST de JS/TS/JSX/TSX
por tree-sitter, alcance textual a Rust, mapa de cobertura honesta, matriz
pilar x dominio, doc gerada com trava de CI, aceite contra o `btv`.

Do reconhecimento: severidade por contexto de credencial, `.tsx`/`.jsx` no
alcance textual de P-01/P-06/S-04/S-06/E-04, dominio reservado em P-01/S-03, e
`docs/reconhecimento/` — 6 laudos contra alvos reais, triagem de 148 achados,
as duas propostas de check, `PENDENCIAS-DO-DONO.md` e o delta antes/depois.

O QUE NAO ENTROU
----------------
PAN (`P-12`) e o refino de sigilo em LLM seguem NAO implementados, bloqueados
por A-01, A-02 e D-07. Ha teste que reprova se entrarem no catalogo sem que o
ledger mude no mesmo commit.
```

## Verificacao do comportamento unificado

Sonda unica, os cinco comportamentos que as duas linhagens exigem:

| Caso | Esperado | Obtido |
|---|---|---|
| `api_key` em `tests/` | MÉDIO | MÉDIO |
| `password` em `tests/` | MÉDIO | MÉDIO |
| `password` em `scripts/generate_test_password.py` | CRÍTICO | CRÍTICO |
| `console.log(user.cpf)` em `.tsx` | achado | P-01 ALTO |
| `test@example.com` em seed | sem achado | sem achado |

## Validacao

- `python -m pytest -q` → **798 passaram, 8 puladas**
- `pse --self-test` → ok, **58 mutações canônicas, 0 falhas**
- clone limpo → verde
- 10 conflitos, 0 resolvidos por descarte
