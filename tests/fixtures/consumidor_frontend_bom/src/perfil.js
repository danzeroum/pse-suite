// FE-02 conforme: o que vai para o storage passa por mascaramento, e a URL
// nao carrega dado pessoal. FE-03 conforme: o token nao existe no cliente —
// vive em cookie HttpOnly+Secure emitido pelo servidor.
import { mask } from "./mascaramento";

export function salvarPerfil(user) {
  localStorage.setItem("cpf", mask(user.cpf));
  const url = "/relatorio?ref=" + user.idPseudonimo;
  return fetch(url, { credentials: "include" });
}
