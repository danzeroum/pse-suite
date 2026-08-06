# Manifesto de release — pse-suite v0.4.0

> Gerado por `pse --manifesto`. A tag anotada `v0.4.0` existe localmente.
> Reproduzível: `git checkout v0.4.0 && pse --manifesto`.

> **Nenhuma tag foi publicada ainda** — o proxy git deste ambiente recusa
> push de `refs/tags`. Pendentes: v0.2.0 (`b98916f`), v0.3.0 (`6dad2fd`)
> e v0.4.0.

```
pse-suite v0.4.0 — IA e cadeia de terceiros (E-11, E-12, E-13)

Manifesto de release
--------------------
suite_version   : 0.4.0
commit          : 7ede04d5acf1f031ae34739e525d4696bbb855fe
catalog_hash    : e0bd5173b0f5be509fe0541dbf642c08dccf77cb430cab3b2be713dca1d622c6
schema_version  : laudo-pse-1.0
checks          : 32 implementados, 1 previsto(s)

Autoprova
---------
resultado       : OK
mutacoes        : 32 declaradas, 0 falhas

Compatibilidade vs 0.3.0
------------------------
Exit codes INTACTOS. Schema laudo-pse-1.0 inalterado.
ATENCAO: E-11 e CRITICO — atualizar de 0.3.0 pode passar a bloquear CI
que antes passava, se houver PII crua indo para prompt de LLM.

Previsto: E-08
```
