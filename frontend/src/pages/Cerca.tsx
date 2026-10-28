import { AlertCircle, Search } from "lucide-react";
import {
  Button,
  Callout,
  EmptyState,
  PageHeader,
} from "@suite/design-system";
import SearchForm from "../components/SearchForm";
import type { SearchRequest } from "../types";

interface CercaProps {
  loading: boolean;
  initial: SearchRequest | null;
  onSearch: (request: SearchRequest) => void;
  error: string | null;
  onRetry: () => void;
}

export function Cerca({
  loading,
  initial,
  onSearch,
  error,
  onRetry,
}: CercaProps) {
  return (
    <div className="flex max-w-4xl flex-col gap-6">
      <PageHeader
        icon={<Search aria-hidden />}
        title="Cerca"
        subtitle="Confronta treni e pullman sulla tua tratta."
      />
      <SearchForm loading={loading} initial={initial} onSubmit={onSearch} />
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
      {!loading && !error && (
        <EmptyState
          icon={<Search aria-hidden />}
          title="Nessuna ricerca recente"
          description="Imposta i parametri qui sopra per interrogare le fonti disponibili"
          action={
            <Button type="submit" form="search-form">
              Avvia ricerca
            </Button>
          }
        />
      )}
    </div>
  );
}
