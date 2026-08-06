from dataclasses import dataclass, asdict
from enum import Enum
from typing import Optional


class Severidade(str, Enum):
    CRITICO = "CRITICO"   # violacao legal ou risco grave — fail-closed
    ALTO = "ALTO"         # gap significativo — bloqueia merge em main
    MEDIO = "MEDIO"       # boa pratica ausente — entra no laudo sem bloquear
    BAIXO = "BAIXO"
    INFO = "INFO"


class SkipCheck(Exception):
    """Check nao aplicavel. O motivo e obrigatorio e SEMPRE aparece no laudo
    (checks_pulados) — um check pulado nunca e indistinguivel de um check verde."""


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

    def to_dict(self) -> dict:
        d = asdict(self)
        d["severidade"] = self.severidade.value
        return d
