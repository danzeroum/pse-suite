# Manifesto de release — pse-suite v0.2.0

> Gerado por `pse --manifesto`. A tag anotada `v0.2.0` carrega o mesmo texto.
> Reproduzível: `git checkout v0.2.0 && pse --manifesto`.

```
pse-suite v0.2.0 — Trabalho B completo, fail-closed provado

Manifesto de release
--------------------
suite_version   : 0.2.0
commit          : b98916f783148b130564e6a24e03d99c712ba01c
catalog_hash    : 5830a4ae43a9ac09f071d2b68711d556cd106eb6c55c7ad60a8259644386341e
schema_version  : laudo-pse-1.0
checks          : 13 implementados, 17 previstos (30 no catalogo)

Autoprova
---------
resultado       : OK
motivo          : trava integra: a fixture embarcada produz os CRITICOs esperados e as 13 mutacoes canonicas reprovam
criticos na fixture embarcada: E-04, P-01, P-06, P-08
mutacoes canonicas: 13 declaradas, 0 falhas (executor interino)

Contrato do CLI (QUEBRA vs 0.1.0)
---------------------------------
Exit codes 0/1/2 -> 0/10/11/20/30, precedencia 30>10>20>11>0.
Consumidor pinado em 0.1.0 nao deve subir sem ajustar o gate do CI.

Implementados: E-00, E-04, E-05, E-07, P-01, P-02, P-03, P-04, P-06, P-08, S-04, S-06, S-08
```
