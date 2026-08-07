// D-08: cifra de aplicacao aplicada ao campo, e regiao dentro da residencia.
use aes_gcm::Aes256Gcm;
use aws_config::Region;
use sqlx::PgPool;

pub struct Titular {
    pub id: i64,
    pub cpf: String,
}

pub async fn conectar() -> PgPool {
    // Residencia declarada BR, e a regiao e brasileira: nada a dizer.
    let _regiao = Region::new("sa-east-1");
    PgPool::connect("postgres://db.sa-east-1.rds.amazonaws.com/app")
        .await
        .expect("conexao")
}

fn cifrar(cpf: &str) -> Vec<u8> {
    let chave = chave_do_kms();
    Aes256Gcm::encrypt(&chave, cpf.as_bytes())
}

fn chave_do_kms() -> Vec<u8> {
    // Chave gerenciada fora da aplicacao, como o catalogo declara.
    aws_sdk_kms::decrypt_data_key()
}

pub async fn gravar(pool: &PgPool, t: &Titular) {
    let cpf_cifrado = cifrar(&t.cpf);
    sqlx::query("INSERT INTO titulares (id, cpf) VALUES ($1, $2)")
        .bind(t.id)
        .bind(&cpf_cifrado)
        .execute(pool)
        .await
        .unwrap();
}
