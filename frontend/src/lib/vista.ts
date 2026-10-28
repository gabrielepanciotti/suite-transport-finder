import type { VistaBody, VistaFetcher } from "@suite/design-system";

const fallback: VistaBody = {
  ruolo: "admin",
  etichetta: "Amministratore",
  sezioni: [
    { id: "cerca", titolo: "Cerca", nascosta: false, preferita: false },
    { id: "risultati", titolo: "Risultati", nascosta: false, preferita: false },
    { id: "salvati", titolo: "Salvati", nascosta: false, preferita: false },
    { id: "impostazioni", titolo: "Impostazioni", nascosta: false, preferita: false },
  ],
  azioni: {
    "ricerca.crea": true, "ricerca.elimina": true, "salvato.crea": true,
    "salvato.modifica": true, "salvato.elimina": true, "impostazioni.modifica": true,
  },
  preferenze: { nascoste: [], ordine: ["cerca", "risultati", "salvati", "impostazioni"], preferiti: [] },
};

export const vistaFetcher: VistaFetcher = async (input, init) => {
  const url = String(input);
  if (url !== "/api/vista" || init?.method) return fetch(input, init);
  try {
    const response = await fetch(input, init);
    return response.ok ? response : fallback;
  } catch {
    return fallback;
  }
};
