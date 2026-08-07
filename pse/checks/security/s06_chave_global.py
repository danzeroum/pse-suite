"""S-06 — credencial de parceiro hardcoded.

O vetor mais universal da suite: um literal de chave num `.rs` e exatamente
a mesma exposicao que num `.py`. `docs/cobertura-btv.md` mediu o preco de
nao alcanca-lo — 38 mil linhas de Rust no primeiro alvo real, e este check,
cuja razao de existir e achar chave em codigo, nunca olhou nenhuma delas.

O ALCANCE A RUST E TEXTUAL E ANCORADO, nao um parser. A ancora e a
ESTRUTURA da ligacao (`let`/`const`/`static` + `=` + literal), nunca a
mencao do nome: `// key = "AKIA..."` num comentario nao dispara, porque o
comentario e apagado antes de qualquer heuristica (D-01).

SEVERIDADE CONSERVADORA, e a assimetria e deliberada. Em Python o fato vem
da arvore; em Rust vem de texto, que e mais fragil. Entao CRITICO so quando
o literal casa com um FORMATO conhecido de credencial (AKIA, sk-, ghp_,
PEM) — ai nao ha ambiguidade que a fragilidade do texto possa introduzir.
Nome de credencial com literal longo mas de formato desconhecido e ALTO:
provavelmente e chave, e "provavelmente" nao merece o grau maximo.

D-08 em Rust: `std::env::var("API_KEY")` nao e literal e nem chega a ser
candidato. `let key = "changeme"` e placeholder, e punir o exemplo que o
time deixou de proposito seria o D-08 ao contrario.

SEVERIDADE POR CONTEXTO, sobre TUDO — Python, JS/TS e Rust. Depois das duas
assimetrias acima vem uma terceira pergunta, e ela e de outra natureza:
aquela credencial esta VIVA? `pse.checks._credencial` responde olhando o
caminho do arquivo e o proprio literal, e rebaixa para MEDIO o que for de
teste ou obviamente sintetico. Medido contra 6 alvos reais: 18 dos 19
CRITICOs de credencial da suite eram fixtures, e um deles era um token
propositalmente invalido num teste de rejeicao.

REBAIXA, NUNCA SUPRIME. O achado continua no laudo com o motivo escrito, e
para de dirigir o exit code. Ignorar `tests/` seria a trava que o vigiado
desliga movendo o segredo de arquivo.
"""
import re

from pse.checks import _credencial, _rust
from pse.engine import rustscan, scan
from pse.engine.registry import check
from pse.model import Finding, Severidade

PADRAO = (r"(\b(api_key|apikey|access_token)\s*=\s*[\"'][^\"']{12,}[\"']"
          r"|Authorization[\"']?\s*[:=].{0,10}(Bearer|Basic)\s+[A-Za-z0-9._\-]{16,})")

BASE = "LGPD Art. 46"
DESCRICAO = ("Credencial hardcoded: irrevogavel sem novo deploy e "
             "compartilhada por todo consumidor do codigo.")
RECOMENDACAO = ("Chave por parceiro em cofre, com TTL, rotacao e "
                "revogacao em 1 clique.")


def _formato_conhecido(ctx, valor: str) -> str | None:
    for padrao in _rust.r(ctx, "formatos_de_credencial"):
        if re.search(padrao, valor):
            return padrao
    return None


def _em_rust(ctx) -> list:
    """Ligacao com nome de credencial e literal que parece credencial.

    Tres condicoes, todas necessarias, e a conjuncao e o que separa isto de
    um grep: (1) a ESTRUTURA e uma ligacao, (2) o NOME casa com a regua de
    credencial, (3) o VALOR e literal, longo o bastante e nao e placeholder.
    Qualquer uma sozinha produziria falso-positivo num alvo real.
    """
    nomes = _rust.r(ctx, "nomes_de_credencial")
    minimo = int(ctx.data[_rust.REGUA]["tamanho_minimo_de_credencial"])
    findings = []

    for p, texto in _rust.arquivos(ctx):
        rel = scan.rel(ctx.repo, p)
        linhas = texto.splitlines()
        for lig in rustscan.ligacoes(texto):
            if not scan.nome_casa_tokens(lig.nome, nomes):
                continue
            # Ambiguidade estreita: valor de macro de compilacao. Antes de
            # olhar o literal, porque `env!` nem literal tem.
            _rust.recusar_se_ambiguo(
                ctx, "S-06", p, lig.linha, lig.valor_bruto,
                f"o valor da credencial `{lig.nome}`")
            if lig.literal is None:
                continue                     # veio de chamada: D-08
            if len(lig.literal) < minimo or _rust.e_placeholder(ctx, lig.literal):
                continue
            fonte = (linhas[lig.linha - 1] if lig.linha <= len(linhas) else "")
            formato = _formato_conhecido(ctx, lig.literal)
            bruta = Severidade.CRITICO if formato else Severidade.ALTO
            # O contexto decide POR CIMA da assimetria de formato: um `.rs`
            # sob `tests/` nao dirige o gate nem quando o literal casa com
            # AKIA. `rebaixar` so desce, e nunca abaixo de MEDIO.
            severidade = _credencial.rebaixar(ctx, rel, fonte, bruta)
            contexto = _credencial.motivo(ctx, rel, fonte)
            nota = ("O literal casa com um formato conhecido de credencial, "
                    "entao o casamento textual nao introduz ambiguidade aqui."
                    if formato else
                    "O nome e de credencial e o literal tem "
                    f"{len(lig.literal)} caracteres, mas nao casa com nenhum "
                    "formato conhecido. Severidade ALTO e nao CRITICO de "
                    "proposito: o alcance a Rust e textual, e texto sem "
                    "formato reconhecido nao merece o grau maximo.")
            findings.append(Finding(
                check_id="S-06", pack="security", severidade=severidade,
                titulo=f"Credencial em texto claro na ligacao `{lig.nome}` (Rust)",
                descricao=f"{DESCRICAO} {nota}"
                          + (" " + contexto if contexto else ""),
                recomendacao=(
                    f"{RECOMENDACAO} Em Rust, ler com `std::env::var` ou por um "
                    f"cliente de cofre (`aws_sdk_secretsmanager`, `vaultrs`) — "
                    f"nao com `env!`, que grava o valor no binario."),
                base_legal=BASE, arquivo=rel, linha=lig.linha,
                snippet=fonte.strip()[:80] or None))
    return findings


@check("S-06", "security", "Credencial de parceiro hardcoded", base_legal=BASE)
def chave_global(ctx):
    findings = []
    for p in scan.arquivos(ctx.repo, scan.ECMASCRIPT | {".py", ".go", ".java",
                                                       ".env", ".yaml", ".yml"}):
        rel = scan.rel(ctx.repo, p)
        for linha, snippet in scan.grep(p, PADRAO):
            sev = _credencial.severidade(ctx, rel, snippet)
            nota = _credencial.motivo(ctx, rel, snippet)
            findings.append(Finding(
                check_id="S-06", pack="security", severidade=sev,
                titulo="API key / token de parceiro em texto claro",
                descricao=DESCRICAO + (" " + nota if nota else ""),
                recomendacao=RECOMENDACAO, base_legal=BASE,
                arquivo=rel, linha=linha, snippet=snippet[:80]))
    return findings + _em_rust(ctx)
