// P-19 — evento com PII num registro append-only, sem crypto-shredding.
//
// Nao ha nenhuma rotina de destruicao de chave neste repositorio: quando o
// pedido de eliminacao chegar, o CPF continua em todo replay do topico.
use rdkafka::producer::{FutureProducer, FutureRecord};

pub async fn publicar(producer: &FutureProducer, cpf: &str, email: &str) {
    let payload = format!("{{\"cpf\":\"{}\",\"email\":\"{}\"}}", cpf, email);
    producer
        .send(
            FutureRecord::to("titulares").payload(&payload).key("k"),
            std::time::Duration::from_secs(0),
        )
        .await
        .unwrap();
}
