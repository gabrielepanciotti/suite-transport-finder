import { useCallback, useRef, useState } from "react";
import type { SearchRequest, SearchResponse } from "../types";

interface SearchState {
  loading: boolean;
  data: SearchResponse | null;
  error: string | null;
}

const INITIAL: SearchState = { loading: false, data: null, error: null };

export function useSearch() {
  const [state, setState] = useState<SearchState>(INITIAL);
  const abortRef = useRef<AbortController | null>(null);
  const requestRef = useRef<SearchRequest | null>(null);

  const run = useCallback(async (request: SearchRequest) => {
    requestRef.current = request;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    setState({ loading: true, data: null, error: null });
    try {
      const response = await fetch("/api/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
        signal: controller.signal,
      });
      if (!response.ok) {
        const body = await response.json().catch(() => null);
        throw new Error(body?.detail ?? `Errore ${response.status}`);
      }
      const data = (await response.json()) as SearchResponse;
      setState({ loading: false, data, error: null });
    } catch (err) {
      if (controller.signal.aborted) return;
      setState({
        loading: false,
        data: null,
        error: err instanceof Error ? err.message : "Errore imprevisto",
      });
    }
  }, []);

  const retry = useCallback(() => {
    if (requestRef.current) {
      void run(requestRef.current);
    }
  }, [run]);

  return { ...state, run, retry };
}
