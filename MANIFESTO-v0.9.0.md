# Manifesto de release — pse-suite v0.9.0

> Gerado por `pse --manifesto`. Tag anotada `v0.9.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.8.0` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.9.0 — pacotes fundadores de API e backend

Manifesto de release
--------------------
suite_version   : 0.9.0
commit          : 07da726e970fe9d3491a01db03751a31cced066a
catalog_hash    : 2c613cca9d5ba1e605467c5fa51b91e257aee65fefb6817d98c0095897c149cc
schema_version  : laudo-pse-1.0
checks          : 48 implementados, 0 previstos
por dominio     : {'frontend': 3, 'api': 15, 'backend': 16, 'data': 14, 'ai': 15}

Autoprova
---------
resultado       : OK
mutacoes        : 48 declaradas, 0 falhas

RATIFICACAO — CONJUNTO CRITICO ATUALIZADO
-----------------------------------------
O conjunto CRITICO era, desde o plano §4 + Etapa 3 §2.4:

  P-01, P-06, P-08, P-11, S-01, S-04(dpa), S-06, E-04
  + P-07, P-13, P-14, E-11, S-10, S-11 (rodadas seguintes)

RATIFICADO NESTA VERSAO:

  P-15 passa a ter severidade CONDICIONAL
       campo `class: sensitive` sem finalidade de treino -> CRITICO
       campo pessoal comum sem finalidade de treino      -> ALTO

Principio, dado pelo arquiteto: Art. 11 e trava ESTRUTURAL, nao gradiente
— o mesmo que ja rege P-08. A entrega da v0.8.0 registrou a duvida em vez
de resolve-la sozinha, porque S-04 precisou de ratificacao explicita e o
conjunto CRITICO e fixado por precedente.

A graduacao e o ponto: se tudo virasse CRITICO, o operador perderia a ordem
de prioridade. D-08 continua valendo dos dois lados — declarar a finalidade
de treino desliga o achado, sensivel ou nao, e ha teste provando isso.

PACOTE FUNDADOR DE API (dominio `api`)
--------------------------------------
A matriz de v0.7.0 dizia a verdade incomoda: 12 checks e NENHUM nascido
olhando para o estrato. Densidade por heranca nao e cobertura.

  S-12 ALTO  Ontologia `x-ethics` ausente ou nao implementada no contrato.
             Dois vetores: schema com PII sem declaracao, e declaracao que
             promete campo que o DTO nao tem. O segundo e o de maior valor.
  P-17 ALTO  Endpoint de busca aceita filtro sensivel. Discriminacao sem
             modelo nenhum. Le a view (AST) e a spec.
  S-13 ALTO  Resposta de erro expoe pilha, caminho, versao ou `debug=True`.
             `log.exception` NAO e achado.

PACOTE FUNDADOR DE BACKEND (dominio `backend`)
----------------------------------------------
Mesmo diagnostico. O proprio do backend e a INFRA que so existe deste lado.

  S-14 ALTO  Dump de producao em ambiente inferior sem descaracterizar.
  S-15 ALTO  Role de banco com privilegio excessivo.
  P-18 ALTO  Sensivel sem cifra de aplicacao com chave gerenciada.
  P-19 ALTO  Log append-only com PII sem crypto-shredding.
  S-16 ALTO  Persistencia fora da residencia declarada.

REGUAS NOVAS
------------
pse/data/api-contract.yaml e pse/data/backend-infra.yaml, ambas com piso
vigiado. Dois testes de regua pegaram hardcoding durante a rodada e o
levaram para o YAML. O teste de "lista propria" passou a olhar a AST e so
reprova string que participa de COLECAO ou comparacao — procurar o termo no
arquivo inteiro reprovava a docstring que explica o check.

scan.nome_casa_tokens(): marca composta (`validar_filtro`) exige que TODOS
os seus tokens sejam prefixo de algum token do nome. Casa `validar_filtros`
e nao casa `validar_email`.

FIXTURE CORRIGIDA, NAO CHECK AFROUXADO
--------------------------------------
P-18 passou a acusar `consumidor_bom`, construida antes dele:
`clientes.genero` e sensivel e nao declarava cifra. O achado esta CERTO — a
fixture e que precisava declarar `encryption` com `key_management`.

IMPACTO NO CONSUMIDOR
---------------------
Oito checks ALTO novos: repositorio que antes saia 0 pode passar a sair 11.
P-15 sobre campo sensivel passa de 11 para 10. Bump MINOR porque nao ha 1.x
publicado; em 1.x isto seria major.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma.
IDs INTACTOS: nada renomeado, so acrescentado.

BURACO ASSUMIDO
---------------
`ethics x frontend` permanece o unico vazio, com leitura assinada em
pse/matriz.py e teste que impede fechamento silencioso.

PENDENCIA DE RATIFICACAO
------------------------
Os oito novos sairam ALTO. S-14 (dump de producao em staging) e S-15
(grant amplo) sao candidatos defensaveis a CRITICO, mas nao ampliei o
conjunto por conta propria: o principio ratificado para P-15 e "violacao
legal ESTRUTURAL", e estes dois sao falha de seguranca, nao proibicao
per se. Fica registrado para decisao.
```
