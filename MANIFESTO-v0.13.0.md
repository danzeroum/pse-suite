# Manifesto de release — pse-suite v0.13.0

> Gerado por `pse --manifesto`. Tag anotada `v0.13.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.12.0` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.13.0 — o primeiro alvo real, e o que ele achou

Manifesto de release
--------------------
suite_version   : 0.13.0
commit          : 74fc1917a3a6480544ed0640e397c941ac014163
catalog_hash    : 3a67e7d737a15c0d2aec3a1e8d251533240dac7d275f614976978dc90a9a0329
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos   (NENHUM check novo)
por dominio     : {'frontend': 11, 'api': 15, 'backend': 16, 'data': 15, 'ai': 15}

Autoprova
---------
resultado       : OK
mutacoes        : 57 declaradas, 0 falhas

CONSOLIDAR ANTES DE EXPANDIR
----------------------------
Nenhum check ativo foi escrito. A Fase 3 continua fechada, e a razao dada na
recomendacao se confirmou na pratica: o aceite achou tres defeitos na regua
EXISTENTE, e adicionar a superficie mais arriscada da suite antes de
consertar isso teria sido construir sobre chao instavel.

NOTA DE PROCEDENCIA
-------------------
O bloco anterior descreveu a infraestrutura de aceite como "ja pronta". Ela
NAO estava — aquele bloco foi substituido antes de ser executado, e
`pse/aceite.py` nasce nesta versao. Fica registrado porque a honestidade que
a suite cobra do laudo vale para o estado do proprio projeto.

O QUE O PRIMEIRO ALVO REAL ACHOU
--------------------------------
Tres defeitos que ONZE VERSOES de fixture nao acharam. Nenhum deles seria
encontrado por mais fixtures: fixture e desenhada por quem escreveu o check,
e por isso nao contem a surpresa.

  1. S-04 LIA COMENTARIO
     `// https://vite.dev/config/` num vite.config.ts do btv virava "host de
     terceiro nao registrado". D-01 — ancora no fato, nunca na mencao —
     violado pelo check MAIS ANTIGO da suite, e sobrevivendo o projeto
     inteiro porque nenhuma fixture tinha URL em comentario.
     Corrigido: passa por `codigo_efetivo`, que apaga comentario e PRESERVA
     literal de string (em egresso, o literal E o fato).

  2. O LAUDO ERA SILENCIOSO SOBRE 137 ARQUIVOS RUST
     A PSE nao tem parser de Rust, leu zero deles, e o laudo saiu sem uma
     palavra sobre isso. Um leitor razoavel concluiria que o backend foi
     auditado e estava limpo.
     Nasceu `pse/alcance.py` e o bloco `alcance` do laudo. Nao e finding
     (nao ha defeito em ser escrito em Rust) e nao e indeterminacao (nao
     houve tentativa frustrada): e ESTADO, como `relatorios`.

  3. A MENSAGEM DE PARSE ACUSAVA O ALVO
     Dizia "erro de sintaxe" num `.ts` que o `tsc` compila sem reclamar —
     mandava o time procurar defeito onde nao havia. Agora `.ts` tenta as
     DUAS gramaticas (typescript e tsx sao diferentes e nenhuma e
     superconjunto da outra) e, quando as duas falham, a mensagem diz que
     pode ser o arquivo OU a gramatica, e nomeia a versao instalada.
     O veredito nao mudou: indeterminado, bloqueia, nunca verde. So o
     diagnostico ficou honesto — diagnostico errado custa mais que ausente.

MUDANCA DE CONTRATO — DEGRAU `local_target`
-------------------------------------------
Aplicacao local-first roda em 127.0.0.1, onde nao ha rede nem prova de posse
a fazer. E JUSTAMENTE por isso o degrau e explicito: sem ele, qualquer coisa
que suba numa porta local viraria alvo sondavel sem registro, e o contrato
perderia o sentido no unico lugar onde e mais facil burla-lo.

  loopback SEM `local_target`       -> indeterminado (exit 20)
  `local_target` em alvo publicado  -> exit 30 (a atestacao mentiria)
  alvo publicado                    -> target_fingerprint segue obrigatorio
  loopback COM o degrau             -> substitui a POSSE, nao a autorizacao:
                                       escopo e prazo continuam valendo

A trava mordeu na hora de nascer: os dois testes ponta-a-ponta contra o alvo
de fixture (loopback) passaram a reprovar por falta do degrau — que e
exatamente o comportamento pretendido.

O ACEITE
--------
`aceites/btv-estatico.yaml`, comparado por FAIXA e nunca por numero exato:
aceite que quebra a cada commit do alvo e desligado no primeiro mes. Fixa o
que nao pode regredir — check que parou de executar, check que parou de
morder, falso positivo novo, estrato que saiu do alcance.
Alvo ausente -> PENDENTE com motivo DATADO, nunca verde. Ha teste-mordida.

PENDENCIA_DO_DONO — OS SHAs DO COCKPIT
---------------------------------------
`d6ae70ea` e `1da4d51` NAO sao commits de `danzeroum/btv`. Verificado:
  * ausentes em todas as refs do btv (402 commits, clone completo);
  * ausentes no pse-suite;
  * sem uma unica mencao em qualquer arquivo do repositorio.
A pendencia foi carregada em conversa e nunca escrita. Perguntas abertas:
  (a) de que repositorio sao esses SHAs?
  (b) o btv E o cockpit, ainda que sob outros commits?
Enquanto nao houver resposta, o aceite do btv fica de pe por si — ele nao
depende dessa identidade para valer.

IMPACTO NO CONSUMIDOR
---------------------
  * S-04 deixa de acusar host que so aparece em COMENTARIO. Repositorio que
    tinha esse achado pode passar de 11 para 0 — e o achado era falso.
  * Laudo ganha o bloco `alcance` (campo novo; nenhum existente mudou).
  * `target_fingerprint` deixa de ser obrigatorio NO SCHEMA e passa a ser
    condicional: obrigatorio para alvo publicado, substituido por
    `local_target` em loopback. Config existente continua valida.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma. IDs INTACTOS.
Catalogo 57/57 — nenhum check novo.

VALIDACAO
---------
  * 525 passed com navegador real; 517 sem binario de navegador.
  * Aceite do btv: estado `conforme`.
  * Prova do skip honesto: com o clone do btv removido, o aceite PULA com
    motivo datado; com ele de volta, roda.

PENDENCIAS DE RATIFICACAO
-------------------------
  1. Identidade dos SHAs do cockpit (acima).
  2. `local_target` — mudanca de contrato desta versao.
  3. P-24 em `privacy`, de v0.12.0.
  4. A excecao de loopback em `validar_config`, de v0.11.0.
  5. S-14 e S-15 como candidatos a CRITICO, de v0.9.0.
```
