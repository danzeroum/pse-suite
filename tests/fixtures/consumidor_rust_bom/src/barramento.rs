// As formas que o btv REAL revelou como falso-positivo do grep ancorado.
//
// Nenhuma delas e escrita em registro append-only, e todas estavam sendo
// consideradas candidatas por P-19 antes da triagem. Ficam aqui como caso
// permanente: a licao de um alvo real vale para todo Rust futuro, nao so
// para o btv.
//
// O arquivo menciona `ledger` de proposito — era exatamente essa mencao,
// num dominio que TEM ledger, que tornava elegivel todo `send` do modulo.
use crate::ledger::LedgerEntry;

pub enum UiCommand {
    Send(String),
}

/// (1) DEFINICAO de funcao, nao chamada. A lista de parametros nao e um span
///     de argumento — e um check que a varresse acusaria a propria
///     assinatura, um achado que nao tem como ser corrigido.
pub fn append(&mut self, kind: &str, cpf: &str, email: &str) -> anyhow::Result<()> {
    let _ = (kind, cpf, email);
    Ok(())
}

pub fn publish(cpf: &str) {
    let _ = cpf;
}

pub async fn fluxos(tx: tokio::sync::mpsc::Sender<String>, cpf: &str) {
    // (2) canal tokio: `send` num `tx` nao e escrita em barramento.
    let _ = tx.send(cpf.to_string()).await;

    // (3) canal com nome idiomatico sufixado — o casamento por token exato
    //     nao alcancava o sufixo, e oito destes sobreviveram ao primeiro
    //     refino no btv.
    let (agent_evt_tx, _rx) = tokio::sync::mpsc::channel::<String>(8);
    let _ = agent_evt_tx.send(cpf.to_string()).await;

    // (4) requisicao HTTP do reqwest: `builder.send()` nao publica evento.
    let builder = reqwest::Client::new().post("https://exemplo.test").body(cpf.to_string());
    let _ = builder.send().await;

    // (5) construcao de VARIANTE de enum, nao chamada de metodo. Em Rust
    //     idiomatico metodo e snake_case e variante e CamelCase.
    let _cmd = UiCommand::Send(cpf.to_string());

    // (6) oneshot responder: responde uma pergunta, nao grava historico.
    let (responder, _) = tokio::sync::oneshot::channel::<bool>();
    let _ = responder.send(true);

    let _ = LedgerEntry::default();
}
