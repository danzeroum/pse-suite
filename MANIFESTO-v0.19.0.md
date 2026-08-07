# Manifesto de release — pse-suite v0.19.0

> Gerado por `pse --manifesto`. Sem tag: o proxy de git deste ambiente recusa
> push de tag. O manifesto versionado no repositorio e o registro.

```
pse-suite v0.19.0 — a etiqueta de finalidade ganhou consequencia

Manifesto de release
--------------------
suite_version   : 0.19.0
schema_version  : laudo-pse-1.0
catalog_hash    : 96574901f8a2c4da022e4ac39216dab84f500368038fbdc5923a3dcf511c176e
checks          : 58 implementados, 0 previstos   (+1: S-22)

Autoprova       : OK · 58 mutacoes declaradas, 0 falhas
Suite           : 730 passaram, 8 puladas   (era 713 + 8)

SEIS MATERIAIS, UM CHECK — E ISSO E O RESULTADO
-----------------------------------------------
Foram avaliados seis materiais de security (api, backend, dados, ia, partner,
designDireito). Quase tudo ja tinha dono:

  BOLA / IDOR                  -> S-01
  minimizacao por jornada      -> P-05
  hash como anonimizacao       -> P-20
  terceiro sem DPA             -> S-04
  dado pessoal em treino       -> P-15
  filtro sensivel na busca     -> P-17
  erro expondo internals       -> S-13

Um unico vetor sobreviveu. A convergencia nao e falha de leitura: e o sinal
de que a regua GENERALIZOU alem dos exemplos que a produziram. A suite parou
de crescer porque cobriu o essencial, e registrar isso importa tanto quanto
registrar o check novo — sem o registro, a proxima rodada refaz a avaliacao
achando que faltou alguma coisa.

O que sobrou e o vetor mais FINO de todos, e e por isso que ele escapou.

S-22 — BASE LEGAL AMARRADA A FINALIDADE
---------------------------------------
S-07 verifica que a finalidade e propagada (`X-Purpose`) e registrada no log
de auditoria. Ele responde "o sistema sabe PARA QUE o dado foi lido?" — Art.
37, rastreabilidade, e ele responde a pergunta inteira.

A pergunta seguinte e de LEGALIDADE: **aquela finalidade podia rodar sob
aquela base?** Um sistema pode propagar `X-Purpose: marketing`, registrar
isso impecavelmente, e processar sob legitimo interesse. O log, que era a
prova de conformidade, vira a prova documental da infracao — ele registra com
precisao que a operacao ilegal aconteceu, e para que.

S-07 verifica que a etiqueta existe. S-22 verifica que a etiqueta tem
CONSEQUENCIA. Um sistema passa o primeiro e falha o segundo, e e o caso
comum: por isso sao dois IDs.

  pilar        security   (e enforcement de acesso por finalidade)
  dominio      api
  tipo         estatico + runtime opcional
  modo         active     (a sonda espera rejeicao — regra ratificada)
  severidade   ALTO       (criterio de S-14/S-15: grave, e ainda nao e
                           exposicao consumada)
  base legal   Art. 6o I (finalidade) + Art. 7o (base legal)

O FATO, EM DUAS PARTES — E A SEGUNDA E A QUE IMPORTA
----------------------------------------------------
1. O MAPA finalidade -> base legal existe. Duas formas, ambas estrutura:
   dicionario LITERAL no codigo cujos valores sao bases do Art. 7o, ou lista
   de finalidades com base por entrada na declaracao (a forma que
   `consent-model.yaml` ja usa).

2. A COMBINACAO INVALIDA E RECUSADA. Uma funcao que consulta o mapa e, no
   mesmo corpo, recusa — `raise`, `abort`, status de rejeicao.

Sem a segunda, o mapa e decorativo, e esse e o SEGUNDO achado — o mais
interessante dos dois, porque o alvo que o recebe ja fez o trabalho dificil
de escrever a tabela. Uma tabela que ninguem consulta e papel, e papel nao e
enforcement.

`# TODO: validar legal basis por finalidade` nao e mapa nem checagem.
Comentario nao chega a arvore sintatica (D-01), e a fixture ruim carrega
exatamente esse comentario para provar.

OS DESFECHOS, E A FRONTEIRA QUE CUSTOU UMA CORRECAO
---------------------------------------------------
PULA quando nenhum ponto do codigo LE a finalidade da requisicao: sem lugar
onde ela chegue nao ha lugar onde a base possa ser exigida, e o motivo nomeia
S-07.

A primeira versao tratava `purposes:` declarado como superficie, e passou a
acusar `consumidor_bom` e `consumidor_data_bom` — repositorios de dados que
declaram finalidades e nao tem servidor nenhum. Corrigido: declaracao e uma
das formas do MAPA, nunca o gatilho. Finalidade declarada e nao lida e
defeito de propagacao, que ja e de S-07.

INDETERMINA quando ha finalidade entrando, ha identificador com nome de mapa
de base legal (`BASES_LEGAIS = carregar_config(...)`) e o que ele guarda nao
e literal decidivel. Precisao sobre recall: o pior desfecho possivel seria
adivinhar.

A REGUA, E O PISO INVERTIDO
---------------------------
`pse/data/legal-basis.yaml` — as bases do Art. 7o e do Art. 11, com sinonimo
em ingles, mais a superficie de finalidade, as formas de declaracao e as
formas de recusa. Nunca no `.py` do check (D-13).

Ha DOIS pisos vigiados, e o segundo e novo em especie:

  test_regua_da_base_legal_e_vigiada       remover uma base faz S-22 parar de
                                           reconhecer o mapa de quem acertou
  test_finalidade_disfarcada_nunca_entra   `analytics`, `melhoria_do_produto`,
  _como_base_legal                         `interesse_do_negocio` NAO podem
                                           entrar na lista — nenhuma esta no
                                           Art. 7o, e acrescenta-las INVERTE
                                           o sentido do check: ele passaria a
                                           abencoar exatamente o que existe
                                           para reprovar, e o teste ficaria
                                           verde porque o achado sumiria

OS DOIS CANDIDATOS QUE NAO VIRARAM CHECK
----------------------------------------
Registrados em `docs/BURACOS-ASSUMIDOS.md` e assinados em `pse/matriz.py`,
com leitura completa em cada um. NAO implementados.

  ACESSO DO TITULAR (Art. 18 II). O check possivel seria "existe rota de
  exportacao?" — e isso JA e P-10, que roda no ar e confirma que ela responde
  e devolve conteudo integro. O que faria dele um check novo seria verificar
  que a resposta traz os dados DAQUELE titular, TODOS eles, DENTRO DO PRAZO:
  a primeira exige conhecer o conjunto correto (so o alvo sabe), a segunda
  exige impersonar titular real (o Trabalho A obriga identidade sintetica), a
  terceira e propriedade do processo. Um check de "existe rota" duplicaria
  P-10 com nome novo, e o laudo exibiria dois verdes pela mesma evidencia.

  EFEITO DOWNSTREAM DE REVOGACAO (Art. 18 IX). Real e grave, e por construcao
  nao observavel a partir do alvo: exigiria enumerar e acessar sistemas a
  jusante que nao sao o alvo declarado — exatamente o que o contrato do
  Trabalho A proibe. A metade verificavel JA tem dono: P-19 (crypto-shredding
  no log append-only) e P-07 (revogacao existe, retencao pos-revogacao
  declarada). Sobre o efeito distribuido a suite nao afirma nada.

Cada um traz o ARTEFATO QUE FALTA para nascer. Um buraco que sabe o que
precisa para fechar nao e o mesmo que um buraco.

A DOC OBRIGATORIA SEGUROU A RODADA
----------------------------------
A trava da v0.18.0 fez o trabalho dela sem que ninguem pedisse: o check novo
so entrou depois de `docs/TESTES.md` e `docs/INDICE-DE-TESTES.md` serem
regenerados, e a trava de check-orfao exigiu que S-22 tivesse teste proprio
antes de o merge abrir. A secao de lacunas ganhou um item novo que LE a
tabela de `BURACOS-ASSUMIDOS.md` — fechado um buraco, ele some dos dois
documentos no mesmo commit.

Uma mordida da propria trava tambem foi corrigida: ela afirmava `**58**
checks` com numero digitado, e teria quebrado a cada check novo. O teste que
cobra a doc de nao envelhecer nao pode ser o primeiro a envelhecer — passou a
derivar de `len(catalogo.CATALOGO) + 1`.
```

## Pendencias de ratificacao

Nenhuma nova. As seis abertas seguem em `docs/RATIFICACOES.md`.

## Validacao

- `python -m pytest -q` → **730 passaram, 8 puladas** (era 713 + 8)
- clone limpo → verde
- `pse --manifesto` → autoprova OK, 58 mutacoes, 0 falhas
- `catalog_hash` mudou: o catalogo ganhou S-22 e `pse/data/` ganhou
  `legal-basis.yaml`. Mudanca de regua declarada, como manda o Gap 3.
