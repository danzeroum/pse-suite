# PSE Suite

Suite de **evidências de Privacidade, Segurança e Ética por Design** — o padrão
externo e versionado consumido pela harness de `danzeroum/project`.

> **O projeto declara configuração e autorização; o padrão fornece o motor e as verificações.**
>
> **Não copie a régua.** `pse/data/` (padrões de PII, campos sensíveis, proxies de
> discriminação, hosts de terceiros) evolui por versão deste pacote. Se cada
> consumidor tivesse uma cópia editável, remover uma linha faria o laudo dizer
> "nenhum achado" — sem erro, sem aviso, indistinguível de um projeto seguro.

## Os três pacotes (testes separados entre si)

| Pacote | Marcador pytest | Checks v0.1.0 |
|---|---|---|
| Privacidade | `pse_privacy` | P-01 PII em logs · P-02 retenção sem purga · P-03 soft-delete · P-04 catálogo vivo · P-06 chave no código · P-08 sensível+legítimo interesse |
| Segurança | `pse_security` | S-04 terceiro sem manifesto/DPA · S-06 credencial hardcoded · S-08 transferência internacional sem base |
| Ética | `pse_ethics` | E-04 decisão crítica sem rota humana · E-05 proxy de discriminação · E-07 Model Card ausente |

v0.1.0 cobre o **Trabalho B** (inventário estático — sem rede, sem autorização,
agente pode disparar). O Trabalho A (auditoria runtime do alvo publicado) entra
na Fase 2, com os modos de autorização da harness.

## Uso

```bash
pip install pse-suite            # no consumidor: via requirements-qa.txt (pin)
pse --path . --config tests/qa/pse-config.yaml --output harness/reports/laudo-pse.json
pse --path . --packs privacy     # um pacote por vez
```

**Fail-closed:** qualquer finding `CRITICO` → exit 1. Não existe flag para
desligar. Um check não aplicável nunca "passa": vira `checks_pulados` com motivo
obrigatório no laudo.

## Laudo

Schema `laudo-pse-1.0` (`schemas/`), com bloco `artifact` de procedência:
versão da suite, commit auditado, fingerprint SHA-256 da config declarativa e
timestamp — pronto para arquivar em `harness/runs/`.

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest                    # inclui a mordida: prova que o gate aborta
pytest -m pse_privacy     # um pacote isolado
pytest -m mordida         # só os testes negativos
```
