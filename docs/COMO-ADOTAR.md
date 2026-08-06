# Como adotar a PSE Suite no consumidor (`danzeroum/project`)

Tudo que entra no consumidor é **declarativo ou de orquestração**. Nenhum check,
nenhuma régua, nenhum threshold fora das faixas que a suite valida.

## 1. Pin da versão (fonte única)

```
# requirements-qa.txt  — único lugar com o número; todo o resto referencia
pse-suite==0.1.0
```

## 2. Config declarativa

```yaml
# tests/qa/pse-config.yaml
pse_suite:
  version_source: requirements-qa.txt      # nunca restate a versão
  catalog_path: tests/qa/catalog.yaml
  third_party_manifest: .privacy/third-party-manifest.yml
  packs:
    privacy:  {enabled: true}
    security: {enabled: true}
    ethics:   {enabled: true}
```

## 3. Catálogo vivo (P-04 cobra a existência e a coerência)

```yaml
# tests/qa/catalog.yaml
tables:
  users:
    fields:
      cpf:
        class: personal          # personal | sensitive | anonymized
        owner: financeiro
        purpose: faturamento
        legal_basis: contrato    # sensitive NUNCA aceita legitimo_interesse (P-08)
        retention_years: 5       # declarar retenção exige job de purga (P-02)
```

## 4. Manifesto de terceiros (S-04 / S-08)

```yaml
# .privacy/third-party-manifest.yml
integrations:
  - name: google-analytics
    hosts: [analytics.google.com]
    dpa_signed: true             # false + required -> CRITICO, deploy bloqueado
    dpa_path: contracts/ga-dpa.pdf
    data_residency: US
    transfer_basis: SCC_ANPD     # fora do BR sem base -> S-08
```

## 5. Modos na harness

```yaml
# harness/harness.yaml (acréscimo)
modes:
  pse_inventory:                 # Trabalho B — agente pode disparar
    network: false
    authorization: none
  # Fase 2: pse_passive / pse_active (Trabalho A), com aval conforme o modo
```

## 6. CI — laudo em toda PR + passo negativo (a mordida)

```yaml
# .github/workflows/qa.yml (acréscimo)
pse-inventory:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: pip install -r requirements-qa.txt
    - name: laudo PSE (fail-closed)
      run: pse --path . --config tests/qa/pse-config.yaml
                --output harness/reports/laudo-pse.json
    - name: mordida — prova que a trava aborta
      run: |
        # fixture publicada com o pacote: se o gate NAO abortar aqui, a trava quebrou
        FIX=$(python -c "import pse, pathlib; print(pathlib.Path(pse.__file__).parent.parent)")
        if pse --path "$FIX/tests/fixtures/consumidor_ruim" \
               --config "$FIX/tests/fixtures/consumidor_ruim/pse-config.yaml" \
               --output /tmp/mordida.json; then
          echo "TRAVA QUEBRADA: fixture com CRITICOS passou"; exit 1
        fi
```

## 7. Rastreabilidade no grafo do projeto

Cada controle de **produto** (consent engine, decision logger, contestação,
kill switch...) é um `REQ-*` no `business/requirements/backlog.yaml`, com
`validated_by` apontando para o teste que consome o check PSE correspondente —
fechando o elo bidirecional que `ci/validate_metadata.py` já cobra.

Alterar `tests/qa/pse-config.yaml` deve ser **caminho protegido** (CODEOWNERS):
afrouxar a régua exige aval humano visível.
