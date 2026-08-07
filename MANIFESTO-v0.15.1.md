# Manifesto de release — pse-suite v0.15.1

> Gerado por `pse --manifesto`. Tag anotada `v0.15.1` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.15.0` são tags de obra.

```
pse-suite v0.15.1 — duas superficies, e o laudo so falava de uma

Manifesto de release
--------------------
suite_version   : 0.15.1
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos   (NENHUM check novo)

Autoprova
---------
resultado       : OK
mutacoes        : 57 declaradas, 0 falhas

A LACUNA QUE O DONO CONFIRMOU
-----------------------------
O btv serve DUAS SPAs na mesma origem — o produto (`btv-web/`) na raiz e um
console de desenvolvedor (`web/`) em `/dev`. Confirmado no
`infra/docker/Dockerfile` (dois estagios de build, `BTV_WEB_DIR` e
`BTV_DEV_WEB_DIR`) e em `crates/btv-server/src/lib.rs`
(`router.nest_service("/dev", svc)`).

Todas as medicoes dinamicas carregaram a RAIZ. O console nunca foi
observado, e o laudo NAO REGISTRAVA esse silencio: os sete checks dinamicos
afirmavam algo sobre uma superficie e nada sobre a outra, sem distinguir as
duas. E o mesmo verde falso que o bloco `alcance` impede no estatico, uma
camada acima.

  CORRECAO 1 — NOMEAR A AUSENCIA. `observacao_de_rede` ganhou
  `superficie_observada` e uma nota dizendo, em toda execucao, que nenhuma
  outra rota da mesma origem foi carregada e como cobri-la.

  CORRECAO 2 — MEDIR A OUTRA. As duas superficies foram observadas.

                      raiz (btv-web)              console (web)
  requisicoes         119                         93
  hosts               127.0.0.1,                  127.0.0.1
                      fonts.googleapis.com
  cookies             nenhum                      nenhum
  S-19 cabecalhos     ALTO                        ALTO
  S-21 sourcemap      MEDIO (107)                 MEDIO (84)
  P-22 P-23 P-24
  S-17 S-20           sem achado                  sem achado
  S-18                pulado (sem manifesto)      pulado (sem manifesto)

O QUE A SEGUNDA MEDICAO EXPOS — CONTRA O QUE SE MEDIU
-------------------------------------------------------
As duas superficies foram observadas em SERVIDOR DE DESENVOLVIMENTO (Vite),
nao no `btv dashboard` de producao. Isso muda o que os achados significam, e
o laudo nao dizia.

  S-21 — FALSO-POSITIVO PROVAVEL SOBRE O ARTEFATO. Os "bundles" sao
  `/@vite/client` (com `sourceMappingURL=data:...base64`), `/@react-refresh`
  e `node_modules/.vite/deps/*`. Nada disso e o que o `vite build` produz: e
  modo de desenvolvimento, que serve sem minificar e com sourcemap embutido
  POR DESIGN. O check nao errou — a referencia existe, e ele so afirma que
  existe. Errado era o laudo nao dizer contra o que mediu.

  S-19 — INCERTO. Dev server nao poe cabecalho de borda, entao o achado nao
  prova a postura de producao. PORÉM o servidor Rust tambem nao os define
  (procurados em `crates/btv-server/src/*.rs`, ausentes) e o compose delega
  ao ingress: o achado PODE valer em producao, e so observando o ingress se
  sabe.

  CORRECAO 3. `observacao_de_rede` passou a declarar
  `servidor_de_desenvolvimento` com os indicios que o denunciaram, em regua
  (`marcas_de_dev_server` em `pse/data/servido-ao-cliente.yaml`), com nota
  dizendo que o comportamento e normal do modo e nao propriedade do artefato
  publicado. NENHUM VEREDITO MUDOU — mudou o que o leitor entende dele.

O ESTATICO JA COBRIA AS DUAS ARVORES, E `web/` E A MAIOR
----------------------------------------------------------
Verificado por arquivo, nao por impressao:

  web/       104 analisados,  2 ilegiveis
  btv-web/    61 analisados,  1 ilegivel

A segunda arvore nunca ficou de fora. E os tres arquivos ilegiveis sao
CODIGO EMBARCADO E SERVIDO nas duas SPAs, nao sobra — o que confirma a
prioridade da gramatica, ja registrada na v0.15.0 e nao duplicada aqui.

LIMITE DESTA MEDICAO, DECLARADO
--------------------------------
O console foi servido em PORTA PROPRIA (Vite em 127.0.0.1:5179), nao
aninhado em `/dev` atras do servidor Rust. Origem separada em vez de origem
compartilhada: cookie, `SameSite` e cabecalho podem diferir do arranjo real.
Medir o arranjo de producao exigiria subir a imagem Docker com as duas
`dist` buildadas — PENDENCIA REGISTRADA, nao presumida limpa.

A LINHA QUE A SUITE NAO CRUZA
------------------------------
O `docker-compose.prod.yml` declara que autenticacao e responsabilidade do
ingress, e o console fica na mesma origem do produto. Isso esta registrado
como FATO OBSERVADO. Se e exposicao, e VEREDITO DO DONO — a PSE observa
carga, cabecalho e cookie; nao conclui risco.

O btv NAO FOI ALTERADO.

IMPACTO NO CONSUMIDOR
---------------------
  * `observacao_de_rede` ganha `superficie_observada`, `nota_de_superficie`
    e `servidor_de_desenvolvimento` (+ indicios e nota quando verdadeiro).
    Campos novos; nenhum existente mudou de forma ou de valor.
  * Consumidor que roda a camada dinamica contra `vite dev`/`next dev` passa
    a ver a qualificacao no laudo. Nenhum achado some, nenhuma severidade
    muda.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma. IDs INTACTOS.
Catalogo 57/57 — nenhum check novo.

VALIDACAO
---------
  * 644 passed com navegador real; clone limpo verde.
  * As duas SPAs medidas ao vivo, cada uma com seu laudo.
  * 10 testes novos, entre eles a mordida que impede "tudo virar dev server"
    e a trava que reprova qualquer check que monte `observacao_de_rede` a
    mao em vez de usar o relator qualificado.

PENDENCIAS DE RATIFICACAO
-------------------------
  1. Medir `/dev` no arranjo real (imagem Docker, origem compartilhada).
  2. A gramatica dos 3 arquivos servidos — prioridade confirmada.
  3. Achado emitido junto com indeterminacao, de v0.15.0.
  4. O embrulho de cifra opaco -> exit 20, de v0.14.2.
  5. A regra `env!` -> exit 20, de v0.14.0.
  6. A severidade assimetrica em Rust, de v0.14.0.
  7. Identidade dos SHAs do cockpit, de v0.13.0.
  8. `local_target`, de v0.13.0.
  9. P-24 em `privacy`, de v0.12.0.
 10. S-14 e S-15 como candidatos a CRITICO, de v0.9.0.
```
