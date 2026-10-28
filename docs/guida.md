# TransportFinder user guide

TransportFinder compares live train and intercity coach options for a route and date. It can also propose train-and-bus combinations that are not sold as a single ticket. Flight search is not currently included.

## Running the application

For local development, start the backend on `http://localhost:10022` and the frontend on `http://localhost:3356`. The backend health endpoint is `http://localhost:10022/health`.

See the [root README](../README.md) for installation instructions and the generic Docker Compose command.

## Search a route

1. Enter an origin, destination, and date.
2. Select **Search**.
3. Compare the listed options by mode, schedule, duration, changes, and price.
4. Use the carrier link to purchase a selected option.

You can limit results by transport mode, sort by departure, duration, or price, and set a maximum number of changes. Enable mixed itineraries to include a train leg followed by a coach leg, with the connection time shown in the result.

## Command line

From `backend/`, run:

```bash
.venv/bin/python -m transportfinder_backend.cli Perugia Udine 2026-11-03 --combine --sort price
```

Useful options include `--max-changes N`, `--sort price|duration|departure`, and `--json`.

## API

Send a `POST` request to `/api/search`:

```json
{"origin":"Perugia","destination":"Roma","day":"2026-11-03","modes":["train","bus"],"combine":false,"sort":"departure"}
```

The service queries carriers live. If one carrier is temporarily unavailable, results from the other carriers remain available. Fares may change between a search and checkout.
