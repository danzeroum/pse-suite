"""Motor de navegador da PSE — a camada dinamica do Trabalho A.

Adaptado de danzeroum/qa-suite (webqa/navegador.py, webqa/trackers.py,
webqa/gates.py e as fixtures de conftest.py), do mesmo dono, sob MIT.

O QUE FOI PRESERVADO, porque foram decisoes que as revisoes da qa-suite
custaram a fixar e que seria tolice redescobrir:

  * Playwright OPCIONAL. Quem so quer o inventario estatico nao carrega um
    navegador junto.
  * Engine desconhecida e ERRO FAIL-CLOSED, nunca filtro silencioso. Um
    typo que degenerasse em "rodou zero engines e passou" seria a pior
    forma de verde falso.
  * NetworkLog IMUTAVEL. Dois checks que compartilham a observacao nao
    podem interferir um no outro.
  * Contexto VIRGEM a cada observacao. Cookie ou consentimento herdado
    faria o alvo parecer conforme — o pior falso negativo possivel numa
    bateria de consentimento previo.
  * Ausencia vira SKIP HONESTO com instrucao, nunca aprovacao silenciosa.

O QUE MUDOU NA ADAPTACAO, e por que:

  * A lista de rastreadores saiu do modulo Python e foi para
    `pse/data/rastreadores.yaml`. Na PSE toda regua curada mora em data/ e
    entra no `catalog_hash` (D-13): a cobertura de um check tem de ser
    audivel a partir do laudo, nao so lendo o codigo.
  * A autorizacao NAO e um gate por variavel de ambiente. A PSE ja tem o
    contrato de Trabalho A ratificado — modo, atestacao humana com prazo,
    `target_fingerprint`, healthcheck — e este motor entra DEPOIS dos cinco
    degraus, pela mesma porta unica (`trabalho_a.base.exigir_alvo`). Dois
    sistemas de autorizacao no mesmo processo seriam duas respostas
    possiveis para a mesma pergunta.
  * A observacao e memorizada no Contexto, nao numa fixture de sessao do
    pytest: os checks da PSE rodam dentro de `executar()`, nao sob pytest,
    no repositorio do consumidor.
"""
from pse.navegador.engines import ENGINES_PADRAO, ENV_ENGINES, engines_configurados
from pse.navegador.rede import (CookieObservado, NetworkLog, RequisicaoObservada,
                                RecursoObservado, host_casa, host_de)

__all__ = ["ENGINES_PADRAO", "ENV_ENGINES", "engines_configurados",
           "CookieObservado", "NetworkLog", "RequisicaoObservada",
           "RecursoObservado", "host_casa", "host_de"]
