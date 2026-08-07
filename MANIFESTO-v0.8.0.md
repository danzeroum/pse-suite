# Manifesto de release — pse-suite v0.8.0

> Gerado por `pse --manifesto`. Tag anotada `v0.8.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.7.0` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a v0.8.0.**

```
pse-suite v0.8.0 — o estrato de IA ganha checks proprios

Manifesto de release
--------------------
suite_version   : 0.8.0
commit          : b0336944bc010fc9b8507875753eda54f0a4952d
catalog_hash    : 4d5b96839a38994390f6eb62488c9245e1f24430074bda32958d0dcedc7ef2a2
schema_version  : laudo-pse-1.0
checks          : 40 implementados, 0 previstos
por dominio     : {'frontend': 3, 'api': 12, 'backend': 11, 'data': 11, 'ai': 15}

Autoprova
---------
resultado       : OK
mutacoes        : 40 declaradas, 0 falhas

O QUE MUDA vs 0.7.0
-------------------
Quatro checks NOVOS, nascidos do estrato de IA — nao sao checks antigos
reetiquetados. A matriz de 0.7.0 expos duas celulas vazias, e as duas
foram fechadas:

  S-10  CRITICO  Injecao de prompt. Tres vetores num unico check porque
                 sao o mesmo ponto de entrada e a mesma consequencia:
                 instrucao concatenada, caractere invisivel (zero-width e
                 controles bidi) e token flooding.
  S-11  CRITICO  Saida do modelo em sink perigoso. Rastreio de fluxo curto
                 e honesto — aninhamento direto e uma variavel, dentro do
                 escopo. Nao promete interprocedural.
  P-15  ALTO     Dado pessoal como feature de treino sem finalidade
                 declarada. Sem chamada de treino e SkipCheck; com treino
                 e sem catalogo e INDETERMINADO, nunca verde por ausencia.
  P-16  ALTO     Dataset de treino sem governanca (finalidade e retencao).

REGUA NOVA
----------
pse/data/adversarial-patterns.yaml — fontes de entrada, 16 codepoints
invisiveis, teto de 32000 caracteres, nomes de protecao, sinks perigosos
e validacoes de saida. Nenhum dos quatro checks tem lista propria (D-13),
e ha teste que reprova se tiver.

CORRECAO DE FALSO-NEGATIVO
--------------------------
scan.nome_casa(): casamento por substring fazia `delimitar` valer como
`limitar`, e o vetor de token flooding sumia em silencio numa chamada que
so delimitava. Agora a marca casa com TOKEN do nome.

BURACO ASSUMIDO
---------------
ethics x frontend permanece vazio, com leitura assinada em pse/matriz.py
e teste que impede fechamento silencioso. AST sozinha nao decide se um
botao e coercitivo.

IMPACTO NO CONSUMIDOR
---------------------
S-11 e CRITICO: repositorio com IA que entregue saida de modelo a exec,
banco, shell ou rede sem validacao passa a sair com exit 10 onde antes
saia 0. Bump MINOR porque nao ha 1.x publicado; em 1.x isto seria major.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma.
IDs INTACTOS: nada renomeado, so acrescentado.

PENDENCIA DE RATIFICACAO
------------------------
P-15 saiu ALTO, nao CRITICO. Dado sensivel (Art. 11) como feature de
treino talvez mereca CRITICO, mas o conjunto CRITICO e fixado por
precedente — S-04 precisou de ratificacao explicita — e nao foi ampliado
por conta propria.
```
