# Prova de NÃO-falso-positivo — o crypto-shredding correto não é punido

**Etapa 2b.** O teste mais importante da rodada.
**Alvo:** `juridico-platform/services/shared/lgpd_crypto.py` (commit `87f4934…`)
**Suíte:** pse-suite `0.3.0` · `catalog_hash 33d5be7e…20e3`

> Uma régua que dispara em quem faz certo é pior que uma que perde quem faz
> errado, porque ensina todo mundo a ignorar o laudo.
> Por isso a ausência de achado aqui é provada com o **mesmo rigor** com que se
> prova a presença de um.

---

## 0. Resultado

| | |
|---|---|
| Achados da PSE em `lgpd_crypto.py` | **0** |
| Checks que olharam o arquivo | P-01, P-03, P-06, S-04, S-06 (+ E-04, E-05, E-10 no varrer de `.py`) |
| Falso-positivo encontrado | **nenhum** |
| Refino de check necessário | **nenhum** |
| Caso adicionado ao `consumidor_bom` | **nenhum** (a condição não se realizou) |
| Bump de versão | **nenhum** |

**A ausência de achado é uma decisão da régua, não cegueira** — provado por mutação
na §3.

---

## 1. Nota de mapeamento

O enunciado da tarefa pede que a PSE não dispare **P-06/P-18/P-19/P-20** neste
arquivo. `P-18`, `P-19` e `P-20` **não existem** nesta suíte: privacidade vai de
P-01 a P-11 (ver `ONBOARDING-NOTES.md` §0). Auditei os checks que realmente
poderiam morder um módulo de criptografia:

| Check | Por que é candidato a morder este arquivo |
|---|---|
| **P-06** CRÍTICO — chave de pseudonimização em claro | é literalmente um módulo de gestão de chave |
| **P-03** ALTO — soft-delete sem eliminação física | o módulo implementa erasure; se marcasse em vez de destruir, seria o alvo exato |
| **P-01** CRÍTICO — PII em log | o módulo chama `log_pii_decrypt` / `log_pii_erase` com dado de titular |
| **S-06** CRÍTICO — credencial hardcoded | mesmo vetor de P-06, outra régua |
| **S-04** ALTO — terceiro sem manifesto | o docstring cita KMS/Vault |

P-03 é o mais relevante dos cinco: **sua própria recomendação pede
"crypto-shredding para dados criptografados"**. Um check que recomenda o controle
e depois pune quem o implementa seria o falso-positivo mais caro possível.

---

## 2. O controle sob teste

`services/shared/lgpd_crypto.py`, resumido nos fatos que importam:

| Linha | Fato |
|---|---|
| `40` | `from cryptography.hazmat.primitives.ciphers.aead import AESGCM` — AEAD real |
| `47` | `_KEY_SIZE = 32` — AES-256 |
| `64` | `_KEY_STORE[key_id] = os.urandom(_KEY_SIZE)` — **chave gerada, nunca literal** |
| `50-52` | `_key_id()` escopa por `tenant:pseudonym` — **uma chave por titular** |
| `82` | `iv = os.urandom(12)` — IV de 96 bits, novo a cada operação (NIST) |
| `84` | `aesgcm.encrypt(iv, pseudonym.encode(), None)` — cifragem autenticada |
| `109-126` | `erase_titular()` **destrói a chave** — erasure por crypto-shredding |
| `105, 125` | `log_pii_decrypt(pseudonym=…)` / `log_pii_erase(pseudonym=…)` — loga o **pseudônimo**, não o dado |

O docstring ainda explica por que AES-GCM e não HMAC ("HMAC é pseudonimização
determinística, não cifragem"). É o controle correto, e o arquivo sabe disso.

---

## 3. A prova: certo vs. mutado, mesma suíte, mesmo comando

Se um arquivo não produz achado, há duas explicações possíveis — **a régua
decidiu que está certo** ou **a régua não olhou**. Distinguir as duas é a prova.

Isolei o arquivo em dois diretórios, um com o original e outro com a **mesma
lógica e o controle quebrado**:

```bash
cp juridico-platform/services/shared/lgpd_crypto.py  prova2b/certo/
cp juridico-platform/services/shared/lgpd_crypto.py  prova2b/mutado/
# em prova2b/mutado/lgpd_crypto.py:
#   L64  os.urandom(_KEY_SIZE)          -> b"chave-mestra-fixa-de-32-bytes!!"
#                                        + secret_key = "chave-mestra-fixa-de-32-bytes!!"
#   L129 + def marcar_apagado(registro, cpf):
#            logging.getLogger(__name__).info("erase cpf=%s", cpf)
#            registro.deleted_at = "now"

pse --path prova2b/certo
pse --path prova2b/mutado
```

### Saída — arquivo CERTO

```
exit 11   findings {'total_findings': 2, 'por_severidade': {'ALTO': 2}}
   P-04 ALTO  tests/qa/catalog.yaml:1
   P-07 ALTO  tests/qa/consent-model.yaml:1
```

**Zero achados em `lgpd_crypto.py`.** Os dois ALTOs são os artefatos declarativos
ausentes do diretório de teste — presentes em todos os 6 alvos, sem relação com o
arquivo.

### Saída — arquivo MUTADO

```
exit 10   findings {'total_findings': 4, 'por_severidade': {'ALTO': 3, 'CRITICO': 1}}
   P-06 CRITICO  lgpd_crypto.py:65   | secret_key = "ch***"
   P-03 ALTO     lgpd_crypto.py:133  | registro.deleted_at = "now"
   P-04 ALTO     tests/qa/catalog.yaml:1
   P-07 ALTO     tests/qa/consent-model.yaml:1
```

### O que a comparação estabelece

| | certo | mutado |
|---|---|---|
| findings em `lgpd_crypto.py` | **0** | **2** (P-06 CRÍTICO + P-03 ALTO) |
| exit_code | 11 | **10** |

Mesma suíte, mesmo comando, mesmo arquivo em quase toda a sua extensão. **A régua
olhou, e mordeu assim que o controle quebrou.** A ausência de achado no original
é um veredito, não um silêncio.

---

## 4. Por que cada check não disparou — o fato, linha a linha

Não basta observar que não disparou; é preciso saber **por qual mecanismo**, senão
a próxima refatoração da régua quebra a propriedade sem ninguém notar.

### P-06 — não disparou porque a chave não é literal

Padrão (`pse/checks/privacy/p06_chave_segregada.py:5`):

```python
r"\b(hmac_key|secret_key|private_key|senha|password)\s*=\s*[\"'][^\"']{8,}[\"']"
```

Exige **atribuição de literal de string**. Em `lgpd_crypto.py:64` o valor vem de
`os.urandom(_KEY_SIZE)` — chamada de função, não literal. **Não há string a casar.**

Isto é D-08 no sentido mais forte: o check não "deixou passar" — não há o que
casar, porque o alvo faz a coisa certa. Chave gerada em runtime, ou vinda de
env/vault, é estruturalmente invisível a P-06. E a mutação prova que uma chave
literal na *mesma linha lógica* dispara CRÍTICO na hora.

### P-03 — não disparou porque não há soft-delete

Padrão (`p03_soft_delete.py:5`): `(deleted_at|is_deleted|status\s*==?\s*['\"]deleted['\"])`.

`erase_titular()` faz `_KEY_STORE.pop(kid, None)` — **destrói a chave**. Não há
marcação, não há flag, não há registro sobrevivente legível. O arquivo implementa
exatamente o que a recomendação de P-03 pede, e por isso não casa o padrão que
P-03 procura.

Verificado adicionalmente em toda a rodada: `deleted_at`/`is_deleted` **não
aparecem em nenhum `.py`/`.sql` dos 6 alvos**. P-03 produziu 0 achados em 6 laudos
— ausência real, não supressão.

### P-01 — não disparou por dois motivos independentes

1. **O sink não é reconhecido como log.** `RX_LOG`
   (`p01_pii_em_logs.py:29-31`) casa `^(logger|logging|log|console)$`,
   `^(logger|logging|console)\.`, `^print$` ou `\.(info|warn|…|log)$`.
   `log_pii_decrypt` não casa nenhum: `^log$` é ancorado, e não há ponto.
2. **O argumento não é PII.** Mesmo que casasse, o que é passado é
   `pseudonym=` e `tenant_id=` — e `pseudonym` **não está** em
   `pii-patterns.yaml`. Corretamente: o docstring do próprio módulo declara que o
   argumento é "identificador já pseudonimizado (ex.: HMAC do CNPJ/CPF)".

**Achado incidental sobre a suíte — um falso-NEGATIVO de P-01.** A mutação também
introduziu `logging.getLogger(__name__).info("erase cpf=%s", cpf)`, que é sink
reconhecível **e** variável da régua — e mesmo assim **P-01 não disparou**.
Investiguei em vez de deixar passar:

```python
# pse/engine/scan.py::nome_chamado não atravessa um nó Call
logging.getLogger(__name__).info("x", cpf)   ->  nome_chamado == 'info'     # RX_LOG NÃO casa
logger.info("x", cpf)                        ->  nome_chamado == 'logger.info'  # casa
```

`RX_LOG` exige `^log$` exato ou um ponto antes do nível (`\.(info|warn|…)$`).
Como `nome_chamado` para no `ast.Call` intermediário, o logger **inline** resolve
para `'info'` e escapa. Confirmado com sonda isolada: forma nomeada → `P-01
CRÍTICO`; forma inline → nenhum achado.

**Isto não é falso-positivo** (é o defeito oposto) e **não altera nada nesta
rodada**: medi o padrão `getLogger(...).<nivel>(` nos 6 alvos e ele ocorre
**0 vezes** — todos usam a forma nomeada, que P-01 detecta corretamente. Fica
registrado como candidato a refino em PENDÊNCIA S-04, não corrigido aqui (a
rodada não altera a suíte).

O ponto desta prova — a régua morde quando o controle quebra — está estabelecido
pelo **P-06 CRÍTICO** e pelo **P-03 ALTO**, que são os checks nomeados no enunciado.

### S-06 — não disparou porque não há literal de credencial

Padrão exige `api_key|apikey|access_token = "…"` (≥12) ou `Authorization: Bearer …`.
Nada disso existe no arquivo.

### S-04 — não disparou porque não há host literal

`RX_HOST` procura `https?://…`. O arquivo cita "KMS", "HashiCorp Vault", "GCP KMS"
e "External Secrets Operator" — **em docstring, e sem URL**. Duplamente correto:
`scan.grep` já apagaria o comentário, e não há host a casar de todo modo.

Este é D-01 pelo lado benigno: a **menção** a um serviço externo, sem chamada real,
não fabrica um achado de terceiro.

---

## 5. Conclusão e consequências

**A régua não pune quem faz certo.** O controle mais sofisticado encontrado nos 6
alvos — crypto-shredding AES-256-GCM por titular — atravessou a suíte inteira sem
produzir um único achado, e a mutação prova que a suíte estava olhando.

Consequências desta rodada, na ordem em que as regras da tarefa as condicionam:

1. **Nenhum check refinado.** A condição ("se disparar, corrigir o CHECK") não se
   realizou.
2. **Nenhum caso adicionado ao `consumidor_bom`.** Pelo mesmo motivo.
3. **Nenhum bump.** Reconhecimento não altera a suíte, e não houve falso-positivo
   a corrigir.
4. **`pytest` segue com 144 testes verdes** em clone limpo, e `pse --self-test`
   com as 29 mutações canônicas reprovando.

### Recomendação para uma rodada futura (não executada aqui)

O comportamento provado nesta seção **não está protegido por teste**. Se alguém
alargar o padrão de P-06 para pegar `key = <expressão>` — uma mudança plausível,
que aumentaria o recall — o crypto-shredding correto passa a disparar CRÍTICO, e
nada no CI avisaria.

Proponho, para a rodada que **puder** alterar a suíte (com bump):

- adicionar a `tests/fixtures/consumidor_bom/` um módulo de crypto-shredding
  derivado deste caso — chave via `os.urandom`, erasure por destruição de chave,
  log de pseudônimo — e o teste correspondente exigindo **zero achados**;
- registrar a proveniência ("caso real, `juridico-platform@87f4934`"), porque uma
  fixture que veio de código real vale mais que uma inventada.

Isso transformaria a prova desta rodada, que é um instantâneo, numa **trava**.

---

## 6. Reprodutibilidade

```bash
git clone --depth 1 https://github.com/danzeroum/juridico-platform.git
pip install -e ".[dev]"          # pse-suite 0.3.0
pse --path juridico-platform --output laudo.json
python -c "import json;d=json.load(open('laudo.json'));\
print([f for f in d['findings'] if 'lgpd_crypto' in (f['arquivo'] or '')])"
# -> []
```

O laudo completo do alvo está em
[`laudos/laudo-juridico-platform.json`](laudos/laudo-juridico-platform.json) —
36 achados, **nenhum** em `services/shared/lgpd_crypto.py`.
