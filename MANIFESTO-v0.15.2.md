# Manifesto de release — pse-suite v0.15.2

> Gerado por `pse --manifesto`. Tag anotada `v0.15.2` local.

```
pse-suite v0.15.2 — as nove ratificacoes, seladas

Manifesto de release
--------------------
suite_version   : 0.15.2
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos

Autoprova       : OK · 57 mutacoes declaradas, 0 falhas

NENHUMA MUDANCA DE COMPORTAMENTO
--------------------------------
Este commit nao muda uma linha de logica de check. Ele SELA nove decisoes de
contrato que ja estavam implementadas e testadas, e que viviam espalhadas
como "pendente de ratificacao" por nove manifestos diferentes.

O problema era de ENDERECO, nao de conteudo: quem chegasse na v0.15 teria de
ler nove documentos para saber o que ja fora decidido e o que seguia aberto.
Na pratica ninguem leria — e decisao que ninguem encontra nao foi tomada.

AS NOVE
-------
  1  local_target                       v0.13.0
  2  excecao de loopback (host exato)    v0.11.0
  3  P-24 no pilar privacy               v0.12.0
  4  S-14 e S-15 permanecem ALTO         v0.9.0
  5  env! -> CheckIndeterminado          v0.14.0
  6  severidade textual Rust assimetrica v0.14.0
  7  cifra opaca -> CheckIndeterminado   v0.14.2
  8  achado + indeterminacao coexistem   v0.15.0
  9  qualificacao do que foi observado   v0.15.1

Todas decididas PARA O LADO SEGURO — bloquear em vez de adivinhar, ALTO em
vez de CRITICO sem certeza, nomear a lacuna em vez de calar. Tres delas
(5, 7, 8) existem porque o alvo real mostrou um caso em que os dois lados
obvios estariam errados, e a resposta certa era a terceira: nao decidir, e
dizer que nao decidiu.

O LEDGER SELA PELO COMPORTAMENTO, NAO PELA PROSA
--------------------------------------------------
`docs/RATIFICACOES.md` afirma que as nove estao fechadas. Uma tabela que
afirma isso e nao e verificada e pior que tabela nenhuma: ela parece
autoridade. `tests/test_ratificacao.py` da a cada linha o teste que a torna
verdadeira — se o comportamento mudar, a linha vira falsa e o arquivo
reprova.

Ha tambem duas travas sobre o proprio ledger: ele tem de listar exatamente
nove, cada uma nomeando a versao de origem, e a secao "o que segue pendente"
nao pode esvaziar. Zero pendencia num projeto vivo e sinal de que alguem
parou de registrar, nao de que tudo foi decidido.

OS MANIFESTOS NAO FORAM REESCRITOS
-----------------------------------
Cada manifesto e o registro do que se sabia NAQUELE momento. Edita-los para
dizer "ratificado" falsificaria a historia que eles existem para guardar. Ha
teste que reprova se a secao de pendencias comecar a sumir dos manifestos
antigos.

O QUE SEGUE PENDENTE
--------------------
  * medir `/dev` no arranjo real (imagem Docker, origem compartilhada)
  * a gramatica dos 3 arquivos .ts/.tsx servidos
  * identidade dos SHAs do cockpit
  * o btv declarar catalogo (habilita P-18) e data_residency (habilita S-16)

VALIDACAO
---------
  * 661 passed com navegador real; clone limpo verde.
  * 17 testes novos, todos selando comportamento ja existente.
  * Zero alteracao em pse/checks/ — verificavel no diff.
```
