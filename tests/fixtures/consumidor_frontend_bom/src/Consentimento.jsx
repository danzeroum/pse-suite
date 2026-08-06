// FE-01 conforme: o toggle nasce DESLIGADO, e quando nasce ligado e porque
// reflete uma escolha registrada do titular (estado), com handler de mudanca.
import React, { useState } from "react";

export function PreferenciasDeConsentimento({ consentimentoSalvo }) {
  const [marketing, setMarketing] = useState(consentimentoSalvo.marketing);
  const [analytics, setAnalytics] = useState(false);
  return (
    <form>
      <label>
        <input
          type="checkbox"
          name="consent_marketing"
          checked={marketing}
          onChange={e => setMarketing(e.target.checked)}
        />
        Aceito receber comunicacoes de marketing
      </label>
      <label>
        <input
          type="checkbox"
          id="consentimento-analytics"
          checked={analytics}
          onChange={e => setAnalytics(e.target.checked)}
        />
        Aceito cookies de analytics
      </label>
    </form>
  );
}
