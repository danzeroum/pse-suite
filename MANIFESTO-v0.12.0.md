# Manifesto de release — pse-suite v0.12.0

> Gerado por `pse --manifesto`. Tag anotada `v0.12.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.11.0` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.12.0 — camada dinamica Fase 2: o corpo servido

Manifesto de release
--------------------
suite_version   : 0.12.0
commit          : 95667ec5bca8b2df1841f58357245610fbeb5a4f
catalog_hash    : 675759e1b4e2c9c5240b78daa1f2e972e212992ba2371a7d41168430df47cb1b
schema_version  : laudo-pse-1.0
checks          : 57 implementados, 0 previstos
por dominio     : {'frontend': 11, 'api': 15, 'backend': 16, 'data': 15, 'ai': 15}

Autoprova
---------
resultado       : OK
mutacoes        : 57 declaradas, 0 falhas

RATIFICACOES DA FASE 1 — CONFIRMADAS E MANTIDAS
-----------------------------------------------
  * P-22 em ALTO. Nome de host ou de cookie nao prova finalidade: sinal
    forte, nao prova cabal. Mantido, e o achado continua dizendo por que.
  * Playwright OPCIONAL com skip honesto. Mantido — e o skip agora NOMEIA
    se faltou o pacote ou o binario.
  * Sanitizacao do NetworkLog na ORIGEM. Mantida, e estendida: o corpo
    capturado nesta fase nunca entra no laudo, so o rotulo do que se achou.
  * Atribuicao RECOMENDADA e nao obrigatoria. Mantida arquivo a arquivo
    onde ajuda a procedencia — os modulos de motor e os checks portados a
    declaram; os que so consomem a regua, nao.

O QUE MUDA vs 0.11.0 — FASE 2, TODOS PASSIVOS
----------------------------------------------
  S-18 ALTO     Terceiro contactado fora do manifesto. Par dinamico de
                S-04. Inventario completo no laudo mesmo sem achado.
  S-19 ALTO     CSP / nosniff / Referrer-Policy no documento, e mixed
                content. Asset de terceiro pelado e OBSERVACAO.
  S-20 CRITICO  Credencial servida ao cliente. Par dinamico de P-06.
  P-24 ALTO     EXIF-GPS em imagem publicada. So a presenca.
  S-21 MEDIO    Sourcemap referenciado. O `.map` NAO e baixado.

MOTOR ESTENDIDO
`RecursoObservado` ganhou cabecalhos e corpo. A captura acontece DURANTE a
observacao (na qa-suite e sob demanda, porque la o contexto do navegador
fica vivo; aqui ele ja fechou quando os checks rodam). Seletiva e com teto:
512 KB por recurso, 8 MB no conjunto. `motivo_nao_lido` preenchido significa
NAO AVALIADO — e S-20 fica INDETERMINADO se nenhum candidato pode ser lido.

DIVERGENCIA DECLARADA — P-24 EM `privacy`, NAO EM `security`
A tarefa agrupou "metadados/GPS em imagem, sourcemap em producao" sob
`security`. Separei em dois checks e pus P-24 em `privacy`, aplicando a
regra do proprio projeto: o pilar responde QUE VALOR esta em jogo.
Coordenada numa foto publicada e localizacao de pessoa (Art. 5o I);
sourcemap e codigo-fonte, e ficou em S-21, no pilar de seguranca.
Se a leitura estiver errada, o conserto e um campo `pack` no catalogo.

CORRELACAO — DOIS PARES NOVOS
  S-04 x S-18  o terceiro escrito vs o terceiro contactado
  P-06 x S-20  a chave no repositorio vs a chave PUBLICADA
No segundo, o cenario `so_na_camada_dinamica` muda ate a urgencia da
correcao — e por isso deduplicar seria perda de informacao, nao economia.

REGUA NOVA COM TRES GUARDAS
`pse/data/servido-ao-cliente.yaml`. Alem do piso de sempre:
  * cada regex de segredo tem de CASAR O PROPRIO EXEMPLO. Padrao quebrado e
    ignorado por `_compilar` para nao derrubar a varredura inteira — o que
    significa que um typo cegaria o formato em SILENCIO.
  * prosa inocente (`Authorization: required`, `getCsrfToken()`) NAO pode
    virar CRITICO. Falso positivo em bateria regulatoria custa a
    credibilidade da bateria inteira.

O QUE CONTINUA FORA — FASE 3, ATRAS DO GATE ATIVO
Clicar banner, submeter formulario, exercer direito de titular, baixar o
`.map`, pedir arquivo nao linkado. Tudo escreve ou sonda o sistema do alvo.
Na duvida entre passivo e ativo, ativo.

IMPACTO NO CONSUMIDOR
  * `pip install pse-suite` segue LEVE. O estatico nao mudou.
  * Cinco checks novos, um deles CRITICO (S-20): repositorio com camada
    dinamica habilitada pode passar de 11 para 10.
  * Playwright ausente / sem atestacao / alvo fora do ar -> indeterminados,
    exit 20. NUNCA verde.
Exit codes INTACTOS. Schema laudo-pse-1.0 sem mudanca de forma. IDs
INTACTOS.

VALIDACAO
  * 505 passed com navegador real contra o alvo de fixture, que agora serve
    JS com credencial, JPEG com EXIF-GPS, sourcemap e cabecalhos.
  * Teste provando que a credencial plantada NAO sai no laudo, e que a
    coordenada nunca e lida.
  * Clone limpo, com e sem o extra `browser`.

PENDENCIAS DE RATIFICACAO
  1. P-24 em `privacy` (divergencia declarada acima).
  2. A excecao de loopback em `validar_config`, de v0.11.0.
  3. S-14 e S-15 como candidatos a CRITICO, de v0.9.0.
```
