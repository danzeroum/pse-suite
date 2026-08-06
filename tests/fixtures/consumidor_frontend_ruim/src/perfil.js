// FE-02 e FE-03: PII no storage do cliente, PII na URL, token no localStorage.
export function salvarPerfil(user, jwt) {
  localStorage.setItem("cpf", user.cpf);                 // FE-02 CRITICO
  sessionStorage.setItem("token", jwt);                  // FE-03 ALTO
  const url = "/relatorio?email=" + user.email;          // FE-02 CRITICO
  return fetch(url);
}
