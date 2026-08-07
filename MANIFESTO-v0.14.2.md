# Manifesto de release — pse-suite v0.14.2

> Gerado por `pse --manifesto`. Tag anotada `v0.14.2` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.14.1` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.14.2 — a segunda rodada de triagem, e o falso-positivo mais
                    numeroso do alcance a Rust

Manifesto de release
--------------------
suite_version   : 0.14.2
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos   (NENHUM check novo)

Autoprova
---------
resultado       : OK
mutacoes        : 57 declaradas, 0 falhas

O QUE ESTA RODADA ACRESCENTA
----------------------------
A v0.14.1 triou os candidatos de P-19 e corrigiu quatro padroes. Esta
rodada triou os candidatos de P-18 — e achou o falso-positivo MAIS NUMEROSO
do alcance a Rust, mais uma armadilha que quase o transformou em
falso-negativo.

  (e) LEITURA CONTADA COMO PERSISTENCIA — 10 dos 17 sites do btv.
      `query_row("SELECT created_ts, email, nome FROM users ...")`,
      `query_map`, `query_as`. P-18 pergunta se o campo sensivel e GRAVADO
      sem cifra; um SELECT nao grava nada. Acusar isso produz um achado que
      o time NAO CONSEGUE CORRIGIR — nao ha escrita ali para consertar.

  (f) …MAS O NOME NAO PODE DECIDIR SOZINHO, e o btv provou.
      `sqlx::query_scalar("INSERT INTO users (..., email, ...)")` tem NOME
      de leitura e faz ESCRITA. Uma lista de nomes proibidos, sozinha,
      teria produzido FALSO-NEGATIVO no site que mais importa — trocando um
      defeito por outro pior. Agora o verbo do SQL vence o nome da chamada,
      e o nome so decide quando nao ha SQL no span. Ha teste-guarda na regua
      contra esvaziar `verbos_sql_de_escrita`.

  (g) `PASSWORD` COMO PALAVRA-CHAVE DO SQL, nao como coluna.
      `CREATE ROLE btv_app_teste LOGIN PASSWORD '...'` casava `password`
      como campo sensivel. Administrar role de banco e assunto de S-15 — um
      achado de P-18 aqui mandaria o time cifrar uma keyword.

A TERCEIRA SAIDA, PARA O QUE NAO E DECIDIVEL
----------------------------------------------
A tarefa nomeou "cifra em outra linha". As duas formas realistas ja eram
suprimidas pela varredura de cifra do repositorio inteiro (agora com teste).
Sobrou uma que NAO e decidivel:

  let blob = to_ciphertext(&t.cpf);        // embrulho da casa, fora da regua
  sqlx::query("INSERT INTO t (cpf) ...").bind(&blob).execute(p);

A coluna esta no literal e o valor vem de um identificador que a regua nao
reconhece como cifra. E A REGUA NAO E EDITAVEL PELO CONSUMIDOR — entao
inventar achado puniria quem cifrou, e inventar verde absolveria quem nao
cifrou. CheckIndeterminado com motivo, dizendo o que torna o site decidivel.
Quando o campo aparece FORA do literal (`.bind(&t.cpf)`), o valor cru esta
ali e vira achado. Teste-mordida dos dois lados.

O EFEITO, MEDIDO — E O QUE ELE NAO E
--------------------------------------
  sonda P-18 no btv (sem o portao do catalogo):
    candidatos     17
    ELIMINADOS     11    10 leituras + 1 DDL de role
    SOBREVIVEM      6    escritas de verdade, todas gravando `email`

  candidatos P-19:  161 -> 98   (-39%, v0.14.1)
  candidatos P-18:   17 ->  6   (-65%, esta versao)
  achados .rs no btv:  0 ->  0  (INALTERADO)

O LAUDO DO btv NAO MUDOU UMA VIRGULA: exit 20, 29 executados, 6 achados,
ZERO em `.rs`, antes e depois. Os refinos cortaram CANDIDATOS, nao achados —
porque o btv nao tinha nenhum. O ganho e para o proximo alvo Rust.

A TRAVA CONTRA O MODO DE FALHAR DE UM REFINO
----------------------------------------------
Refinar contra falso-positivo tem um jeito obvio de dar errado: cortar
demais e trocar por falso-negativo. `consumidor_rust_ruim` continua
disparando os QUATRO depois dos sete cortes, e ha teste especifico provando
que `sqlx::query_scalar("INSERT ...")` — nome de leitura, SQL de escrita —
continua mordendo.

VIOLACOES PROVAVEIS DEVOLVIDAS AO DONO: ZERO
----------------------------------------------
A tarefa pedia a lista de violacoes provaveis sobreviventes. Ela e VAZIA, e
sempre foi: o btv nao produziu achado `.rs` nenhum, em nenhuma das duas
rodadas. O mais proximo disso sao os SEIS sites de escrita de `email` que a
sonda de P-18 levanta COM O PORTAO DO CATALOGO DESLIGADO — e eles nao sao
achados: P-18 esta pulado no btv e continua pulado, porque sem catalogo nao
ha promessa a confrontar. Ficam como INCERTO (i), com a pergunta ao dono.

  O btv NAO FOI ALTERADO. Nenhum achado descartado sem classificacao.

REGUA ATUALIZADA, COM PISO VIGIADO
-----------------------------------
`pse/data/rust.yaml` ganhou `leituras_de_persistencia`,
`verbos_sql_de_escrita`, `verbos_sql_de_leitura` e
`ddl_de_credencial_de_banco`. O piso de `tests/test_regua.py` passou a
vigiar os quatro, mais `receptores_que_nao_sao_barramento` da v0.14.1 — que
tinha ficado sem guarda. Ha tambem trava contra um verbo estar em escrita E
leitura ao mesmo tempo, que faria a decisao depender da ordem do codigo.

IMPACTO NO CONSUMIDOR
---------------------
  * P-18 em Rust deixa de acusar SELECT e DDL de role. Repositorio que tinha
    achado por esses caminhos ve o achado sumir — e ele era falso.
  * P-18 em Rust passa a produzir exit 20 quando o valor ligado vem de um
    embrulho de cifra que a regua nao reconhece. E mudanca de comportamento,
    e esta na lista de ratificacao.
Exit codes INTACTOS. Schema sem mudanca. IDs INTACTOS. Catalogo 57/57.

VALIDACAO
---------
  * 614 passed com navegador real; clone limpo verde.
  * btv reprocessado: laudo identico, zero achado `.rs`.
  * `docs/triagem-btv-rust.md` com as duas rodadas, evidencia por
    classificacao e o segredo do `CREATE ROLE` mascarado.

PENDENCIAS DE RATIFICACAO
-------------------------
  1. O embrulho de cifra opaco -> exit 20 (novo nesta versao).
  2. Os quatro INCERTOS do relatorio — (i) e (ii) sao perguntas diretas.
  3. A regra de ambiguidade `env!` -> exit 20, de v0.14.0.
  4. A severidade assimetrica em Rust, de v0.14.0.
  5. Identidade dos SHAs do cockpit, de v0.13.0.
  6. `local_target`, de v0.13.0.
  7. P-24 em `privacy`, de v0.12.0.
  8. S-14 e S-15 como candidatos a CRITICO, de v0.9.0.
```
