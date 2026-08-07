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

// (7) DEFINICAO de funcao de conexao. `fn connect(...)` entrava como chamada
//     de persistencia em S-16, e a assinatura era varrida como se fosse um
//     span de argumento.
pub fn connect(regiao: &str) -> String {
    regiao.to_string()
}

// (8) LEITURA nao e persistencia. P-18 pergunta se o campo sensivel e
//     GRAVADO sem cifra; um SELECT nao grava nada. Dez dos dezessete sites
//     que a sonda levantou no btv eram leitura — acusa-los seria um achado
//     que o time nao consegue corrigir, porque nao ha escrita ali.
pub fn ler(conn: &Conn, id: i64) -> Option<(String, String)> {
    conn.query_row(
        "SELECT created_ts, cpf FROM titulares WHERE id = ?1",
        params![id],
        |r| Ok((r.get(0)?, r.get(1)?)),
    )
    .ok()
}

pub fn listar(stmt: &mut Stmt) -> Vec<String> {
    stmt.query_map(params![], |row| row.get::<_, String>(1))
        .unwrap()
        .filter_map(Result::ok)
        .collect()
}

pub async fn buscar(pool: &PgPool) -> Option<(String, String)> {
    sqlx::query_as("SELECT nome, cpf FROM titulares LIMIT 1")
        .fetch_optional(pool)
        .await
        .ok()
        .flatten()
}

// (9) DDL de credencial de BANCO nao e dado de titular. `PASSWORD` aqui e
//     PALAVRA-CHAVE DO SQL, nao coluna — e administrar role de banco e
//     assunto de S-15. Um achado aqui mandaria o time cifrar uma keyword.
pub async fn preparar_role(pool: &PgPool) {
    sqlx::query(
        "DO $$ BEGIN
             CREATE ROLE app_teste LOGIN PASSWORD 'trocada-no-provisionamento';
         EXCEPTION WHEN duplicate_object THEN NULL; END $$",
    )
    .execute(pool)
    .await
    .unwrap();
}
