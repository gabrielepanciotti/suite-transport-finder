import { useState, type FormEvent } from "react";
import {
  Button,
  DatePicker,
  Field,
  Input,
  Segmented,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Toggle,
} from "@suite/design-system";
import type { SearchRequest, SortKey } from "../types";

const SORT_OPTIONS = [
  { value: "departure", label: "Partenza" },
  { value: "duration", label: "Durata" },
  { value: "price", label: "Prezzo" },
];

const MODE_OPTIONS = [
  { value: "all", label: "Tutti i mezzi" },
  { value: "train", label: "Solo treno" },
  { value: "bus", label: "Solo bus" },
  { value: "itabus", label: "Solo Itabus" },
];

const MODES_BY_VALUE: Record<string, string[]> = {
  all: ["train", "bus", "itabus"],
  train: ["train"],
  bus: ["bus"],
  itabus: ["itabus"],
};

function modeValueFromModes(modes: string[]): string {
  const key = [...modes].sort().join(",");
  for (const [value, mapped] of Object.entries(MODES_BY_VALUE)) {
    if ([...mapped].sort().join(",") === key) return value;
  }
  return "all";
}

function maxChangesFromValue(value: string): number | null {
  return value === "none" ? null : Number(value);
}

function maxChangesToValue(value: number | null): string {
  return value == null ? "none" : String(value);
}

function toIsoDate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function tomorrow(): string {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return toIsoDate(d);
}

interface Props {
  loading: boolean;
  initial: SearchRequest | null;
  onSubmit: (request: SearchRequest) => void;
}

export default function SearchForm({ loading, initial, onSubmit }: Props) {
  const [origin, setOrigin] = useState(initial?.origin ?? "");
  const [destination, setDestination] = useState(initial?.destination ?? "");
  const [day, setDay] = useState(initial?.day ?? tomorrow());
  const [modeValue, setModeValue] = useState(
    initial ? modeValueFromModes(initial.modes) : "all",
  );
  const [sort, setSort] = useState<SortKey>(initial?.sort ?? "departure");
  const [maxChanges, setMaxChanges] = useState(
    maxChangesToValue(initial?.max_changes ?? null),
  );
  const [combine, setCombine] = useState(initial?.combine ?? false);
  const [validation, setValidation] = useState<{
    origin?: string;
    destination?: string;
  }>({});

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (loading) return;
    const errors: { origin?: string; destination?: string } = {};
    if (!origin.trim()) errors.origin = "Inserisci la partenza";
    if (!destination.trim()) errors.destination = "Inserisci l'arrivo";
    setValidation(errors);
    if (Object.keys(errors).length > 0) return;

    onSubmit({
      origin: origin.trim(),
      destination: destination.trim(),
      day,
      modes: MODES_BY_VALUE[modeValue],
      sort,
      max_changes: maxChangesFromValue(maxChanges),
      combine,
    });
  };

  return (
    <form
      id="search-form"
      onSubmit={handleSubmit}
      className="rounded-md border border-border bg-surface p-5"
    >
      <div className="grid min-w-0 w-full gap-4 sm:grid-cols-2">
        <Field
          className="min-w-0 w-full"
          label="Partenza"
          htmlFor="origin"
          required
          error={validation.origin}
        >
          <Input
            className="min-w-0 w-full"
            id="origin"
            value={origin}
            onChange={(e) => {
              setOrigin(e.target.value);
              if (validation.origin) setValidation((v) => ({ ...v, origin: undefined }));
            }}
            placeholder="Perugia"
            aria-required="true"
            invalid={!!validation.origin}
          />
        </Field>
        <Field
          className="min-w-0 w-full"
          label="Arrivo"
          htmlFor="destination"
          required
          error={validation.destination}
        >
          <Input
            className="min-w-0 w-full"
            id="destination"
            value={destination}
            onChange={(e) => {
              setDestination(e.target.value);
              if (validation.destination) {
                setValidation((current) => ({
                  ...current,
                  destination: undefined,
                }));
              }
            }}
            placeholder="Udine"
            aria-required="true"
            invalid={!!validation.destination}
          />
        </Field>
        <Field className="min-w-0 w-full" label="Data" htmlFor="day">
          <DatePicker
            id="day"
            value={day ? new Date(`${day}T12:00:00`) : undefined}
            onChange={(value) => value && setDay(toIsoDate(value))}
            aria-label="Data del viaggio"
            locale="it-IT"
            className="min-h-11 min-w-0 w-full"
          />
        </Field>
        <Field className="min-w-0 w-full" label="Ordinamento">
          <Segmented
            options={SORT_OPTIONS}
            value={sort}
            onValueChange={(v) => setSort(v as SortKey)}
            ariaLabel="Ordinamento"
            className="min-w-0 w-full [&_button]:min-h-11"
          />
        </Field>
      </div>

      <div className="mt-4 flex min-w-0 w-full flex-col gap-4">
        <Field className="min-w-0 w-full" label="Mezzi">
          <Segmented
            options={MODE_OPTIONS}
            value={modeValue}
            onValueChange={setModeValue}
            ariaLabel="Mezzi"
            className="min-w-0 w-full flex-wrap sm:flex-nowrap [&_button]:min-h-11"
          />
        </Field>

        <div className="flex flex-wrap items-end justify-between gap-4">
          <Field label="Cambi massimi">
            <Select value={maxChanges} onValueChange={setMaxChanges}>
              <SelectTrigger className="min-h-11 w-44" aria-label="Cambi massimi">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">Nessun limite</SelectItem>
                <SelectItem value="0">Diretti (0 cambi)</SelectItem>
                <SelectItem value="1">1 cambio</SelectItem>
                <SelectItem value="2">2 cambi</SelectItem>
              </SelectContent>
            </Select>
          </Field>

          <label className="flex min-h-11 items-center gap-2 text-sm text-text">
            <Toggle checked={combine} onCheckedChange={setCombine} />
            Itinerari misti treno+bus
          </label>
        </div>

        <Button type="submit" loading={loading} size="lg">
          Avvia ricerca
        </Button>
      </div>
    </form>
  );
}
