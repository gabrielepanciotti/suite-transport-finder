# TransportFinder

TransportFinder is an open-source travel transport finder that searches live intercity rail and coach options and can combine train and bus legs into itineraries that individual carriers do not sell together.

## Features

- Search Trenitalia, FlixBus, and Itabus through their public endpoints.
- Compare departure times, durations, changes, and prices.
- Build mixed train-and-bus itineraries through suitable interchange hubs.
- Use the service from a FastAPI API, a React interface, or the `tfind` command-line tool.

## Requirements

- Python 3.13 (or a compatible supported Python version)
- Node.js 20 and npm
- Docker and Docker Compose for the containerized setup
- The [Life framework](https://github.com/suite-life) checked out next to this repository; it provides the shared `suite_*` packages.

## Quickstart

```bash
git clone <your-fork-url> transport-finder
git clone https://github.com/suite-life Life
cd transport-finder
cp .env.example .env

# The Life framework is the sibling directory named Life.

# Backend
python3.13 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements-dev.txt \
  ../Life/packages/shared ../Life/packages/backend-core
cd backend && .venv/bin/uvicorn transportfinder_backend.app:app --reload --port 10022

# In another terminal, frontend
cd frontend
npm ci
npm run dev
```

Alternatively, build and run the generic Docker setup with `docker compose --env-file .env -f deploy/docker-compose.example.yml up --build`. The project’s private production compose files are intentionally not part of a public release.

## Tests

Run backend tests with `cd backend && .venv/bin/python -m pytest -q`. Run frontend tests with `cd frontend && npm test -- --pool=forks --poolOptions.forks.maxForks=2`, then build with `npm run build`. CI checks out the Life framework as a sibling using the `LIFE_FRAMEWORK_REPO` repository variable (default: `suite-life`).

## Configuration

| Variable | Purpose |
| --- | --- |
| `DB_PASSWORD` | Password used by the local PostgreSQL service. |
| `DB_HOST_PORT` | Host port exposed by the local PostgreSQL service. |
| `DATABASE_URL` | Backend database connection URL. |
| `VITE_BACKEND_PROXY_TARGET` | Frontend development proxy target. |
| `LIFE_FRAMEWORK_DIR` | Optional path to a local Life framework checkout for container builds. |

## License

MIT — see [LICENSE](LICENSE).
