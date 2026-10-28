import type { SearchRequest, SortKey } from "../types";

const SORTS: SortKey[] = ["departure", "duration", "price"];

/**
 * Read a search request from the URL query string, so a result page can be
 * bookmarked and reopened: `/?from=Perugia&to=Udine&day=2026-09-20&combine=1`.
 * Returns `null` when the required fields are absent (no search to auto-run).
 */
export function parseSearchQuery(qs: string): SearchRequest | null {
  const p = new URLSearchParams(qs);
  const origin = p.get("from")?.trim() ?? "";
  const destination = p.get("to")?.trim() ?? "";
  const day = p.get("day") ?? "";
  if (!origin || !destination || !day) return null;

  const modes = (p.get("modes") ?? "train,bus,itabus")
    .split(",")
    .map((m) => m.trim())
    .filter(Boolean);
  const sortRaw = p.get("sort") ?? "departure";
  const sort = (SORTS as string[]).includes(sortRaw)
    ? (sortRaw as SortKey)
    : "departure";
  const maxChangesRaw = p.get("maxChanges");
  const max_changes =
    maxChangesRaw != null && maxChangesRaw !== "" ? Number(maxChangesRaw) : null;

  return {
    origin,
    destination,
    day,
    modes: modes.length ? modes : ["train", "bus", "itabus"],
    sort,
    combine: p.get("combine") === "1",
    max_changes: Number.isFinite(max_changes) ? max_changes : null,
  };
}

/** Serialize a search request back to a query string (keeps the URL shareable). */
export function toSearchQuery(req: SearchRequest): string {
  const p = new URLSearchParams();
  p.set("from", req.origin);
  p.set("to", req.destination);
  p.set("day", req.day);
  p.set("modes", req.modes.join(","));
  p.set("sort", req.sort);
  p.set("combine", req.combine ? "1" : "0");
  if (req.max_changes != null) p.set("maxChanges", String(req.max_changes));
  return p.toString();
}
