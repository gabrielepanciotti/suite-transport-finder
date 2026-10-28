export type SortKey = "departure" | "duration" | "price";

export interface Journey {
  provider: string | null;
  mode: string;
  origin: string | null;
  destination: string | null;
  departure: string;
  arrival: string;
  duration_min: number;
  changes: number;
  layover_min: number | null;
  price: number | null;
  currency: string;
  legs: string[];
  note: string | null;
  deeplink: string | null;
  price_breakdown: string | null;
}

export interface SearchResponse {
  origin: string;
  destination: string;
  date: string;
  errors: string[];
  journeys: Journey[];
}

export interface SearchRequest {
  origin: string;
  destination: string;
  day: string;
  modes: string[];
  sort: SortKey;
  max_changes: number | null;
  combine: boolean;
}

export interface SavedRoute {
  id: number; origin: string; destination: string; mode: string; provider: string | null;
  url: string | null; duration_minutes: number | null; price: number | null; currency: string | null;
  departure: string | null; arrival: string | null; notes: string | null; source: string;
  created: string; updated: string;
}
