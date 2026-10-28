import { useState } from "react";
import { AlertCircle, Star } from "lucide-react";
import {
  Button,
  Callout,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  EmptyState,
  PageHeader,
  Skeleton,
} from "@suite/design-system";
import type { SavedRoute } from "../types";

interface SalvatiProps {
  items: SavedRoute[];
  loading: boolean;
  error: string | null;
  retry: () => void;
  onRemove: (id: number) => Promise<void>;
  onNewSearch: () => void;
}

function savedRoutePrice(item: SavedRoute) {
  if (item.price == null) return null;

  return new Intl.NumberFormat("it-IT", {
    style: "currency",
    currency: item.currency ?? "EUR",
  }).format(item.price);
}

function SavedRouteCard({
  item,
  onRemove,
}: {
  item: SavedRoute;
  onRemove: () => void;
}) {
  const price = savedRoutePrice(item);

  return (
    <article
      className={[
        "flex flex-col gap-3 rounded-md border border-border bg-surface p-4",
        "sm:flex-row sm:items-center sm:justify-between",
      ].join(" ")}
    >
      <div>
        <h2 className="font-semibold">
          {item.origin} → {item.destination}
        </h2>
        <p className="text-sm text-muted">
          {item.provider ?? item.mode}
          {price && ` · ${price}`}
        </p>
      </div>
      <Button
        variant="destructive"
        onClick={onRemove}
        className="min-h-11"
      >
        Rimuovi dai salvati
      </Button>
    </article>
  );
}

export function Salvati({
  items,
  loading,
  error,
  retry,
  onRemove,
  onNewSearch,
}: SalvatiProps) {
  const [selected, setSelected] = useState<SavedRoute | null>(null);
  const [removing, setRemoving] = useState(false);
  const [removeError, setRemoveError] = useState<string | null>(null);

  const rimuoviSelezionato = async () => {
    if (!selected) return;

    setRemoving(true);
    setRemoveError(null);
    try {
      await onRemove(selected.id);
      setSelected(null);
    } catch {
      setRemoveError("Impossibile rimuovere il salvato");
    } finally {
      setRemoving(false);
    }
  };

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <PageHeader
        icon={<Star aria-hidden />}
        title="Salvati"
        subtitle="Le tratte che vuoi ritrovare."
      />
      {loading && (
        <>
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </>
      )}
      {error && (
        <div className="flex flex-col gap-3">
          <Callout
            variant="danger"
            title="Impossibile caricare i salvati"
            icon={<AlertCircle aria-hidden />}
          >
            {error}
          </Callout>
          <Button onClick={retry}>Riprova</Button>
        </div>
      )}
      {!loading && !error && !items.length && (
        <EmptyState
          icon={<Star aria-hidden />}
          title="Nessun elemento salvato"
          description="Salva i risultati migliori durante una ricerca per ritrovarli qui"
          action={<Button onClick={onNewSearch}>Nuova ricerca</Button>}
        />
      )}
      {!loading && !error && items.map((item) => (
        <SavedRouteCard
          key={item.id}
          item={item}
          onRemove={() => setSelected(item)}
        />
      ))}
      <Dialog
        open={!!selected}
        onOpenChange={(open) => !open && setSelected(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rimuovere dai salvati?</DialogTitle>
            <DialogDescription>
              La tratta selezionata verrà eliminata dai tuoi elementi salvati.
            </DialogDescription>
          </DialogHeader>
          {removeError && <Callout variant="danger">{removeError}</Callout>}
          <DialogFooter>
            <Button variant="secondary" onClick={() => setSelected(null)}>
              Annulla
            </Button>
            <Button
              variant="destructive"
              loading={removing}
              onClick={() => void rimuoviSelezionato()}
            >
              Rimuovi dai salvati
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
