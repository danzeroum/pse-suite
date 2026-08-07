"""D-01 do conserto — `.tsx` e `.jsx` saem da invisibilidade.

O reconhecimento mediu o buraco: `.ts` era auditado por P-01, P-06, S-04,
S-06 e E-04; `.tsx` e `.jsx` não estavam em conjunto de extensão **nenhum**.
**281 arquivos React** nos 6 alvos, e um `console.log(user.cpf)` num
componente simplesmente não existia para a suíte inteira.

Silêncio que parece verde é o pior defeito que um laudo pode ter — e este era
da própria suíte. O consumidor lia "nenhum achado em P-01" e concluía que os
componentes estavam limpos; a verdade é que ninguém os abriu.

A CORREÇÃO NÃO INVENTA PARSER DE JSX. É a mesma heurística de linha que `.ts`
já recebia, com a mesma severidade rebaixada (ALTO, não CRÍTICO) e pelo mesmo
motivo declarado em P-01: sem AST para a linguagem, a suíte não consegue
provar que não houve mascaramento.

A CAUSA RAIZ ERA CÓPIA. A lista vivia duplicada em cinco conjuntos, e ninguém
lembra de editar cinco listas iguais. `scan.ECMASCRIPT` existe para que a
próxima extensão entre em um lugar só.
"""
import pytest

from pse.checks.ethics import e04_hitl
from pse.checks.privacy import p01_pii_em_logs, p06_chave_segregada
from pse.checks.security import s04_manifesto_terceiros
from pse.engine import scan
from pse.engine.runner import executar

CFG = {"catalog_path": "catalog.yaml"}


def rodar(caminho):
    return executar(caminho, {"privacy", "security", "ethics"}, CFG)


def escrever(base, arquivos):
    for nome, corpo in arquivos.items():
        alvo = base / nome
        alvo.parent.mkdir(parents=True, exist_ok=True)
        alvo.write_text(corpo, encoding="utf-8")
    return rodar(base)


def de(res, cid):
    return [f for f in res["findings"] if f.check_id == cid]


# ==================================================== o buraco que existia
@pytest.mark.pse_privacy
def test_componente_tsx_com_pii_em_log_agora_dispara(tmp_path):
    """Antes deste conserto: invisível. Não "sem achado" — sem leitura."""
    res = escrever(tmp_path, {
        "src/Perfil.tsx":
            'export function Perfil({ user }) {\n'
            '  console.log("perfil", user.cpf);\n'
            '  return <div>{user.nome}</div>;\n'
            '}\n'})
    achados = de(res, "P-01")
    assert achados, "componente .tsx continua invisível para P-01"
    assert achados[0].arquivo.endswith("Perfil.tsx")


@pytest.mark.pse_privacy
def test_componente_jsx_com_pii_em_log_agora_dispara(tmp_path):
    res = escrever(tmp_path, {
        "src/Cadastro.jsx":
            'export function Cadastro({ user }) {\n'
            '  console.error("falha", user.email);\n'
            '}\n'})
    assert de(res, "P-01"), "componente .jsx continua invisível para P-01"


@pytest.mark.pse_security
def test_credencial_em_tsx_agora_dispara(tmp_path):
    res = escrever(tmp_path, {
        "src/api.tsx": 'const api_key = "Kp7xR2mQvLt9Wz4Ny6Bd";\n'})
    assert de(res, "S-06"), "credencial em .tsx continua invisível"


@pytest.mark.pse_security
def test_host_de_terceiro_em_tsx_agora_dispara(tmp_path):
    res = escrever(tmp_path, {
        "src/Analytics.tsx":
            'fetch("https://analytics.google.com/collect");\n'})
    achados = de(res, "S-04")
    assert any("analytics.google.com" in f.titulo for f in achados)


# ================================= a severidade é a mesma que `.ts` já tinha
@pytest.mark.pse_privacy
def test_tsx_herda_a_severidade_rebaixada_de_ts(tmp_path):
    """Não é parser de JSX: é a heurística de linha, com a mesma ressalva
    declarada. Emitir CRÍTICO aqui repetiria em `.tsx` o falso-positivo que
    P-01 já corrigiu em Python."""
    corpo = 'console.log("u", user.cpf);\n'
    res_ts = escrever(tmp_path / "a", {"src/x.ts": corpo})
    res_tsx = escrever(tmp_path / "b", {"src/x.tsx": corpo})
    assert de(res_ts, "P-01") and de(res_tsx, "P-01")
    assert (de(res_ts, "P-01")[0].severidade
            == de(res_tsx, "P-01")[0].severidade == "ALTO")


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_mascaramento_em_tsx_nao_e_punido(tmp_path):
    """D-08 acompanha o alcance novo. Ampliar cobertura sem levar a supressão
    do caso correto junto seria trocar um buraco por um falso-positivo."""
    res = escrever(tmp_path, {
        "src/Perfil.tsx": 'console.log("perfil", mascarar(user.cpf));\n'})
    assert not de(res, "P-01"), "o mascaramento correto virou achado em .tsx"


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_comentario_em_tsx_nao_vira_achado(tmp_path):
    """D-01 acompanha o alcance novo: `.tsx` entrou também nos mapas de
    comentário de `scan`, senão a extensão traria de volta o defeito de
    1eb616b numa linguagem nova."""
    res = escrever(tmp_path, {
        "src/Perfil.tsx":
            '// console.log(user.cpf) — removido na review\n'
            'export const Perfil = () => null;\n'})
    assert not de(res, "P-01"), "comentário em .tsx virou achado"


@pytest.mark.pse_privacy
@pytest.mark.mordida
def test_comentario_de_bloco_em_tsx_nao_vira_achado(tmp_path):
    res = escrever(tmp_path, {
        "src/Perfil.tsx":
            '/* console.log(user.cpf) */\n'
            'export const Perfil = () => null;\n'})
    assert not de(res, "P-01")


# ================================================ a causa raiz era a cópia
def test_a_familia_ecmascript_vive_num_lugar_so():
    """Cinco listas iguais foi como `.tsx` ficou de fora de todas. A próxima
    extensão tem de entrar em um lugar e alcançar os cinco checks."""
    assert {".js", ".jsx", ".ts", ".tsx"} <= scan.ECMASCRIPT
    for conjunto in (p01_pii_em_logs.OUTRAS, e04_hitl.OUTRAS,
                     s04_manifesto_terceiros.EXTS):
        assert scan.ECMASCRIPT <= conjunto, sorted(scan.ECMASCRIPT - conjunto)


def test_todo_check_que_le_js_tambem_le_jsx_e_tsx(tmp_path):
    """A trava contra a regressão: um check novo que copie a lista antiga em
    vez de usar `scan.ECMASCRIPT` reprova aqui."""
    import ast
    from pathlib import Path
    raiz = Path(__file__).resolve().parent.parent / "pse"
    ofensores = []
    for p in sorted(raiz.rglob("*.py")):
        arvore = ast.parse(p.read_text(encoding="utf-8"))
        for no in ast.walk(arvore):
            if not isinstance(no, ast.Set):
                continue
            literais = {e.value for e in no.elts
                        if isinstance(e, ast.Constant) and isinstance(e.value, str)}
            if ".js" in literais and not {".jsx", ".tsx"} <= literais:
                ofensores.append(f"{p.name}:{no.lineno}")
    assert not ofensores, (
        f"conjunto de extensão com `.js` e sem `.jsx`/`.tsx` em {ofensores} — "
        f"use `scan.ECMASCRIPT` em vez de copiar a lista")


def test_scan_apaga_comentario_das_extensoes_novas():
    """Se `.tsx` entrasse nos checks e não nos mapas de comentário de `scan`,
    o alcance novo nasceria com o defeito que D-01 existe para impedir."""
    for ext in (".jsx", ".tsx"):
        assert ext in scan._CMT_LINHA, ext
        assert ext in scan._CMT_BLOCO, ext
        efetivo = scan.codigo_efetivo("// senha = 'x'\nconst a = 1;\n", ext)
        assert "senha" not in efetivo
