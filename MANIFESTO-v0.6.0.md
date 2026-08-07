# Manifesto de release — pse-suite v0.6.0

> Gerado por `pse --manifesto`. Tag anotada `v0.6.0` local.

> `v0.2.0` e `v0.3.0` já publicadas pelo dono; `v0.4.0` (`7ede04d`),
> `v0.5.0` (`8552073`) e `v0.6.0` seguem o mesmo caminho.

```
pse-suite v0.6.0 — matriz pilar x dominio + dominio frontend

Manifesto de release
--------------------
suite_version   : 0.6.0
commit          : f87ab09d9df16cb47d01dea2593b1152c81938f9
catalog_hash    : 136b3066ce7405ae47837f421d40349ba9cb0f90b6d6f3bc1a5f7dfbf1cc153b
schema_version  : laudo-pse-1.0
checks          : 36 implementados, 0 previstos
por dominio     : {'frontend': 3, 'api': 12, 'backend': 11, 'data': 11, 'ai': 11}

Autoprova
---------
resultado       : OK
mutacoes        : 36 declaradas, 0 falhas

Compatibilidade vs 0.5.0
------------------------
Exit codes INTACTOS. Schema laudo-pse-1.0 aditivo (dominios,
cobertura.por_dominio, finding.domain); padrao de ID relaxado para
^[A-Z]{1,3}-[0-9]{2}$ por causa de FE-*.
NOVA DEPENDENCIA: tree-sitter + gramaticas javascript/typescript.
ATENCAO: FE-01 e FE-02 sao CRITICOS — repositorio com frontend passa a
poder bloquear onde antes nem era olhado.
```
