import { Star, TriangleAlert } from "lucide-react";
import { Badge, Button, DataTable, type Column } from "@suite/design-system";
import type { Journey } from "../types";

type BadgeState = "success" | "warning" | "danger" | "info";

const MODE_META: Record<string, { label: string; state: BadgeState }> = {
  train: { label: "Treno", state: "info" },
  bus: { label: "Bus", state: "warning" },
  mix: { label: "Misto", state: "success" },
};

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("it-IT", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function dayOffset(departure: string, arrival: string): number {
  const d = new Date(departure);
  const a = new Date(arrival);
  const dd = new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const ad = new Date(a.getFullYear(), a.getMonth(), a.getDate()).getTime();
  return Math.round((ad - dd) / 86400000);
}

function fmtDuration(min: number): string {
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}h${String(m).padStart(2, "0")}`;
}

function fmtSosta(min: number | null): string {
  if (min == null) return "—";
  if (min < 60) return `${min}′`;
  const h = Math.floor(min / 60);
  const m = min % 60;
  return `${h}h${String(m).padStart(2, "0")}`;
}

function fmtPrice(journey: Journey): string {
  if (journey.price == null) return "n.d.";
  return `${journey.price.toFixed(2).replace(".", ",")} ${journey.currency}`;
}

function isSosta(leg: string): boolean {
  return leg.startsWith("(sosta");
}

function SaveJourneyButton({
  journey,
  onSave,
}: {
  journey: Journey;
  onSave?: (journey: Journey) => void;
}) {
  if (!onSave) return null;

  return (
    <Button
      variant="ghost"
      aria-label="Salva nei preferiti"
      className="size-11 p-0"
      onClick={() => onSave(journey)}
    >
      <Star aria-hidden />
    </Button>
  );
}

function RouteDetails({ journey }: { journey: Journey }) {
  const links = journey.deeplink
    ? journey.deeplink.split(" | ").filter(Boolean)
    : [];

  return (
    <div className="flex flex-col gap-1.5">
      {journey.note && (
        <span className="flex items-start gap-1 text-xs leading-tight text-danger">
          <TriangleAlert aria-hidden className="mt-0.5 size-3 shrink-0" />
          {journey.note}
        </span>
      )}
      <div className="flex flex-col gap-0.5">
        {journey.legs.map((leg, index) => (
          <span
            key={index}
            className={
              isSosta(leg)
                ? "pl-3 text-xs italic text-muted"
                : "text-xs"
            }
          >
            {leg}
          </span>
        ))}
      </div>
      {links.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {links.map((url, index) => (
            <Button
              key={`${url}-${index}`}
              asChild
              variant="link"
              size="sm"
              className="h-auto p-0 text-xs"
            >
              <a href={url} target="_blank" rel="noreferrer">
                {links.length > 1 ? `Acquista ${index + 1}` : "Acquista"}
              </a>
            </Button>
          ))}
        </div>
      )}
    </div>
  );
}

const IDENTITY_COLUMNS: Column<Journey>[] = [
  {
    key: "mode",
    header: "Mezzo",
    sortable: true,
    accessor: (j) => j.mode,
    render: (j) => {
      const meta = MODE_META[j.mode] ?? {
        label: j.mode,
        state: "info" as BadgeState,
      };
      return (
        <div className="flex flex-col items-start gap-0.5">
          <Badge state={meta.state}>{meta.label}</Badge>
          {j.provider && (
            <span className="text-xs text-muted">{j.provider}</span>
          )}
        </div>
      );
    },
  },
];

const SCHEDULE_COLUMNS: Column<Journey>[] = [
  {
    key: "departure",
    header: "Partenza",
    sortable: true,
    accessor: (j) => new Date(j.departure).getTime(),
    render: (j) => (
      <span className="whitespace-nowrap font-medium">
        {fmtTime(j.departure)}
      </span>
    ),
  },
];

const DETAILS_COLUMNS: Column<Journey>[] = [
    {
      key: "arrival",
      header: "Arrivo",
      sortable: true,
      accessor: (j) => new Date(j.arrival).getTime(),
      render: (j) => {
        const off = dayOffset(j.departure, j.arrival);
        return (
          <span className="whitespace-nowrap font-medium">
            {fmtTime(j.arrival)}
            {off > 0 && (
              <span className="ml-1 text-xs text-muted">+{off}</span>
            )}
          </span>
        );
      },
    },
    {
      key: "duration",
      header: "Durata",
      sortable: true,
      accessor: (j) => j.duration_min,
      render: (j) => (
        <span className="whitespace-nowrap text-muted">
          {fmtDuration(j.duration_min)}
        </span>
      ),
    },
    {
      key: "changes",
      header: "Cambi",
      sortable: true,
      accessor: (j) => j.changes,
      render: (j) => (
        <span className="whitespace-nowrap">
          {j.changes === 1 ? "1 cambio" : `${j.changes} cambi`}
        </span>
      ),
    },
    {
      key: "layover",
      header: "Sosta",
      sortable: true,
      accessor: (journey) => (
        journey.layover_min == null
          ? Number.POSITIVE_INFINITY
          : journey.layover_min
      ),
      render: (j) => (
        <span className="whitespace-nowrap">
          {j.layover_min == null ? (
            <span className="text-muted">—</span>
          ) : j.layover_min < 45 ? (
            <span className="font-medium text-danger">{fmtSosta(j.layover_min)}</span>
          ) : (
            <span className="text-muted">{fmtSosta(j.layover_min)}</span>
          )}
        </span>
      ),
    },
    {
      key: "price",
      header: "Prezzo",
      sortable: true,
      accessor: (journey) => (
        journey.price == null ? Number.POSITIVE_INFINITY : journey.price
      ),
      render: (j) => (
        <div className="whitespace-nowrap text-right">
          <div className="font-semibold">{fmtPrice(j)}</div>
          {j.price_breakdown && (
            <div className="text-xs text-muted">
              {j.price_breakdown.replace(/ /g, "")}
            </div>
          )}
        </div>
      ),
    },
    {
      key: "route",
      header: "Percorso",
      accessor: () => "",
      render: (journey) => <RouteDetails journey={journey} />,
    },
];

interface JourneyTableProps {
  journeys: Journey[];
  onSave?: (journey: Journey) => void;
}

export default function JourneyTable({
  journeys,
  onSave,
}: JourneyTableProps) {
  const saveColumn: Column<Journey> = {
    key: "save",
    header: "Salva",
    accessor: () => "",
    render: (journey) => (
      <SaveJourneyButton journey={journey} onSave={onSave} />
    ),
  };
  const columns = [
    saveColumn,
    ...IDENTITY_COLUMNS,
    ...SCHEDULE_COLUMNS,
    ...DETAILS_COLUMNS,
  ];

  return (
    <div className="overflow-x-auto rounded-md border border-border bg-surface">
      <DataTable
        columns={columns}
        data={journeys}
        rowKey={(j) => `${j.departure}-${j.arrival}-${j.price ?? ""}`}
      />
    </div>
  );
}
