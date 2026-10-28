"""``tfind`` — compare trains and coaches on one route from the terminal.

Agent-native by design: a single command returns every option across providers, already
ranked, either as a table for a human or as JSON for another tool.

    python -m transportfinder_backend.cli Perugia Udine 2026-09-13
    python -m transportfinder_backend.cli Perugia Udine 2026-09-13 --sort price --json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime

from .providers import PROVIDERS, combine
from .search import SORTS, collect, dedupe, journey_to_dict, search  # noqa: F401


def render_table(journeys: list) -> str:
    header = f"{'':2} {'partenza':>8}  {'arrivo':>8}  {'durata':>7}  {'cambi':>5}  {'prezzo':>8}  percorso"
    rows = [header, "-" * len(header)]
    for j in journeys:
        icon = {"train": "🚆", "bus": "🚌"}.get(j.mode, "🔀")
        price = f"{j.price:.2f}" if j.price is not None else "n.d."
        breakdown = getattr(j, "price_breakdown", None)
        if breakdown:
            price = f"{price} ({breakdown})"
        overnight = "+1" if j.arrival.date() > j.departure.date() else "  "
        rows.append(
            f"{icon} {j.departure:%H:%M}{'':>3} {j.arrival:%H:%M}{overnight}{'':>1} "
            f"{j.duration_hhmm:>7}  {j.changes:>5}  {price:>8}  {' + '.join(j.legs)}"
        )
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    # Windows consoles still default to cp1252, which cannot render the arrows and icons.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        prog="tfind", description="Confronta treni e pullman su una tratta."
    )
    parser.add_argument("origin", help="città o stazione di partenza")
    parser.add_argument("destination", help="città o stazione di arrivo")
    parser.add_argument("day", help="data di viaggio, YYYY-MM-DD")
    parser.add_argument(
        "--modes",
        default="train,bus",
        help="mezzi da interrogare, separati da virgola (default: train,bus)",
    )
    parser.add_argument("--from-time", default="05:00", help="non prima di questo orario (HH:MM)")
    parser.add_argument("--sort", choices=sorted(SORTS), default="departure")
    parser.add_argument(
        "--max-changes", type=int, default=None, help="scarta le soluzioni con più cambi di N"
    )
    parser.add_argument(
        "--combine",
        action="store_true",
        help="costruisci anche itinerari misti treno+bus via un hub intermedio",
    )
    parser.add_argument(
        "--via",
        default=",".join(combine.DEFAULT_HUBS),
        help="hub da provare con --combine, separati da virgola",
    )
    parser.add_argument("--max", type=int, default=0, help="mostra al massimo N risultati")
    parser.add_argument("--json", action="store_true", help="output JSON invece della tabella")
    parser.add_argument("--links", action="store_true", help="stampa i link di acquisto")
    args = parser.parse_args(argv)

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    unknown = [m for m in modes if m not in PROVIDERS]
    if unknown:
        parser.error(f"mezzi sconosciuti: {', '.join(unknown)} (disponibili: {', '.join(PROVIDERS)})")

    day = date.fromisoformat(args.day)
    from_time = datetime.strptime(args.from_time, "%H:%M").time()
    hubs = [h.strip() for h in args.via.split(",") if h.strip()]

    result = search(
        args.origin,
        args.destination,
        day,
        modes=modes,
        from_time=from_time,
        sort=args.sort,
        max_changes=args.max_changes,
        combine=args.combine,
        via=hubs,
        max_results=args.max,
    )
    journeys, errors = result.journeys, result.errors

    if args.json:
        payload = {
            "origin": result.origin,
            "destination": result.destination,
            "date": result.date.isoformat(),
            "errors": result.errors,
            "journeys": [journey_to_dict(j) for j in result.journeys],
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"{args.origin} → {args.destination}, {day:%a %d/%m/%Y} — {len(journeys)} opzioni\n")
        print(render_table(journeys) if journeys else "Nessuna opzione trovata.")
        if args.links:
            print()
            for i, j in enumerate(journeys, 1):
                print(f"{i}. {j.departure:%H:%M} → {j.arrival:%H:%M}  {j.deeplink or '—'}")
        for err in errors:
            print(f"\n⚠️  {err}", file=sys.stderr)
    return 0 if journeys else 1


if __name__ == "__main__":
    raise SystemExit(main())
