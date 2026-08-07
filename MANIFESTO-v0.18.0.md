# Manifesto de release — pse-suite v0.18.0

> Gerado por `pse --manifesto`. Sem tag: o proxy de git deste ambiente recusa
> push de tag. O manifesto versionado no repositorio e o registro.

```
pse-suite v0.18.0 — a documentacao de testes virou trava

Manifesto de release
--------------------
suite_version   : 0.18.0
schema_version  : laudo-pse-1.0
catalog_hash    : a35bf065ab601e29bf1d6252ced3d2f538dd554e6a7ee0297861fce3ce2d039f
checks          : 57 implementados, 0 previstos   (NENHUM check novo)

Autoprova       : OK · 57 mutacoes declaradas, 0 falhas
Suite           : 713 passaram, 8 puladas   (era 684 + 8)

O QUE MUDOU, EM UMA FRASE
-------------------------
A doc de testes deixou de ser um documento e virou um artefato GERADO do
codigo, com uma trava de CI que reprova o merge quando o commitado diverge
do que o codigo produz — ou quando um check existe sem teste que o cubra.

POR QUE "GERADO" NAO BASTAVA
----------------------------
O relatorio de testes foi aprovado com a proposta "gerado, nao redigido". A
proposta estava certa e era insuficiente: um gerador que ninguem e obrigado
a rodar produz doc velha do mesmo jeito — a unica diferenca e de quem e a
culpa. Alguem acrescenta P-25, esquece de rodar o gerador, e o merge entra
com o documento afirmando 57 checks quando ha 58.

A peca que faltava e a conferencia NO MERGE. O CI regenera os dois
documentos em memoria e compara com o commitado; divergiu, o portao nao
abre. E a doutrina da suite aplicada a ela mesma: uma trava que o vigiado
pode desligar nao e trava.

O QUE ENTROU
------------
`pse/testes.py`         gerador. Le o catalogo, o registro e a arvore
                        sintatica de `pse/checks/**` e de `tests/**`.
                        Nenhum numero do documento e digitado.
`docs/TESTES.md`        as duas camadas: os 57 checks (o que a suite audita
                        num alvo) e as 596 funcoes de teste (o que prova que
                        os checks funcionam), com a secao de lacunas.
`docs/INDICE-DE-TESTES.md`
                        check a check: modulo, testes que o cobrem, COMO
                        cobrem, mutacao canonica, reguas, substrato.
`tests/test_indice.py`  a trava — 32 testes.
`.github/workflows/ci.yml`
                        primeiro workflow do repositorio. A trava roda no
                        MESMO job que a suite.

AS DUAS TRAVAS
--------------
1. DOC DESATUALIZADA REPROVA. `corpo_comparado()` compara byte a byte tudo
   que vem antes de `<!-- fim-do-corpo-comparado -->`. A mensagem de falha
   traz o comando de regenerar — trava que reprova sem dizer o que fazer
   vira ticket, nao conserto.

2. CHECK ORFAO REPROVA. Um documento que lista 57 checks e 596 funcoes sem
   verificar que as segundas cobrem os primeiros e meia-garantia. E o
   simetrico tambem reprova: teste citando ID que nao existe no catalogo.

DETERMINISMO E PRE-REQUISITO, NAO DETALHE
-----------------------------------------
Gerador que produz bytes diferentes a cada execucao faz a comparacao falhar
por ruido; o time aprende a ignorar o vermelho e a trava morre de fadiga —
o mesmo mecanismo pelo qual falso-positivo em CRITICO ensina a ignorar o
laudo. Entao: toda iteracao ordenada, e um teste que roda o gerador em
PROCESSO NOVO (hash seed diferente) para pegar o `set` que escapou do
`sorted`. O volatil — versao do pacote, data — vive DEPOIS da marca, fora
da comparacao: um bump de versao nao reprova merge.

O QUE A TRAVA ACHOU NO PRIMEIRO USO
-----------------------------------
S-08 ESTAVA ORFAO. `Transferencia internacional sem base declarada`, fase 1,
existia desde o comeco sem um unico teste proprio. Ele aparecia em docstring
— inclusive na de `test_backend_estrato.py` — e docstring nao e teste. E o
D-01 aplicado a propria suite: a MENCAO do check nao prova que alguem o
exercitou.

A prova de mutacao passava por ele, porque parametriza sobre
`catalogo.implementados()` e alcanca os 57 por construcao. Por isso ela NAO
conta como cobertura no indice: se contasse, nenhum check jamais seria
orfao e a trava nao provaria nada. Ela prova que o inverso canonico fica
vermelho; nao prova que o caso conforme fica quieto, que o skip nomeia o
motivo, nem que S-08 e S-16 nao sao o mesmo check com dois IDs.

Entraram 5 testes de S-08, incluindo o par com S-16: manifesto promete BR,
codigo escreve em `us-east-1` — S-16 acha, S-08 fica quieto. E essa
assimetria que justifica os dois IDs.

SEIS CHECKS SEM DOCSTRING. P-03, P-06, P-08, S-04, S-08 e E-07 nao tinham
descricao propria, e a doc gerada caia para o titulo do catalogo. Escritas.

A SECAO DE LACUNAS E GERADA, E ISSO E O PONTO
---------------------------------------------
Uma doc obrigatoria que so listasse o que tem cobertura seria propaganda.
Cada lacuna sai de uma sonda sobre o estado real:

  linguagens sem parser        de `alcance.SEM_PARSER` e `ALCANCE_PARCIAL`
  exclusao de caminho          sonda a arvore de `pse/` por chave de config
                               que fale de excluir/ignorar; nao achando,
                               declara que so ha `scan.IGNORAR_DIRS` fixo
  IDs ausentes (P-12, P-21)    buraco na numeracao do catalogo
  pendencias abertas           LIDAS de `docs/RATIFICACOES.md`, nao copiadas
  parametrizacoes opacas       4 funcoes cujos argvalues sao computados; o
                               total de casos e declarado como PISO
  orfaos / sem mutacao /       zerados hoje, e a trava reprova quem abrir
  sem docstring / previstos    o primeiro

Ratificada uma pendencia, ela sai da tabela de RATIFICACOES.md e sai deste
documento no mesmo commit, sem ninguem lembrar.

A DIVISAO NAO TEM BALDE
-----------------------
As sete familias de teste sao JULGAMENTO e ficam declaradas em
`pse.testes.FAMILIAS`, como o substrato em `pse/cobertura.py`. Nao ha balde
`outros`: arquivo de teste novo sem familia declarada levanta
`FamiliaAusente` e reprova. Um documento cuja divisao aceita qualquer coisa
deixa de dividir.

O QUE NAO MUDOU
---------------
Nenhum check novo. Nenhum comportamento de check alterado. Os exit codes,
o contrato do laudo e a regua estao intactos: nenhum arquivo de `pse/data/`
foi tocado, e portanto o `catalog_hash` e o mesmo da v0.17.1. As unicas
edicoes em `pse/checks/**` foram as seis docstrings — texto, nao logica.
```

## Pendencias de ratificacao

Nenhuma nova. As seis abertas seguem em `docs/RATIFICACOES.md` — e agora
aparecem tambem em `docs/TESTES.md`, lidas de la, nao recopiadas.

## Validacao

- `python -m pytest -q` → **713 passaram, 8 puladas**
- `python -m pytest tests/test_indice.py -q` → **32 passaram**
- clone limpo → verde
- `pse --manifesto` → autoprova OK, 57 mutacoes, 0 falhas
