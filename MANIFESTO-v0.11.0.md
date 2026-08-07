# Manifesto de release — pse-suite v0.11.0

> Gerado por `pse --manifesto`. Tag anotada `v0.11.0` local.

> `v0.2.0` e `v0.3.0` estão publicadas. `v0.4.0`–`v0.10.0` são tags de obra:
> nenhuma chegou a consumidor. **Quando o consumo real começar, publicar só
> a mais recente.**

```
pse-suite v0.11.0 — a camada dinamica: motor de navegador proprio

Manifesto de release
--------------------
suite_version   : 0.11.0
commit          : db3770095a5ed4d72610ef6e0e240a84d62a88a9
catalog_hash    : cd2893421347c7884f2f68a342446958c283f9addeb16b104ecaabc7c35c9b25
schema_version  : laudo-pse-1.0
checks          : 52 implementados, 0 previstos
por dominio     : {'frontend': 6, 'api': 15, 'backend': 16, 'data': 15, 'ai': 15}

Autoprova
---------
resultado       : OK
mutacoes        : 52 declaradas, 0 falhas

O QUE MUDA vs 0.10.0 — FASE 1 DA CAMADA DINAMICA (Opcao 1)
-----------------------------------------------------------
A PSE ganha MOTOR DE NAVEGADOR PROPRIO. Trabalho A e B no MESMO laudo, com
procedencia comum — que e a razao de ser da Opcao 1. A harness do
`project` orquestra a PSE igual orquestra a qa-suite: muda so o pin.

MOTOR (pse/navegador/), adaptado de danzeroum/qa-suite (MIT, mesmo dono).
Portado, nao reescrito — as decisoes que as revisoes da qa-suite custaram a
fixar vieram inteiras, e ha teste exigindo a nota de procedencia em cada
arquivo:

  engines.py  Playwright OPCIONAL; engine desconhecida e ERRO fail-closed.
  rede.py     NetworkLog IMUTAVEL; host casa por SUFIXO DE ROTULO.
  sessao.py   Contexto VIRGEM por observacao; espera POS-LOAD.

O QUE MUDOU NA ADAPTACAO
  * A lista de rastreadores saiu do .py para pse/data/rastreadores.yaml —
    na PSE toda regua curada entra no `catalog_hash` (D-13).
  * A autorizacao NAO virou gate por variavel de ambiente. O contrato de
    Trabalho A ja existe e o motor entra DEPOIS dos cinco degraus, por
    `exigir_observacao`. Dois sistemas de autorizacao no mesmo processo
    seriam duas respostas possiveis para a mesma pergunta.

OS TRES FUNDADORES (todos PASSIVOS, dominio `frontend`)
  P-22 ALTO  Rastreador ou cookie nao essencial antes de qualquer aceite.
  S-17 ALTO  Cookie de sessao sem HttpOnly/Secure/SameSite.
  P-23 ALTO  PII na query, no form GET e no Referer.

Clicar banner e submeter formulario ESCREVEM no sistema do alvo e ficam
para a fase seguinte, atras do gate ativo. Na duvida, ativo.

P-22 e ALTO e nao CRITICO de proposito, e o achado diz por que: o nome do
host nao prova a finalidade do tratamento. Sinal forte, nao prova cabal.

CORRELACAO ESTATICO x DINAMICO
Bloco `correlacoes` novo no laudo, ligando P-14 x P-23 e S-09 x S-17 em
tres cenarios: confirmado nas duas camadas, so no codigo, ou SO NO AR. O
terceiro e o mais interessante — veio de template do servidor ou tag
gerenciada, e nenhuma leitura de repositorio o encontraria. Nenhum finding
e removido: e indice, nao filtro.

VAZAMENTO ENCONTRADO PELO PROPRIO TESTE
`test_p23_nao_publica_o_dado_que_denuncia` reprovou na primeira execucao.
`sanitizar_finding` preservava `arquivo` intacto por uma premissa escrita —
"e o endereco do achado, nao o seu conteudo". Verdade para `src/App.jsx`,
FALSA para `https://alvo/fatura?cpf=529...`, onde o endereco E o conteudo.
Nasceu `sanitizar_url` (mantem nome de parametro, apaga valor), e a
correlacao — que copiava `arquivo` cru — virou porta dos fundos e passou a
usar o mesmo sanitizador. O valor do cookie nem chega a existir no objeto
observado.

MUDANCA DE REGRA, DECLARADA E ESTREITA
`http://` passou a ser aceito em LOOPBACK (127.0.0.1, localhost, ::1). A
exigencia de https existe por um motivo escrito — sonda em texto claro vaza
o token na rede — e em loopback nao ha rede. Sem isso, a camada dinamica so
teria prova contra objeto fabricado, que e o mesmo erro de tratar working
tree como repositorio. Ha teste-mordida provando que
`http://127.0.0.1.atacante.com` segue recusado com exit 30.
**Sujeito a reversao: e mudanca num contrato ratificado.**

IMPACTO NO CONSUMIDOR
  * `pip install pse-suite` segue LEVE — so estatico, sem navegador.
  * `pip install 'pse-suite[browser]'` habilita a camada dinamica.
  * Playwright ausente -> os tres em `checks_indeterminados` com instrucao
    de instalar, exit 20. NUNCA verde.
  * Sem `target` declarado -> `checks_nao_habilitados`, nao bloqueia.
  * Sem atestacao valida -> indeterminados, exit 20, ZERO navegacoes.
  * `environment: production` -> exit 30.
Exit codes INTACTOS. Schema laudo-pse-1.0 ganha `correlacoes` (campo novo,
sem mudanca de forma nos existentes). IDs INTACTOS.

VALIDACAO
  * 464 passed com navegador real (chromium contra alvo de fixture local).
  * 458 passed + 6 skipped sem binario de navegador — o skip NOMEIA se
    faltou o pacote ou o binario.
  * Clone limpo + venv sem o extra `browser`: estatico exit 0, self-test
    exit 0, dinamicos exit 20 com a instrucao.

BURACO ASSUMIDO
`ethics x frontend` permanece a unica celula vazia — e agora com mais
sentido: o estrato ganhou camada dinamica, e dark pattern observavel
(recusar mais dificil que aceitar) e candidato natural para quando o gate
ATIVO existir. Segue exigindo julgamento humano.

PENDENCIAS DE RATIFICACAO
  1. A excecao de loopback em `validar_config` — mudanca num contrato
     ratificado, feita para nao deixar a camada dinamica sem prova real.
  2. Segue aberta a de v0.9.0: S-14 e S-15 como candidatos a CRITICO.
  3. `danzeroum/qa-suite` nao tem arquivo LICENSE no repositorio. A
     atribuicao MIT esta declarada nos arquivos portados conforme
     instruido, mas convem publicar o LICENSE la para a procedencia ficar
     verificavel por terceiros.
```
