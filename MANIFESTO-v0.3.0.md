# Manifesto de release — pse-suite v0.3.0

> Gerado por `pse --manifesto`. A tag anotada `v0.3.0` carrega o mesmo texto.
> Reproduzível: `git checkout v0.3.0 && pse --manifesto`.

> **v0.2.0 nunca foi publicada** — o proxy git deste ambiente recusa push de
> `refs/tags`. `MANIFESTO-v0.2.0.md` fica como registro daquele commit
> (`b98916f`, Trabalho B completo); esta é a release corrente.

```
pse-suite v0.3.0 — Fase 3: catalogo completo menos E-08

Manifesto de release
--------------------
suite_version   : 0.3.0
commit          : 6dad2fd7ce93262e7f5aa449fafbc3891dfbf038
catalog_hash    : 33d5be7e85777045d0088c3f5f7a91e394c83c4be33cfeda519b6073be0420e3
schema_version  : laudo-pse-1.0
checks          : 29 implementados, 1 previstos

Autoprova
---------
resultado       : OK
motivo          : trava integra: a fixture embarcada produz os CRITICOs esperados e as 29 mutacoes canonicas reprovam
mutacoes        : 29 declaradas, 0 falhas

Compatibilidade vs 0.2.0
------------------------
Exit codes INTACTOS (0/10/11/20/30). Schema laudo-pse-1.0 so aditivo.
Novidades: --modo (pse_passive/pse_active), 16 checks runtime,
thresholds com faixa validada, contrato trabalho-a-config-1.0.

Previstos: E-08
```
