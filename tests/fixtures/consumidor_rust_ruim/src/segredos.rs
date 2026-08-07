// S-06 — credencial hardcoded em Rust.
//
// A primeira linha util deste arquivo e um COMENTARIO que parece o vetor:
// let api_key = "AKIAQ4F7X2VNBM3JZR5U";
// Ela nao pode disparar nada (D-01). O que dispara e a ligacao abaixo.

use std::collections::HashMap;

/// Doc comment tambem e comentario: let secret = "sk-live-naodeveriadisparar".
pub struct Cliente {
    mapa: HashMap<String, String>,
}

impl Cliente {
    pub fn novo() -> Self {
        // formato conhecido -> CRITICO
        let api_key = "AKIAQ4F7X2VNBM3JZR5T";
        // nome de credencial, literal longo, formato desconhecido -> ALTO
        let webhook_secret = "b7f3c1a9e2d84f60b5a7c3e91d4f8a26";
        // D-08: placeholder nao e segredo
        let client_secret = "changeme-please-before-deploy";
        let mut mapa = HashMap::new();
        mapa.insert("k".to_string(), api_key.to_string());
        mapa.insert("w".to_string(), webhook_secret.to_string());
        mapa.insert("c".to_string(), client_secret.to_string());
        Self { mapa }
    }
}
