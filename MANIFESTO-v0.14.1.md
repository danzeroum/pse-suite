# Manifesto de release — pse-suite v0.14.1

> Gerado por `pse --manifesto`. Tag anotada `v0.14.1` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.14.0` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.14.1 — a triagem que nao achou violacao, e achou quatro defeitos

Manifesto de release
--------------------
suite_version   : 0.14.1
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos   (NENHUM check novo)

Autoprova
---------
resultado       : OK
mutacoes        : 57 declaradas, 0 falhas

A PREMISSA NAO SE CONFIRMOU
---------------------------
A rodada partia de que os quatro checks com alcance a Rust tinham ACHADO
algo contra o btv. Nao acharam.

  S-06  executou   0 achados .rs
  P-19  executou   0 achados .rs
  P-18  PULADO     o btv nao tem catalogo de dados
  S-16  PULADO     o btv nao declara `data_residency`

Metade dos checks com alcance a Rust nunca chegou a olhar o Rust — e isso
so aparece porque o balde `checks_pulados` existe e carrega motivo.

ZERO ACHADO NAO E RESULTADO: E AFIRMACAO
-----------------------------------------
E afirmacao precisa de prova, senao "zero" e indistinguivel de "o scanner
nunca alcancou os arquivos". A triagem virou duas perguntas.

  (1) OS CHECKS OLHARAM?
      S-06: 137 arquivos varridos, 3.225 ligacoes reconhecidas, 5 com nome
            de credencial, 1 com literal, 0 acima do minimo. O funil fecha
            por motivo verificavel.
      SONDA CEGA (sem filtro de nome, todo literal >= 16 caracteres em
            qualquer ligacao): ZERO. O limite nao e a regua — nao ha
            literal com forma de segredo em ligacao Rust nenhuma do btv.
      P-19: 161 chamadas de producao consideradas em 18 arquivos.
      S-16: rodado com politica HIPOTETICA (`data_residency: BR`) so para a
            triagem — zero. Vale para `.rs`; o Terraform segue fora.

  (2) O QUE ELES CONSIDERARAM E DESCARTARAM?
      Foi aqui que a triagem deu retorno.

QUATRO PADROES DE FALSO-POSITIVO LATENTE — CORRIGIDOS NO CHECK
----------------------------------------------------------------
Nenhum gerou achado no btv. Todos eram candidatos considerados, e num
repositorio cujo canal carregasse uma struct com `cpf` os quatro teriam
disparado. Nao dispararam POR SORTE, e sorte nao e controle.

  (a) DEFINICAO TRATADA COMO CHAMADA — o mais grave, e afeta os quatro.
      `fn append(&mut self, kind: &str, payload: Value)` entrava como
      chamada, e a ASSINATURA era varrida como span de argumento. Num
      arquivo com `fn append(&mut self, cpf: &str)`, o check acusaria a
      PROPRIA DECLARACAO — um achado que nao tem como ser corrigido, porque
      nao ha defeito nenhum ali. `fn connect(...)` viraria chamada de
      persistencia em S-16 pelo mesmo caminho.

  (b) CANAL tokio CONTADO COMO BARRAMENTO. O btv tem LEDGER no dominio: a
      marca aparece em 18 arquivos, e a regra "o modulo fala com barramento"
      tornava elegivel todo `send` deles. 142 DOS 161 candidatos eram
      elegiveis SO pelo modulo. `tx.send(event)` de canal nao e escrita em
      registro imutavel — o Art. 18 VI nao tem nada a dizer sobre ele.

  (c) CANAL COM NOME SUFIXADO sobreviveu ao primeiro refino. `agent_evt_tx`
      nao casa com o token exato `tx`. OITO passaram. Achado porque medi de
      novo DEPOIS de corrigir, e nao porque o refino pareceu suficiente.

  (d) VARIANTE DE ENUM contada como metodo. `UiCommand::Send(payload)` e
      construcao, nao chamada — em Rust idiomatico metodo e snake_case e
      variante e CamelCase.

EFEITO MEDIDO, E A TRAVA CONTRA TROCAR UM DEFEITO POR OUTRO
-------------------------------------------------------------
  candidatos P-19 no btv:  161 -> 114 -> 98      (-39%)
  achados P-19 no btv:       0 ->   0 ->  0      (inalterado)
  achados na fixture ruim:   1 ->   1 ->  1      (inalterado)

Refinar contra falso-positivo tem um modo de falhar obvio: cortar demais e
trocar por falso-negativo, que e pior. Ha teste-mordida provando que o
produtor legitimo (`ledger.append`) continua mordendo depois dos quatro
cortes.

A LICAO DO ALVO REAL VIRA CASO PERMANENTE
------------------------------------------
As quatro formas entraram em `consumidor_rust_bom` — definicao de funcao,
canal tokio, canal sufixado, requisicao HTTP do reqwest, variante de enum e
`fn connect`. O arquivo novo menciona `ledger` DE PROPOSITO: era exatamente
essa mencao, num dominio que tem ledger, que tornava tudo elegivel.

QUATRO INCERTOS PARA O DONO — E ZERO INCERTO SERIA SUSPEITO
-------------------------------------------------------------
  (i)   P-18 nunca rodou. Sonda sem o portao do catalogo: 17 sites de
        persistencia `.rs` carregando nome de PII (`email`, `nome` em
        `INSERT INTO users`). PODE ou nao ser violacao — sem catalogo nao ha
        promessa a confrontar. PERGUNTA: o btv vai declarar catalogo?
        Um dos 17 e ruido demonstravel (`"problema de login e senha"` numa
        string de teste) — e o portao do catalogo e justamente o que da
        precisao a P-18, entao isso NAO e defeito a corrigir.
  (ii)  S-16 nunca rodou. PERGUNTA: qual a residencia declarada do btv, e
        onde ela vive? A infra e Terraform, fora de alcance.
  (iii) `const TOKEN_OK: &str = "btvs_valido"` foi descartado por TAMANHO
        (11 < 16), nao por a suite ter entendido que e fixture de teste. Um
        token real de 11 caracteres escaparia pela mesma porta. O dono
        decide se o limiar e aceitavel.
  (iv)  `token_hash = sha256_hex(&token)` toca o vetor de P-20, que NAO tem
        alcance a `.rs`. Aqui o hash e de segredo aleatorio de 256 bits e
        provavelmente esta certo — mas quem afirma isso sou eu lendo, nao um
        check.

O QUE A SUITE AFIRMA, E O QUE ELA NAO AFIRMA
----------------------------------------------
AFIRMA, com prova de leitura: sem credencial hardcoded em ligacao Rust; sem
producao de evento com PII no payload; sem literal de regiao em chamada de
conexao `.rs`.
NAO AFIRMA: nada sobre cifra de campo sensivel (P-18 nao rodou); nada sobre
jurisdicao (S-16 nao rodou, Terraform fora de alcance); nada sobre os outros
53 checks no Rust do btv — 13 seguem meio-cegos; nada sobre PII que chegue
ao payload por DOIS saltos.

O btv NAO FOI ALTERADO. Nenhum achado descartado sem classificacao.

IMPACTO NO CONSUMIDOR
---------------------
  * P-19 em Rust deixa de considerar canal, requisicao HTTP e variante de
    enum. Repositorio que tinha achado por esses caminhos pode ver o achado
    sumir — e ele era falso.
  * `rustscan.chamadas()` nao devolve mais definicao de funcao. Afeta os
    quatro checks, sempre para MENOS achado.
Exit codes INTACTOS. Schema sem mudanca. IDs INTACTOS. Catalogo 57/57.

VALIDACAO
---------
  * 608 passed com navegador real.
  * btv reprocessado apos os refinos: zero achado `.rs`, inalterado.
  * `docs/triagem-btv-rust.md` com evidencia de cada classificacao, e teste
    que reprova se algum trecho com forma de credencial entrar nele.

PENDENCIAS DE RATIFICACAO
-------------------------
  1. Os quatro INCERTOS acima — (i) e (ii) sao perguntas diretas ao dono.
  2. A regra de ambiguidade (`env!` -> exit 20), de v0.14.0.
  3. A severidade assimetrica em Rust, de v0.14.0.
  4. Identidade dos SHAs do cockpit, de v0.13.0.
  5. `local_target`, de v0.13.0.
  6. P-24 em `privacy`, de v0.12.0.
  7. S-14 e S-15 como candidatos a CRITICO, de v0.9.0.
```
