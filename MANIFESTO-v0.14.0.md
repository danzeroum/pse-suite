# Manifesto de release — pse-suite v0.14.0

> Gerado por `pse --manifesto`. Tag anotada `v0.14.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.13.0` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.14.0 — quatro vetores em Rust, e nenhum parser

Manifesto de release
--------------------
suite_version   : 0.14.0
catalog_hash    : 4cb64d7e63b37515f600615ad445a36a21a33ba4e5e88165c2cf037a87856820
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos   (NENHUM check novo)

Autoprova
---------
resultado       : OK
mutacoes        : 57 declaradas, 0 falhas

A DECISAO, E DE ONDE ELA VEIO
-----------------------------
NAO fazer parser de Rust. A decisao nao foi de gosto: veio da medicao da
v0.13.0, que separou o que um parser compraria do que ele nao compraria e
mostrou que o degrau `literal` — quatro vetores alcancaveis SEM GRAMATICA
NENHUMA — era o unico com retorno claro.

E exatamente isso que esta versao entrega. Quatro checks EXISTENTES passaram
a reconhecer `.rs`; nenhum check novo nasceu; nenhuma arvore foi construida.

  S-06  chave hardcoded              literal numa ligacao let/const/static
  P-18  campo sensivel sem cifra     chamada de cifra sobre o campo
  P-19  evento sem crypto-shredding  producao com PII no span do payload
  S-16  persistencia sem jurisdicao  regiao literal numa chamada de conexao

O QUE `pse/engine/rustscan.py` FAZ, E O QUE ELE NAO FAZ
--------------------------------------------------------
faz     apaga comentario e resolve literal com as regras de Rust; acha
        ligacoes com valor literal; acha chamadas com o span de argumento
        delimitado por parenteses balanceados; distingue macro de chamada.
NAO faz arvore, tipos, escopo, resolucao de `use`, generics, macro
        expandida. Check que precise disso continua declarando Rust fora do
        seu alcance — e o mapa continua dizendo isso em voz alta.

TRES CONSTRUCOES QUE O APAGADOR GENERICO ERRA, CADA UMA PARA UM LADO
---------------------------------------------------------------------
  * COMENTARIO DE BLOCO ANINHADO. `/* a /* b */ c */` e valido em Rust; um
    apagador que pare no primeiro `*/` deixa ` c */` valendo como codigo, e
    um segredo comentado volta a ser fato. Erra para MAIS achado.
  * TEMPO DE VIDA. `&'a str` comeca com aspa simples; tratado como abertura
    de literal, engole linhas inteiras de codigo real. Erra para MENOS
    achado, em silencio.
  * STRING CRUA. `r#"... " ..."#` e comum em SQL embutido; sem entende-la o
    fim do literal cai errado e o arquivo inteiro desalinha.
As tres aparecem em Rust rotineiro. Nenhuma era opcional.

PRECISAO SOBRE RECALL — A POLITICA, E ONDE ELA MORDE
------------------------------------------------------
Sem arvore o casamento e mais fragil, entao a regra e errar para MENOS
achado. Falso-positivo num alvo real ensina o time a ignorar o pack inteiro,
e esse custo e maior que o do achado perdido.

  CRITICO so com FORMATO conhecido (AKIA, sk-, ghp_, xox, AIza, PEM, JWT):
    ali o casamento textual nao introduz ambiguidade.
  ALTO   nome de credencial + literal longo de formato desconhecido:
    provavelmente e chave, e "provavelmente" nao merece o grau maximo.
  minimo de 16 caracteres (Python usa 12): cada caractere a menos e um
    falso-positivo a mais quando nao ha arvore para desempatar.
  ancora na ESTRUTURA: `const REGION: &str = "us-east-1"` solto NAO dispara
    S-16 — nao se sabe se ele chega a alguma persistencia.

A AMBIGUIDADE BLOQUEIA, E ELA E UMA SO
---------------------------------------
`env!("API_KEY")` grava o valor no BINARIO em tempo de compilacao — nao le o
ambiente em execucao. Se o valor e um segredo, o binario carrega um segredo,
e o texto do `.rs` nao diz qual. Achado seria inventar; verde seria
conveniencia. E o caso exato de "pode ou nao ser o vetor":
CheckIndeterminado com motivo, nomeando arquivo, linha e macro. Exit 20.
`std::env::var` (execucao) e decidivel e nao bloqueia — ha teste-mordida dos
dois lados, senao o gate seria inutil.

`.rs` NAO ENTRA EM `COM_PARSER` — TERCEIRA CATEGORIA NO BLOCO `alcance`
------------------------------------------------------------------------
As duas leituras faceis seriam falsas em direcoes opostas. "Rust: lido"
faria um leitor concluir que os 57 checks olharam o motor; "Rust: nao lido"
esconderia o alcance que existe. Entao ha uma terceira lista, com os checks
NOMEADOS, e a nota diz literalmente: ausencia de achado DESSES QUATRO
significa "olhei e esta limpo"; ausencia de achado de qualquer outro check
nesses arquivos nao significa nada.

NAO-APLICAVEL VIROU MEDIDO, E A MEDICAO CONTRARIOU A EXPECTATIVA
------------------------------------------------------------------
A rodada partia da leitura de que o Rust do btv seria MAJORITARIAMENTE
nao-aplicavel — motor gRPC/sandbox/ledger, sem consentimento nem dark
pattern. Em vez de aceitar isso (alegar nao-aplicabilidade e a forma mais
confortavel de inflar cobertura), a suite passou a SONDAR: para cada check
com vetor em backend, procura nos `.rs`, sem comentario e sem literal, as
marcas daquele vetor.

  Resultado: 2 checks — P-02 e P-03. Nao a maioria.

Logger, hash, serde, tratamento de erro e cliente HTTP estao todos presentes
no motor, entao os vetores de P-01, S-13, P-20, S-12 e S-04 EXISTEM la e
seguem sem ser olhados. A divergencia entre a expectativa e a medicao fica
registrada no documento — e o ponto de medir.

O DELTA CONTRA O btv (a3e14f45), E COMO LE-LO
-----------------------------------------------
                                          antes    agora
  Linhas lidas por parser                  47,0%    47,0%
  Linhas em alcance parcial (4 vetores)      —      50,8%
  Linhas cegas para TODO check             53,0%     2,2%
  Checks auditados de verdade                13       16
  Checks meio-cegos em Rust                  19       13

O 53% -> 2,2% e real e e o ganho da rodada. Mas ele acontece porque 38 mil
linhas sairam de CEGAS e entraram em ALCANCE PARCIAL, nao em LIDAS: quatro
checks passaram a olha-las, treze continuam sem ver nada ali. Ler a primeira
linha como se fosse cobertura seria a fachada que esta serie de rodadas
existe para impedir — e por isso as tres fatias nunca sao somadas.

O btv esta LIMPO nos quatro vetores: zero achado em `.rs`. Nao-achado que
agora significa alguma coisa.

DEFEITOS ACHADOS PELO PROPRIO INCREMENTO
-----------------------------------------
  1. IndexError em ligacao de valor VAZIO (`let x =` com a expressao na
     linha seguinte). Achado pelo btv real: derrubava S-06 inteiro para
     indeterminado — bloqueio por defeito da suite, nao do alvo.
  2. A supressao D-08 de P-18 em Rust valia so para o "vao" e nao para o
     catalogo inteiro: um consumidor cujo motor cifra de verdade seria
     punido por o catalogo nao declarar. Punir quem protegeu e o pior sinal
     que uma suite pode mandar.
  3. P-19 nao via PII que chegasse ao payload por uma ligacao local — o caso
     IDIOMATICO em Rust. Resolvido com UM salto, declarado como tal: dois
     saltos, campo de struct ou outro modulo seguem invisiveis, e isso e
     lacuna conhecida, nao descuido.

TRAVAS QUE MORDERAM (as tres, como deviam)
-------------------------------------------
  * `test_o_alcance_registrado_ainda_bate_com_o_alvo` reprovou: Rust saiu de
    fora-de-alcance. Obrigou a atualizar a afirmacao em vez de deixar o
    documento continuar dizendo o que era.
  * O aceite do btv reprovou pelo mesmo motivo, e o baseline ganhou
    `alcance_parcial: {Rust: [S-06, P-18, P-19, S-16]}` — fixado porque o
    perigo desta linha e ela crescer sozinha.
  * `test_toda_fixture_no_disco_esta_versionada` pegou as fixtures novas
    antes do commit.

IMPACTO NO CONSUMIDOR
---------------------
  * Consumidor com Rust pode ver achados NOVOS de S-06/P-18/P-19/S-16. Sao
    legitimos: o codigo nunca tinha sido olhado.
  * `env!` numa ligacao de credencial passa a produzir exit 20. Trocar por
    `std::env::var` resolve, e a mensagem diz isso.
  * Laudo ganha `alcance.alcance_parcial` e `alcance.arquivos_em_alcance_parcial`
    (campos novos; nenhum existente mudou de forma).
  * `proporcao` ganha `linhas_em_alcance_parcial` e `percentual_alcance_parcial`.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma. IDs INTACTOS.
Catalogo 57/57 — nenhum check novo.

VALIDACAO
---------
  * 599 passed com navegador real.
  * Aceite do btv: `conforme` com o baseline atualizado.
  * btv ao vivo (Vite em 127.0.0.1:5178, `local_target`): 29 executados,
    veredito indeterminado, exit 20, seis achados — os mesmos de antes.

PENDENCIAS DE RATIFICACAO
-------------------------
  1. A regra de ambiguidade (`env!` -> exit 20) e mudanca de comportamento
     para consumidor com Rust.
  2. A severidade assimetrica: CRITICO textual so com formato conhecido.
  3. Identidade dos SHAs do cockpit (`d6ae70ea` / `1da4d51`), de v0.13.0.
  4. `local_target`, de v0.13.0.
  5. P-24 em `privacy`, de v0.12.0.
  6. S-14 e S-15 como candidatos a CRITICO, de v0.9.0.
```
