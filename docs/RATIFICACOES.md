# Ratificações

> **O que este documento é.** O registro das decisões de contrato que o dono
> aprovou. Cada uma nasceu numa versão, ficou listada como *pendente de
> ratificação* no manifesto daquela versão, e foi selada aqui.
>
> **O que ele não é.** Não é changelog nem justificativa retroativa. Uma
> ratificação não muda comportamento: ela sela o comportamento que já
> existia, e que já tinha teste. Se selar exigisse mexer em código, a
> decisão não estava madura para ser selada.
>
> **Por que existe.** As pendências viviam espalhadas por nove manifestos.
> Quem chegasse na v0.15 teria de ler nove documentos para saber o que já
> tinha sido decidido e o que ainda estava em aberto — e, na prática,
> ninguém leria. Uma decisão que ninguém encontra não foi tomada.
>
> Os manifestos **não** são reescritos. Eles são o registro do que se sabia
> naquele momento, e alterá-los para dizer *ratificado* falsificaria a
> história que eles existem para guardar.

---

## Seladas em 2026-08-07 — as dez primeiras

| # | Decisão | Nasceu em | Comportamento selado |
|---|---|---|---|
| 1 | `local_target` | v0.13.0 | Alvo em loopback dispensa `target_fingerprint` e **exige** o degrau explícito; declará-lo em alvo publicado é exit 30 |
| 2 | Exceção de loopback | v0.11.0 | `http://` é aceito **apenas** com host de loopback exato, parseado — `127.0.0.1.atacante.com` não passa |
| 3 | P-24 em `privacy` | v0.12.0 | EXIF/GPS em arquivo publicado é pilar `privacy`, não `security` |
| 4 | S-14 e S-15 permanecem `ALTO` | v0.9.0 | Não sobem para `CRÍTICO`: dump entre ambientes e GRANT amplo são graves, e `CRÍTICO` fica reservado ao que já é exposição consumada |
| 5 | `env!` → `CheckIndeterminado` | v0.14.0 | Macro de tempo de compilação numa ligação de credencial bloqueia (exit 20); `std::env::var` decide normalmente |
| 6 | Severidade textual em Rust é assimétrica | v0.14.0 | `CRÍTICO` só com formato conhecido (AKIA, `sk-`, `ghp_`, PEM, JWT); literal longo de formato desconhecido é `ALTO` |
| 7 | Embrulho de cifra opaco → `CheckIndeterminado` | v0.14.2 | Coluna sensível no SQL com valor ligado a identificador que a régua não reconhece como cifra bloqueia, em vez de virar achado ou verde |
| 8 | Emitir achado **e** indeterminar coexistem | v0.15.0 | Arquivo ilegível não apaga o veredito dos demais: o check emite o que leu e segue indeterminado |
| 9 | Qualificação do que foi observado | v0.15.1 | `observacao_de_rede` declara a superfície observada e se quem serviu era servidor de desenvolvimento |
| 10 | `target.artefato` — declarado × observado | v0.16.0 | O operador declara `producao`/`desenvolvimento`, a suíte observa, e o laudo cruza: `producao` declarado com indício de dev server é `contradicao_de_artefato`; valor fora da lista é exit 30; nada declarado, o laudo não afirma |

### O que as dez têm em comum

Todas foram decididas **para o lado seguro** — bloquear em vez de adivinhar,
`ALTO` em vez de `CRÍTICO` sem certeza, nomear a lacuna em vez de calar. Três
delas (5, 7, 8) existem porque o alvo real mostrou um caso em que qualquer um
dos dois lados óbvios estaria errado, e a resposta certa era a terceira: não
decidir, e dizer que não decidiu.

A décima é de uma família própria e vale destacar: ela sela que a suíte **não
adivinha** contra o que está medindo. Um `vite preview` e um deploy real
servem bundle igualmente minificado — inferir *produção* da ausência de
indícios seria inventar um fato sobre o alvo. Então o operador declara, a
suíte observa, e o valor do laudo está no **cruzamento**, não em nenhum dos
dois isolados.

Nenhuma foi selada por conveniência. As dez já tinham teste-mordida antes de
chegar aqui, e o teste é o que sela de verdade — este documento apenas torna a
decisão localizável.

---

## Como uma pendência vira ratificação

1. Nasce numa versão, implementada e com teste, e entra em
   **PENDÊNCIAS DE RATIFICAÇÃO** no manifesto daquela versão.
2. Fica lá enquanto o dono não decide. Pendência sem data não vence sozinha.
3. Ratificada, entra na tabela acima com a versão de origem preservada.
4. `tests/test_ratificacao.py` reprova se o comportamento selado deixar de
   valer — a linha da tabela vira falsa, e uma tabela falsa é pior que
   ausente.

## O que segue pendente

| Pendência | Nasceu em |
|---|---|
| Apontar o repositório do `global-ingress` — confirmado versionado e compartilhado por vários projetos; falta o nome | v0.17.0 |
| Medir `/dev` no arranjo real (imagem Docker, origem compartilhada) | v0.15.1 |
| A gramática dos 3 arquivos `.ts`/`.tsx` servidos | v0.15.0 |
| Identidade dos SHAs do cockpit (`d6ae70ea` / `1da4d51`) | v0.13.0 |
| O btv declarar `tests/qa/catalog.yaml` (habilita P-18) | v0.14.1 |
| O btv declarar `data_residency` (habilita S-16) | v0.14.1 |
