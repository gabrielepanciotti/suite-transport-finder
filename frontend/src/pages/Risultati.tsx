import { useMemo, useState } from "react";
import { AlertCircle, ListFilter } from "lucide-react";
import {
  Button,
  Callout,
  EmptyState,
  PageHeader,
  SearchBar,
  Segmented,
  Skeleton,
} from "@suite/design-system";
import JourneyTable from "../components/JourneyTable";
import type { Journey, SearchResponse, SortKey } from "../types";

const sortOptions = [
  { value: "departure", label: "Partenza" },
  { value: "duration", label: "Durata" },
  { value: "price", label: "Prezzo" },
];

const modeOptions = [
  { value: "all", label: "Tutti" },
  { value: "train", label: "Treno" },
  { value: "bus", label: "Bus" },
];

interface RisultatiProps {
  loading: boolean;
  data: SearchResponse | null;
  error: string | null;
  onNewSearch: () => void;
  onRetry: () => void;
  onSave: (journey: Journey) => void;
}

function emptyResults(onNewSearch: () => void) {
  return (
    <EmptyState
      icon={<ListFilter aria-hidden />}
      title="Nessun risultato trovato"
      description="Allarga l'intervallo di prezzo o modifica le date"
      action={<Button onClick={onNewSearch}>Modifica criteri</Button>}
    />
  );
}

export function Risultati({
  loading,
  data,
  error,
  onNewSearch,
  onRetry,
  onSave,
}: RisultatiProps) {
  const [sort, setSort] = useState<SortKey>("departure");
  const [mode, setMode] = useState("all");
  const [query, setQuery] = useState("");
  const journeys = useMemo(() => {
    return (data?.journeys ?? [])
      .filter(
        (journey) =>
          (mode === "all" || journey.mode === mode)
          && `${journey.origin} ${journey.destination} ${journey.provider}`
            .toLocaleLowerCase("it")
            .includes(query.toLocaleLowerCase("it")),
      )
      .sort((first, second) => {
        if (sort === "price") {
          return (first.price ?? Infinity) - (second.price ?? Infinity);
        }
        if (sort === "duration") {
          return first.duration_min - second.duration_min;
        }
        return +new Date(first.departure) - +new Date(second.departure);
      });
  }, [data, mode, query, sort]);

  return (
    <div className="flex min-w-0 flex-col gap-6">
      <PageHeader
        icon={<ListFilter aria-hidden />}
        title="Risultati"
        subtitle={
          data
            ? `${data.origin} → ${data.destination}`
            : "Le opzioni trovate per la tua ricerca"
        }
        actions={<Button onClick={onNewSearch}>Nuova ricerca</Button>}
      />
      {loading && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-36 w-full" />
        </div>
      )}
      {error && (
        <div className="flex flex-col gap-3">
          <Callout
            variant="danger"
            title="Impossibile completare la ricerca sulle fonti selezionate"
            icon={<AlertCircle aria-hidden />}
          >
            {error}
          </Callout>
          <Button onClick={onRetry}>Riprova</Button>
        </div>
      )}
      {!loading && !error && !data && (
        <EmptyState
          icon={<ListFilter aria-hidden />}
          title="Nessun risultato trovato"
          description="Avvia una ricerca per vedere le opzioni disponibili"
          action={<Button onClick={onNewSearch}>Avvia ricerca</Button>}
        />
      )}
      {!loading && data && (
        <>
          <div className="flex flex-col gap-4 rounded-md border border-border bg-surface p-4">
            <SearchBar
              className="min-h-11"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Filtra i risultati"
              aria-label="Filtra i risultati"
            />
            <Segmented
              className="[&_button]:min-h-11"
              options={sortOptions}
              value={sort}
              onValueChange={(value) => setSort(value as SortKey)}
              ariaLabel="Ordina risultati"
            />
            <Segmented
              className="[&_button]:min-h-11"
              options={modeOptions}
              value={mode}
              onValueChange={setMode}
              ariaLabel="Filtra per mezzo"
            />
          </div>
          {data.errors.length > 0 && (
            <Callout
              variant="warning"
              title="Alcune fonti non sono disponibili"
            >
              {data.errors.join(" ")}
            </Callout>
          )}
          {journeys.length ? (
            <JourneyTable journeys={journeys} onSave={onSave} />
          ) : (
            emptyResults(onNewSearch)
          )}
        </>
      )}
    </div>
  );
}
