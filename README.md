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

| Pacote | Marcador pytest | Checks |
|---|---|---|
| Privacidade | `pse_privacy` | P-01 PII em logs · P-02 retenção sem purga · P-03 soft-delete · P-04 catálogo vivo · P-06 chave no código · P-08 sensível+legítimo interesse |
| Segurança | `pse_security` | S-04 terceiro sem manifesto/DPA · S-06 credencial hardcoded · S-08 transferência internacional sem base |
| Ética | `pse_ethics` | E-04 decisão crítica sem rota humana · E-05 proxy de discriminação · E-07 Model Card ausente |

Cobre o **Trabalho B** (inventário estático — sem rede, sem autorização, agente
pode disparar). O Trabalho A (auditoria runtime do alvo publicado) entra na
Fase 2, com o contrato de autorização de `docs/COMO-ADOTAR.md`.

## Uso

```bash
pip install pse-suite            # no consumidor: via requirements-qa.txt (pin)
pse --path . --config tests/qa/pse-config.yaml --output harness/reports/laudo-pse.json
pse --path . --packs privacy     # um pacote por vez
```

## Veredito — três estados, nunca binário

Um check pulado nunca é indistinguível de um check verde, e "não consegui
auditar" nunca compartilha código de saída com "conforme".

| Código | Significado | Bloqueia? |
|---|---|---|
| `0` | conforme | não |
| `10` | violação com CRÍTICO | sim |
| `11` | violação com ALTO, sem CRÍTICO | política do CI do consumidor |
| `20` | indeterminado — a suite tentou e não conseguiu decidir | **sim, igual ao 10** |
| `30` | entrada inválida — path/config/catálogo/versão irresolvíveis | sim |

Precedência quando coexistem: `30 > 10 > 20 > 11 > 0`.

**Não existe flag que rebaixe o gate.** A suite reporta a verdade em códigos
distintos; a política "ALTO bloqueia em `main`, avisa em feature branch" vive no
CI do consumidor, declarativa e protegida por CODEOWNERS — onde o dono da
decisão é visível. Uma trava que o vigiado pode desligar em silêncio não é trava.

Três destinos possíveis para um check, todos visíveis no laudo:

- `checks_executados` — rodou e decidiu;
- `checks_pulados` — **N/A declarado**: a pré-condição declarativa não existe
  (sem manifesto de terceiros não há o que conferir em S-08). Não bloqueia, mas
  o motivo é obrigatório;
- `checks_indeterminados` — **tentei e não decidi**: fato não decidível
  estaticamente, arquivo ilegível, erro inesperado. Bloqueia.

## Laudo

Schema `laudo-pse-1.0` (`schemas/`), com bloco `artifact` de procedência:

```
suite · suite_version · schema_version · catalog_hash · repo_commit
· config_fingerprint · timestamp_utc
```

O `catalog_hash` cobre `pse/data/` **e** o código dos checks: dois laudos que
declaram a mesma `suite_version` mas divergem no hash foram produzidos por
réguas diferentes, e isso fica visível sem depender da palavra de ninguém.

A evidência é sanitizada com a própria régua antes de ser serializada — o laudo
não republica o CPF, o e-mail ou a chave que acabou de denunciar. O localizador
de um achado é `arquivo:linha`, nunca o literal.

## Versão

Fonte única: `pyproject.toml`. O laudo lê dos metadados do pacote instalado. A
suite **nunca fabrica** um número: versão irresolvível é ambiente quebrado
(exit 30), não `0.2.0-dev`.

## Autoprova — a régua obedece ao que receita

```bash
pse --self-test     # a trava desta versão instalada ainda morde?
pse --manifesto     # versão, catalog_hash, checks, resultado da autoprova
```

`--self-test` audita uma fixture **embarcada no wheel** e exige vermelho, e
roda a **mutação canônica** de cada check: a violação mínima que deve reprová-lo,
declarada como dado no catálogo. Check implementado sem mutação declarada
**reprova a si mesmo** — um check que nunca foi visto reprovando nada é uma
hipótese, não uma trava.

O consumidor roda isso no próprio CI, sem clonar este repositório. Se um check
parar de morder, o pipeline diz qual.

## Desenvolvimento

```bash
pip install -e ".[dev]"
pytest                    # inclui a mordida: prova que o gate aborta
pytest -m pse_privacy     # um pacote isolado
pytest -m mordida         # só os testes negativos
```

As fixtures são três, e as três importam:

| Fixture | Prova |
|---|---|
| `consumidor_ruim` | a suite acha o que existe |
| `consumidor_silencioso` | violação real + comentário citando o controle **não** fica verde — a âncora é o fato, não a menção |
| `consumidor_bom` | o controle correto **não** vira achado — falso-positivo em CRÍTICO ensina o operador a ignorar o laudo |
