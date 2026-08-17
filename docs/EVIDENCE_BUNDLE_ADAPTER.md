# Evidence Bundle Adapter — PSE → evidence-bundle/v1 draft

> Sprint 6 — documentação do adapter piloto.
> Branch: `sprint-6-evidence-bundle-adapter`
> Base do laudo: `v0.3.0` (commit `6dad2fd7ce93262e7f5aa449fafbc3891dfbf038`)
> Contrato congelado de validação: `common-controls` main (commit
> `a2cd02c1fc1f06d65f6ee0a6ede75e2855c4001a`,
> `schemas/evidence-bundle-v1-draft.schema.json`)

## O que faz

O adapter converte um laudo no formato `laudo-pse-1.0` em um `evidence-bundle/v1 draft` (definido em `common-controls/schemas/evidence-bundle-v1-draft.schema.json`).

## Como usar

CLI via módulo (a integração `pse evidence-bundle` no `pse/cli.py` segue
pendente — veja Limitações):

```bash
python -m pse.adapters.evidence_bundle_v1 \
  --input-laudo laudo-pse.json \
  --context assurance-context.json \
  --output pse-evidence-bundle.json
```

Ou via Python:

```python
from pse.adapters.evidence_bundle_v1 import adapt
documento = adapt(laudo_dict, context_dict)  # {"evidence_bundle": {...}}
bundle = documento["evidence_bundle"]
```

## Shape do contrato

O documento emitido segue exatamente o schema draft:

```json
{"evidence_bundle": {"schema_version": "evidence-bundle/v1-draft",
                     "producer": {...}, "subject": {...},
                     "assertions": [...], "integrity": {...}}}
```

- `integrity.canonical_hash` cobre o bundle interno (excluindo `integrity`).
- `details.severity` usa o enum do contrato (`critical/high/medium/low`);
  `severidade: INFO` (sem equivalente no contrato) omite o campo.
- `local_execution=true` restringe todo status a
  `not_assessed`/`not_applicable` (regra `allOf` do schema): `passed`,
  `failed`, `skipped` e `errored` são rebaixados para `not_assessed` com o
  estado original preservado em `reason`.

## Mapeamento de campos

Ver `common-controls/docs/EVIDENCE_FIELD_MAPPING.md` para a tabela completa.

Resumo:
- `artifact.suite` → `producer.suite_id`
- `artifact.suite_version` → `producer.suite_version`
- `artifact.repo_commit` → `producer.suite_commit`
- `artifact.schema_version` → `producer.source_schema`
- `artifact.catalog_hash` → `producer.catalog_hash`
- `artifact.modo` → `producer.execution_mode`
- `artifact.timestamp_utc` → `producer.generated_at` (via assertions[].executed_at)
- `artifact.autorizacao` → `producer.authorization`
- `checks_executados[]` → `assertions[status=passed]`
- `findings[]` → `assertions[status=failed]` com `details`
- `checks_pulados[]` → `assertions[status=skipped]` com `reason`
- `checks_indeterminados[]` → `assertions[status=errored]` com `reason`
- `checks_nao_habilitados[]` → `assertions[status=not_assessed]` com `reason`

**Não mapeados (intencional):**
- `veredito` — computado pelo normalizador de common-controls
- `exit_code` — mecanismo de CI
- `packs[]` — agrupamento interno
- `cobertura{}` — estado do laudo
- `checks_previstos[]` — vivem no manifesto, não no bundle

## Sanitização

O adapter usa `pse.sanitize.sanitizar()` e `sanitizar_finding()` da PSE:
- Não copia literals brutos de findings (CPF, e-mail, chaves)
- Não copia tokens, headers, URLs com credencial
- `details.summary` e `details.severity` são sanitizados

## Limitações

1. **Não valida catalog_hash contra o real** — o adapter não tem acesso à PSE em runtime
2. **Não produz PSE-DEP-*** — a release v0.3.0 não emite estas assertions
3. **Capabilities hardcoded** — `CHECK_CAPABILITIES` é um dict fixo; deveria vir do catálogo
4. **Sem CLI integrada** — `pse evidence-bundle` ainda não está no `pse/cli.py` principal
5. **Não publica release v0.4.0** — Sprint 6 é piloto local

## Estados

| Situação no laudo | Estado no bundle |
|---|---|
| Check executado, sem finding | `passed` |
| Check executado, com finding | `failed` |
| Check pulado (N/A) | `skipped` |
| Check indeterminado | `errored` |
| Check não habilitado | `not_assessed` |
| `local_execution=true` | todo status → `not_assessed` (estado original em `reason`) |
| Entrada inválida | `AdapterError` (não produz bundle) |

## Validação contra o contrato

Os três bundles de fixture (`laudo-conforme` strict, `laudo-violacao` strict,
`laudo-conforme` local) validam contra o schema congelado de
`common-controls` (`jsonschema.validate` sobre
`schemas/evidence-bundle-v1-draft.schema.json`, commit `a2cd02c`).
`ci/validate_evidence_contract_draft.py` valida schema + fixtures + mapeamento
do próprio common-controls (nota: a CLI ainda não aceita caminho de bundle —
a validação do bundle gerado foi feita com o mesmo schema via `jsonschema`).

## Testes

- 12 testes em `tests/contract/test_evidence_bundle_adapter.py`
- 10 mutações M26-M35 em `tests/mutation/run_adapter_mutations.py`
