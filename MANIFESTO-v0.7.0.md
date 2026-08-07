# Manifesto de release — pse-suite v0.7.0

> Gerado por `pse --manifesto`. Tag anotada `v0.7.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.6.0` são tags de obra:
> nenhuma chegou a consumidor, e a série pode ser deixada para trás —
> **quando o consumo real começar, publicar só a v0.7.0.**

```
pse-suite v0.7.0 — prefixo do ID volta a codificar o pilar

Manifesto de release
--------------------
suite_version   : 0.7.0
commit          : 79f98836328d2be5fa7f29664594409bd1b89da0
catalog_hash    : e950d510614a34f1148fc81c6454b4c81e3f17d20fc547d79e2851c0d1212db2
schema_version  : laudo-pse-1.0
checks          : 36 implementados, 0 previstos
por dominio     : {'frontend': 3, 'api': 12, 'backend': 11, 'data': 11, 'ai': 11}

Autoprova
---------
resultado       : OK
mutacoes        : 36 declaradas, 0 falhas

QUEBRA DE CONTRATO DE REFERENCIA vs 0.6.0
-----------------------------------------
IDs renomeados: FE-01 -> P-13, FE-02 -> P-14, FE-03 -> S-09.
O prefixo do ID codifica o PILAR, sempre e apenas. Dominio vive no
metadado `domain`, que e lista — e a unica das duas dimensoes que e
multivalorada, entao nao cabe num lugar rigido e unico como o prefixo.
Padrao de ID de volta a ^[PSE]-[0-9]{2}$, com trava que barra prefixo de
dominio (FE-*, AP-*, MB-*) reaparecer.

Nenhuma tag alem de v0.2.0/v0.3.0 foi publicada, entao FE-* nunca chegou
a consumidor: relatorio que cite FE-01 so pode ser interno.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma.
```
