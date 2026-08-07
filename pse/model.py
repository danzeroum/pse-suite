from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional


class Severidade(str, Enum):
    CRITICO = "CRITICO"   # violacao legal ou risco grave — fail-closed
    ALTO = "ALTO"         # gap significativo — bloqueia merge em main
    MEDIO = "MEDIO"       # boa pratica ausente — entra no laudo sem bloquear
    BAIXO = "BAIXO"
    INFO = "INFO"


class Veredito(str, Enum):
    """Estado do processo, nao do check. Nunca binario: 'nao olhei' jamais
    compartilha codigo de saida com 'conforme'."""
    CONFORME = "conforme"
    VIOLACAO = "violacao"
    INDETERMINADO = "indeterminado"
    ENTRADA_INVALIDA = "entrada_invalida"


# Mapa de saida ratificado (Etapa 3 §2.2).
# Precedencia quando coexistem: 30 > 10 > 20 > 11 > 0.
EXIT_CONFORME = 0
EXIT_VIOLACAO_CRITICA = 10
EXIT_VIOLACAO_ALTA = 11
EXIT_INDETERMINADO = 20
EXIT_ENTRADA_INVALIDA = 30


class SkipCheck(Exception):
    """N/A DECLARADO — a pre-condicao declarativa nao existe.

    Ex.: sem manifesto de terceiros nao ha o que conferir em S-08; alvo sem
    decisao automatizada tira o pack de etica de escopo. Nao bloqueia, mas o
    motivo e obrigatorio e SEMPRE aparece no laudo (checks_pulados) — um check
    pulado nunca e indistinguivel de um check verde.
    """


class CheckIndeterminado(Exception):
    """TENTEI E NAO CONSEGUI DECIDIR — bloqueia igual a uma violacao.

    Distinto de SkipCheck: aqui a pre-condicao existia e a analise falhou —
    fato nao decidivel estaticamente, arquivo ilegivel, excecao inesperada,
    ou (Fase 2) alvo indisponivel. Vai para checks_indeterminados e leva o
    processo a exit 20. Indeterminacao nunca degrada para verde.

    `achados` CARREGA O QUE JA FOI DECIDIDO ANTES DE BLOQUEAR, e existe por
    um defeito que o btv expos: um unico `.ts` que nenhuma gramatica alcanca
    derrubava P-13, P-14 e S-09 INTEIROS, e os 171 arquivos que parsearam
    sem problema nenhum ficavam sem veredito. O gate funcionava — exit 20 —
    e a informacao se perdia: uma violacao real nos outros 171 nunca seria
    reportada.

    Bloquear e emitir nao sao opostos. O veredito continua indeterminado (o
    check NAO viu tudo), e o que ele viu vai junto. Perder achado por causa
    de fail-closed e o pior dos dois mundos: nem verde honesto, nem
    informacao.
    """

    def __init__(self, mensagem, achados=None):
        super().__init__(mensagem)
        self.achados = list(achados or [])


class NaoHabilitado(Exception):
    """Check existe e nao foi habilitado nesta execucao.

    Distinto dos outros tres: nao ha pre-condicao faltando (SkipCheck) nem
    tentativa frustrada (CheckIndeterminado) — o consumidor simplesmente nao
    pediu o Trabalho A, ou pediu num modo que nao inclui este check. Nao
    bloqueia, e aparece no laudo em checks_nao_habilitados com o motivo:
    omissao declarada continua sendo declarada.
    """


class VersaoIrresolvivel(Exception):
    """A suite nao consegue dizer que versao e. Ambiente quebrado -> exit 30.

    Nunca se inventa uma string plausivel: um laudo que mente sobre a propria
    procedencia e pior que laudo nenhum.
    """


class EntradaInvalida(Exception):
    """Path inexistente, config/catalogo ilegivel, packs invalidos -> exit 30."""


@dataclass
class Finding:
    check_id: str
    pack: str
    severidade: Severidade
    titulo: str
    descricao: str
    recomendacao: str
    base_legal: Optional[str] = None
    arquivo: Optional[str] = None
    linha: Optional[int] = None
    snippet: Optional[str] = None
    # Trabalho A: requisicao/resposta que provam o achado. Sanitizado aqui,
    # na origem — nunca so na serializacao.
    trace: Optional[dict] = None

    def __post_init__(self):
        """O literal nao sobrevive ao check que o encontrou (D-02).

        `evidence.montar_laudo` continua sendo o choke point da serializacao,
        mas sanitizar so ali deixava o segredo vivo no objeto em memoria — e
        qualquer outro consumidor de `executar()` (um gravador de trace do
        Trabalho A, por exemplo) o receberia em claro. A autoprova embarcada
        detectou exatamente isso. O mascaramento e idempotente, entao aplicar
        aqui e no laudo nao degrada o texto duas vezes.
        """
        from pse.sanitize import sanitizar, sanitizar_profundo
        if self.snippet:
            self.snippet = sanitizar(self.snippet)
        if self.trace:
            self.trace = sanitizar_profundo(self.trace)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severidade"] = self.severidade.value
        return d
