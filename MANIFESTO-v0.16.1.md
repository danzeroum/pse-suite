# Manifesto de release — pse-suite v0.16.1

> Gerado por `pse --manifesto`. Tag anotada `v0.16.1` local.

```
pse-suite v0.16.1 — a decima ratificacao

suite_version   : 0.16.1
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos
Autoprova       : OK · 57 mutacoes declaradas, 0 falhas

NENHUMA MUDANCA DE COMPORTAMENTO
--------------------------------
Zero alteracao em `pse/checks/`, `pse/navegador/` e `pse/trabalho_a/` —
verificavel no diff. `target.artefato` nasceu na v0.16.0 com implementacao e
teste; aqui ele so e SELADO.

A DECIMA
--------
  10  target.artefato — declarado x observado          v0.16.0

  O operador declara `producao` ou `desenvolvimento`; a suite observa; o
  laudo CRUZA os dois. `producao` declarado com indicio de dev server e
  `contradicao_de_artefato`. Valor fora da lista e exit 30. Nada declarado,
  o laudo nao afirma.

POR QUE ELA E DE UMA FAMILIA PROPRIA
--------------------------------------
As nove anteriores selam o que a suite FAZ diante de um caso dificil. Esta
sela o que ela NAO FAZ: adivinhar contra o que esta medindo.

Um `vite preview` e um deploy real servem bundle igualmente minificado.
Inferir "producao" da ausencia de indicios seria inventar um fato sobre o
alvo — e o valor do bloco esta no CRUZAMENTO, nao em nenhum dos dois lados
isolado. Foi essa distincao que decidiu S-21 (andaime) e S-19 (real) em
direcoes opostas na v0.16.0.

VALIDACAO
---------
  * 4 testes novos, todos selando comportamento ja existente.
  * O ledger passou a exigir DEZ linhas numeradas; a trava que contava nove
    reprovaria se alguem acrescentasse a decima sem atualizar o teste.
```
