// P-18 e S-16 em Rust.
//
// O catalogo promete cifra para `cpf`; este motor grava em claro.
// A politica declara residencia BR; este cliente conecta em us-east-1.
use aws_config::Region;
use sqlx::PgPool;

pub struct Titular {
    pub id: i64,
    pub cpf: String,
}

pub async fn conectar() -> PgPool {
    // S-16: regiao literal no span de argumento de uma chamada de conexao.
    let _regiao = Region::new("us-east-1");
    PgPool::connect("postgres://db.us-east-1.rds.amazonaws.com/app")
        .await
        .expect("conexao")
}

pub async fn gravar(pool: &PgPool, t: &Titular) {
    // P-18: o campo declarado cifrado no catalogo entra em claro.
    sqlx::query("INSERT INTO titulares (id, cpf) VALUES ($1, $2)")
        .bind(t.id)
        .bind(&t.cpf)
        .execute(pool)
        .await
        .unwrap();
}
