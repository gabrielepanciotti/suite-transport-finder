import { useCallback, useEffect, useState } from "react";
import type { Journey, SavedRoute } from "../types";

function message(error: unknown) { return error instanceof Error ? error.message : "Errore imprevisto"; }

export function useRoutes() {
  const [items, setItems] = useState<SavedRoute[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try { const r = await fetch("/api/routes"); if (!r.ok) throw new Error("Impossibile caricare i salvati"); setItems(await r.json()); }
    catch (e) { setError(message(e)); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const save = useCallback(async (journey: Journey) => {
    const mode = journey.mode === "mix" ? "transit" : journey.mode === "itabus" ? "bus" : journey.mode;
    const r = await fetch("/api/routes", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ origin: journey.origin ?? "", destination: journey.destination ?? "", mode, provider: journey.provider, url: journey.deeplink, duration_minutes: journey.duration_min, price: journey.price, currency: journey.currency, departure: journey.departure, arrival: journey.arrival, notes: journey.note, source: "api" }) });
    if (!r.ok) throw new Error("Impossibile salvare il risultato");
    const added = await r.json() as SavedRoute; setItems((current) => [...current, added]);
  }, []);
  const remove = useCallback(async (id: number) => {
    const r = await fetch(`/api/routes/${id}`, { method: "DELETE" });
    if (!r.ok) throw new Error("Impossibile rimuovere il salvato");
    setItems((current) => current.filter((item) => item.id !== id));
  }, []);
  return { items, loading, error, load, save, remove };
}
