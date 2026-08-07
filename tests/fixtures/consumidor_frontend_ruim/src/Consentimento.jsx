// FE-01: consentimento pre-marcado. O material de fundacao chama isto de
// "toggle pre-marcado" e classifica como violacao de privacidade por default.
import React from "react";

export function PreferenciasDeConsentimento() {
  // consent default on -- este comentario NAO e o controle, e so texto.
  return (
    <form>
      <label>
        <input type="checkbox" name="consent_marketing" checked />
        Aceito receber comunicacoes de marketing
      </label>
      <label>
        <input type="checkbox" id="consentimento-analytics" defaultChecked={true} />
        Aceito cookies de analytics
      </label>
    </form>
  );
}
