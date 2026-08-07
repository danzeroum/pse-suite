// D-08 em Rust: a forma CORRETA nao pode ser punida.
//
// Nenhuma destas ligacoes carrega literal: a chave vem do ambiente em
// EXECUCAO, ou de um cofre. Nao ha o que hardcodar.
use std::env;

pub struct Cliente {
    pub api_key: String,
    pub client_secret: String,
}

impl Cliente {
    pub fn novo() -> Result<Self, env::VarError> {
        let api_key = std::env::var("API_KEY")?;
        let client_secret = env::var("CLIENT_SECRET")?;
        Ok(Self { api_key, client_secret })
    }

    pub async fn do_cofre(nome: &str) -> String {
        let cliente = aws_sdk_secretsmanager::Client::new(&aws_config::from_env()
            .region(aws_config::Region::new("sa-east-1"))
            .load()
            .await);
        let saida = cliente.get_secret_value().secret_id(nome).send().await.unwrap();
        saida.secret_string().unwrap_or_default().to_string()
    }
}
