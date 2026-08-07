# Manifesto de release — pse-suite v0.10.0

> Gerado por `pse --manifesto`. Tag anotada `v0.10.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.9.0` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.10.0 — a matriz fecha: os cinco dominios com fundador proprio

Manifesto de release
--------------------
suite_version   : 0.10.0
commit          : e95559db74f8e0f6bc4d559c58514ed6fbe90b70
catalog_hash    : 0db572672a4d1a3758c4ded3fdb71b71703185112236050a1c8adf94ee6de575
schema_version  : laudo-pse-1.0
checks          : 49 implementados, 0 previstos
por dominio     : {'frontend': 3, 'api': 15, 'backend': 16, 'data': 15, 'ai': 15}

Autoprova
---------
resultado       : OK
mutacoes        : 49 declaradas, 0 falhas

O QUE MUDA vs 0.9.0
-------------------
  P-20  Hash deterministico sem chave tratado como anonimizacao.
        ALTO para pessoal comum, CRITICO para sensivel.

        `sha256(cpf)` gravado numa coluna `class: anonymized` retira o dado
        da retencao, da base legal e do direito de eliminacao — com base
        numa afirmacao falsa. O CPF tem ~10^11 valores validos: o
        dicionario completo se constroi em segundos, e o Art. 12 so dispensa
        o dado que NAO PODE ser revertido por meios razoaveis e disponiveis.

        Nenhum dos 48 anteriores pegava. P-06 audita onde a chave mora, e
        aqui nao ha chave. P-18 audita a ausencia de cifra, e aqui alguem
        "cifrou" no sentido errado da palavra.

        D-08 e o ponto delicado, porque o caso correto e o que P-06 VALIDA:
        HMAC com chave de cofre, sal aleatorio por registro, KDF e `key=`
        nao disparam. O grupo `credenciais` da regua fica fora por
        construcao — hashear senha e o que se deve fazer.

A MATRIZ FECHA
--------------
Com P-20, os cinco dominios tem pelo menos um check NASCIDO do estrato, em
vez de etiquetado a posteriori:

  frontend  P-13 P-14 S-09          (v0.6.0)
  ai        S-10 S-11 P-15 P-16     (v0.8.0)
  api       S-12 P-17 S-13          (v0.9.0)
  backend   S-14 S-15 P-18 P-19 S-16 (v0.9.0)
  data      P-20                    (esta versao)

Ha teste que reprova se a leitura de densidade de qualquer dominio deixar
de afirmar um check proprio.

P-21 — INVESTIGADO E FORA DE ESCOPO ESTATICO
--------------------------------------------
Zona bruta de data lake com acesso irrestrito e risco real e NAO virou
check. A decisao esta assinada em pse/matriz.py (FORA_DE_ESCOPO_ESTATICO),
no mapa gerado, no catalogo e num teste que reprova se P-21 aparecer sem
que ela seja revista.

  1. Identificar a zona bruta viria do NOME do bucket (raw/bronze/landing).
     E mencao, nao fato — o D-01 proibe esse atalho, ainda mais num check
     cuja consequencia seria bloquear CI.
  2. Policy sem `Condition` no Terraform nao e violacao por si: a restricao
     pode viver numa SCP, num permission boundary, num grant de Lake
     Formation ou no provedor de identidade, todos FORA do repositorio. O
     check acusaria setup correto — o D-08 ao contrario.
  3. A suite nao tem parser de HCL, e adicionar um para avaliar uma forma
     de politica que nao se consegue decidir seria construir a APARENCIA
     de cobertura.

  O que faria P-21 nascer: policy-as-code versionada declarando finalidade
  e expiracao por zona. Ai ha declaracao a confrontar com fato, que e como
  todos os outros funcionam.

  Buraco honesto e melhor que check que nao verifica nada real.

REGUA NOVA
----------
pse/data/anonimizacao.yaml, com piso vigiado. Separada de backend-infra de
proposito: os verbos daqui sao de LINHA (`insert`, `save`, `write`) e os de
la sao de CONEXAO (`create_engine`, `client`, `bucket`). Juntar os dois
faria S-16 passar a olhar `save()` e P-20 passar a olhar `create_engine()`.

IMPACTO NO CONSUMIDOR
---------------------
Um check novo. Repositorio que grave hash nu de identificador passa a sair
11 — ou 10, se o campo for sensivel. Bump MINOR porque nao ha 1.x
publicado; em 1.x isto seria major.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma.
IDs INTACTOS: nada renomeado, so acrescentado.

BURACO ASSUMIDO
---------------
`ethics x frontend` permanece a unica celula vazia, com leitura assinada e
teste que impede fechamento silencioso. AST sozinha nao decide se um botao
e coercitivo.

CONJUNTO CRITICO NESTA VERSAO
-----------------------------
  P-01, P-06, P-07, P-08, P-11, P-13, P-14, S-01, S-04(dpa), S-06,
  S-10, S-11, E-04, E-11
  + condicionais por sensibilidade: P-15, P-20

PENDENCIA DE RATIFICACAO
------------------------
Segue aberta a de v0.9.0: S-14 (dump de producao em staging) e S-15 (grant
amplo) sao candidatos defensaveis a CRITICO. Nao ampliei o conjunto por
conta propria — o principio ratificado e "violacao legal ESTRUTURAL", e
esses dois sao falha de seguranca, nao proibicao per se.
```
