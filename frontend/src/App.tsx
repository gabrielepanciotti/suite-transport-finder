import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ListFilter,
  Search,
  Settings,
  Star,
  type LucideIcon,
} from "lucide-react";
import {
  AppShell,
  Button,
  EmptyState,
  Skeleton,
  VistaProvider,
  useVista,
} from "@suite/design-system";
import { Cerca } from "./pages/Cerca";
import { Risultati } from "./pages/Risultati";
import { Salvati } from "./pages/Salvati";
import { Impostazioni } from "./pages/Impostazioni";
import { useSearch } from "./hooks/useSearch";
import { useRoutes } from "./hooks/useRoutes";
import { parseSearchQuery, toSearchQuery } from "./lib/url";
import { sezioneAttiva } from "./lib/sezione";
import { vistaFetcher } from "./lib/vista";
import type { SearchRequest } from "./types";

const ICONS: Record<string, LucideIcon> = {
  cerca: Search,
  risultati: ListFilter,
  salvati: Star,
  impostazioni: Settings,
};

function defaultSidebarCollapsed() {
  return typeof window !== "undefined"
    && window.matchMedia("(max-width: 767px)").matches;
}

function FinderShell() {
  const { sezioniVisibili, stato, ricarica } = useVista();
  const search = useSearch();
  const routes = useRoutes();
  const initial = useMemo(
    () => parseSearchQuery(window.location.search),
    [],
  );
  const booted = useRef(false);
  const [defaultCollapsed] = useState(defaultSidebarCollapsed);
  const [announcement, setAnnouncement] = useState("");
  const [section, setSection] = useState(
    () => window.location.hash.slice(1) || "cerca",
  );

  useEffect(() => {
    const sync = () => setSection(window.location.hash.slice(1) || "cerca");
    window.addEventListener("hashchange", sync);
    return () => window.removeEventListener("hashchange", sync);
  }, []);

  useEffect(() => {
    if (!booted.current && initial) {
      booted.current = true;
      void search.run(initial);
    }
  }, [initial, search]);

  useEffect(() => {
    if (search.data) {
      setAnnouncement(`${search.data.journeys.length} risultati trovati`);
    }
  }, [search.data]);

  const vistaPronta = stato === "ready" && sezioniVisibili.length > 0;
  const active = sezioneAttiva(section, sezioniVisibili, vistaPronta);

  useEffect(() => {
    if (!vistaPronta) return;
    if (window.location.hash !== `#${active}`) {
      window.location.hash = active;
    }
  }, [active, vistaPronta]);

  const go = (next: string) => {
    window.location.hash = next;
  };

  const start = (request: SearchRequest) => {
    window.history.replaceState(
      null,
      "",
      `${window.location.pathname}?${toSearchQuery(request)}#risultati`,
    );
    void search.run(request);
    go("risultati");
  };

  const saveJourney = async (journey: Parameters<typeof routes.save>[0]) => {
    await routes.save(journey);
    setAnnouncement("Elemento salvato");
  };

  const content = active === "cerca" ? (
    <Cerca
      loading={search.loading}
      initial={initial}
      onSearch={start}
      error={search.error}
      onRetry={search.retry}
    />
  ) : active === "risultati" ? (
    <Risultati
      loading={search.loading}
      data={search.data}
      error={search.error}
      onNewSearch={() => go("cerca")}
      onRetry={search.retry}
      onSave={(journey) => void saveJourney(journey)}
    />
  ) : active === "salvati" ? (
    <Salvati
      items={routes.items}
      loading={routes.loading}
      error={routes.error}
      retry={() => void routes.load()}
      onRemove={routes.remove}
      onNewSearch={() => go("cerca")}
    />
  ) : (
    <Impostazioni />
  );

  if (stato === "loading") {
    return (
      <AppShell defaultCollapsed={defaultCollapsed}>
        <AppShell.Content className="max-md:pl-12 p-4 sm:p-6">
          <Skeleton className="h-10 w-48" />
          <Skeleton className="mt-6 h-56 w-full" />
        </AppShell.Content>
      </AppShell>
    );
  }

  if (stato === "error") {
    return (
      <AppShell defaultCollapsed={defaultCollapsed}>
        <AppShell.Content className="max-md:pl-12">
          <EmptyState
            icon={<AlertCircle aria-hidden />}
            title="Impossibile caricare la vista"
            action={<Button onClick={() => void ricarica()}>Riprova</Button>}
          />
        </AppShell.Content>
      </AppShell>
    );
  }

  return (
    <AppShell defaultCollapsed={defaultCollapsed}>
      <AppShell.Sidebar
        settingsItem={
          sezioniVisibili.find((item) => item.id === "impostazioni") && (
            <AppShell.Sidebar.Item
              icon={<Settings aria-hidden />}
              label="Impostazioni"
              active={active === "impostazioni"}
              onClick={() => go("impostazioni")}
            />
          )
        }
      >
        {sezioniVisibili
          .filter((item) => item.id !== "impostazioni")
          .slice(0, 7)
          .map((item) => {
            const Icon = ICONS[item.id] ?? Search;
            return (
              <AppShell.Sidebar.Item
                key={item.id}
                icon={<Icon aria-hidden />}
                label={item.titolo}
                active={active === item.id}
                onClick={() => go(item.id)}
              />
            );
          })}
      </AppShell.Sidebar>
      <div className="flex min-w-0 flex-1 flex-col">
        <AppShell.Topbar>
          <span className="text-sm font-medium text-text">TransportFinder</span>
        </AppShell.Topbar>
        <AppShell.Content className="max-md:pl-12 p-4 sm:p-6">
          {content}
        </AppShell.Content>
      </div>
      <p aria-live="polite" className="sr-only">
        {announcement}
      </p>
    </AppShell>
  );
}

export default function App() {
  return (
    <VistaProvider fetcher={vistaFetcher}>
      <FinderShell />
    </VistaProvider>
  );
}
