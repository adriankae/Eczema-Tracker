# Zema

Zema is a self-hosted eczema treatment tracker with a FastAPI backend, PostgreSQL database, and a separate CLI/agent runtime.

It tracks subjects, body locations, eczema episodes, taper protocol phases, treatment applications, due reminders, event timelines, and adherence.

## What Zema Is

Zema is designed as two cooperating parts:

- `zema-be`: the backend API and system of record.
- `zema-cli`: a separate runtime image containing the `zema` CLI.

The backend owns all domain logic. The CLI is a client/tooling layer that calls backend HTTP APIs, parses responses, renders terminal output, emits JSON, and returns stable exit codes.

Use `zema` as the preferred CLI command. The older `czm` command remains available as a compatibility alias.

## Architecture

```text
User / Agent / Telegram / Hermes / OpenClaw
        |
        v
zema / czm CLI or zema-cli container
        |
        v
zema-be FastAPI backend
        |
        v
PostgreSQL
```

- `zema-be` is the FastAPI backend service.
- `zema-cli` is the CLI/agent runtime service.
- `postgres` is the canonical datastore.
- Docker Compose keeps the backend and CLI/agent runtime in separate services.
- The backend remains the source of truth for treatment, phase, due, and adherence logic.
- The CLI calls the backend over HTTP.
- Gateway code for Telegram, Hermes, OpenClaw, or similar tools should not run inside `zema-be`.

## Repository Layout

```text
app/                 Backend API, domain services, models, scheduler
alembic/             Database migrations
tests/               Backend tests
cli/                 Separate CLI package
cli/docs/            CLI-specific docs
cli/skills/          Agent Skills package
docker/              Backend and CLI Dockerfiles
docker-compose.yml   Local postgres, zema-be, and profiled zema-cli services
```

The CLI package is still named `czm-cli` and its internal Python package is still under `cli/src/czm_cli`. The public command name is `zema`, with `czm` kept as a compatibility alias.

## Features

- Account-scoped authentication with username/password login, JWT access tokens, and hashed API keys.
- Subject and body-location management.
- Eczema episode lifecycle tracking.
- Taper protocol phases with phase history.
- Treatment application logging, editing, voiding, deleting, and listing.
- Operational due reminders through `/episodes/due`.
- Event history and timelines.
- Daily adherence calculation and persisted audit snapshots.
- In-process scheduler for phase progression.
- Dockerized backend, PostgreSQL, and separate CLI/agent runtime.

Runtime requirements:

- Backend Python: `>=3.11,<4.0`
- CLI Python: `>=3.11`; package metadata lists Python 3.11 and 3.12 support
- Docker images: `python:3.11-slim`
- PostgreSQL required when running outside Docker

## Docker Quickstart

Build the images:

```bash
docker compose build
```

Start PostgreSQL and the backend:

```bash
docker compose up -d postgres zema-be
```

Check the services:

```bash
docker compose ps
docker compose logs --tail=100 zema-be
curl -sS http://localhost:28173/health
```

Expected health response:

```json
{"status":"ok"}
```

The backend is available at:

```text
http://localhost:28173
```

Run the CLI container:

```bash
docker compose run --rm zema-cli zema --help
```

Authenticated CLI container examples:

```bash
docker compose run --rm -e CZM_API_KEY="$CZM_API_KEY" zema-cli zema due list --json
docker compose run --rm -e CZM_API_KEY="$CZM_API_KEY" zema-cli zema adherence summary --last 30 --json
```

Inside Docker Compose, `zema-cli` uses:

```text
CZM_BASE_URL=http://zema-be:28173
```

## Authentication And API Keys

The local Docker Compose setup seeds a default account when the database is empty:

```text
username: admin
password: admin
```

Override these with:

```text
INITIAL_USERNAME
INITIAL_PASSWORD
```

Create an API key manually:

```bash
export CZM_BASE_URL="http://localhost:28173"

export ACCESS_TOKEN="$(
  curl -sS "$CZM_BASE_URL/auth/login" \
    -H 'Content-Type: application/json' \
    -d '{"username":"admin","password":"admin"}' \
  | jq -r '.access_token'
)"

export CZM_API_KEY="$(
  curl -sS "$CZM_BASE_URL/api-keys" \
    -H "Authorization: Bearer $ACCESS_TOKEN" \
    -H 'Content-Type: application/json' \
    -d '{"name":"zema-cli"}' \
  | jq -r '.plaintext_key'
)"
```

Verify the API key:

```bash
curl -sS "$CZM_BASE_URL/auth/me" \
  -H "X-API-Key: $CZM_API_KEY"
```

The CLI can also create its config automatically with `zema setup`:

```bash
zema setup \
  --username admin \
  --password admin \
  --api-key-name zema-cli \
  --timezone Europe/Berlin \
  --base-url http://localhost:28173
```

`zema setup` logs in, creates an API key, and writes a config file under `~/.config/czm/config.toml` or `$XDG_CONFIG_HOME/czm/config.toml`.

## CLI

Install the CLI from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e cli
zema --help
czm --help
zema adherence --help
```

If your pip index is unreachable, use PyPI explicitly:

```bash
PIP_INDEX_URL=https://pypi.org/simple python3 -m pip install -e cli
```

If `zema` is installed into a user bin directory that is not on `PATH`, activate the virtual environment or add the pip scripts directory shown by pip to your `PATH`.

CLI configuration precedence is:

```text
CLI flags > CZM_* environment variables > config file
```

The CLI uses these environment variables:

```text
CZM_BASE_URL
CZM_API_KEY
CZM_TIMEZONE
```

The default base URL is:

```text
http://localhost:28173
```

See the detailed CLI docs in [`cli/docs/`](cli/docs/).

## Common Workflows

After the backend is running and the CLI has an API key:

```bash
zema subject create --display-name "Child A"
zema location create --code left_elbow --display-name "Left elbow"
zema location image set left_elbow ./left-elbow.jpg
zema episode create --subject "Child A" --location left_elbow
zema application log --episode 1
zema due list
zema events list --episode 1
```

Notes:

- `zema application log --episode 1` records a minimal application.
- If omitted, `treatment_type` defaults to `other`.
- Optional application fields include `--applied-at`, `--treatment-type`, `--treatment-name`, `--quantity-text`, and `--notes`.
- Location images are optional and can be added during creation or later with `zema location image set`.
- Subject and location references may be numeric IDs or resolvable names/codes.

Location image examples:

```bash
zema location create --code left_elbow --display-name "Left elbow" --image ./left-elbow.jpg
zema location image set left_elbow ./left-elbow.jpg
zema location image get left_elbow --output ./left-elbow.jpg
zema location image remove left_elbow
```

## Adherence Tracking

Adherence is exposed through backend APIs and `zema adherence ...` commands.

Dynamic adherence:

- Is the default GET behavior.
- Is read-only.
- Is calculated live from phase history, taper protocol, and valid applications.
- Does not write rows.

Persisted adherence:

- Is stored in `episode_daily_adherence`.
- Is returned when `persisted=true` or `--persisted` is used.
- Reads stored rows only.
- May be empty before a rebuild has persisted snapshots.

Rebuild:

- `POST /adherence/rebuild` and `zema adherence rebuild` persist or update rows.
- CLI rebuild requires `--from` and `--to`.
- Rebuild without `episode_id` rebuilds active, non-obsolete episodes only.
- Broad all-episode rebuild with `active_only=false` is intentionally rejected in v1.

Schedule and scoring:

- Adherence snapshots use a fixed phase-start schedule for auditability.
- `/episodes/due` remains separate operational due/reminder logic.
- `completed_applications` is the raw valid logged application count for a day.
- `credited_applications = min(completed_applications, expected_applications)`.
- Score is `sum(credited_applications) / sum(expected_applications)`.
- If there are no expected applications, `adherence_score` is `null`.

Examples:

```bash
zema adherence summary --episode 1 --last 30 --json
zema adherence calendar --episode 1 --last 30
zema adherence missed --episode 1 --last 30 --include-partial
zema adherence rebuild --episode 1 --from 2026-04-01 --to 2026-04-30 --json
zema adherence summary --episode 1 --last 30 --persisted --json
```

## Backend API

Interactive FastAPI docs are available when the backend is running:

```text
http://localhost:28173/docs
```

Endpoint groups:

```text
GET /health

POST /auth/login
GET /auth/me

POST /api-keys
GET /api-keys
POST /api-keys/{api_key_id}/revoke

POST /subjects
GET /subjects
GET /subjects/{subject_id}

POST /locations
GET /locations
POST /locations/{location_id}/image
GET /locations/{location_id}/image
DELETE /locations/{location_id}/image

POST /episodes
GET /episodes
GET /episodes/{episode_id}
POST /episodes/{episode_id}/heal
POST /episodes/{episode_id}/relapse
POST /episodes/{episode_id}/advance
GET /episodes/due

POST /applications
PATCH /applications/{application_id}
DELETE /applications/{application_id}
POST /applications/{application_id}/void
GET /episodes/{episode_id}/applications

GET /episodes/{episode_id}/events
GET /episodes/{episode_id}/timeline

GET /adherence/calendar
GET /adherence/summary
GET /adherence/missed
GET /episodes/{episode_id}/adherence
POST /adherence/rebuild
```

Authenticated API requests can use either:

```text
Authorization: Bearer <jwt-access-token>
X-API-Key: <api-key>
```

## Local Development

Install backend dependencies from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Start dependencies with Docker:

```bash
docker compose up -d postgres
```

Run migrations:

```bash
python3 -m alembic upgrade head
```

Run the backend locally:

```bash
python3 -m app.server
```

For most local manual testing, the Docker Quickstart is simpler because it starts PostgreSQL and `zema-be` with the expected environment.

## Testing

Backend tests:

```bash
python3 -m pytest tests
python3 -m pytest tests/test_location_images.py
python3 -m pytest tests/test_adherence.py
python3 -m pytest tests/test_adherence_api.py
```

CLI tests:

```bash
python3 -m pytest cli/tests
python3 -m pytest cli/tests/test_adherence_cli.py
```

## Database Migrations

Run migrations manually:

```bash
python3 -m alembic upgrade head
```

The `zema-be` Docker image runs this automatically on startup:

```bash
alembic upgrade head && python -m app.server
```

Current migrations include the initial schema, `episode_daily_adherence`, and location image metadata.

## Configuration

Backend environment variables:

```text
DATABASE_URL
APP_ENV
DEPLOYMENT_TIMEZONE
APP_PORT
ENABLE_SCHEDULER
JWT_SECRET
INITIAL_USERNAME
INITIAL_PASSWORD
LOCATION_IMAGE_DIR
LOCATION_IMAGE_MAX_BYTES
```

Docker Compose defaults:

```text
DATABASE_URL=postgresql+psycopg://eczema:eczema@postgres:5432/eczema
APP_ENV=local
DEPLOYMENT_TIMEZONE=UTC
APP_PORT=28173
ENABLE_SCHEDULER=true
JWT_SECRET=change-me-in-production
INITIAL_USERNAME=admin
INITIAL_PASSWORD=admin
LOCATION_IMAGE_DIR=/data/location-images
LOCATION_IMAGE_MAX_BYTES=5242880
```

Location images are stored on the `zema-be` filesystem under `LOCATION_IMAGE_DIR`. Docker Compose mounts a named volume at `/data/location-images` so uploaded images survive container restarts.

CLI environment variables:

```text
CZM_BASE_URL
CZM_API_KEY
CZM_TIMEZONE
```

CLI config file locations:

```text
~/.config/czm/config.toml
$XDG_CONFIG_HOME/czm/config.toml
```

Example CLI config:

```toml
base_url = "http://localhost:28173"
api_key = "your-api-key"
timezone = "Europe/Berlin"
```

## Agent / Telegram / Hermes / OpenClaw Integration

Agent and gateway integrations should call `zema` or `czm` externally, or run the `zema-cli` container as a tool.

Recommended agent pattern:

```bash
zema --json due list
zema --json adherence summary --last 30
zema --json application log --episode 1
```

Do not place Telegram, Hermes, OpenClaw, or other gateway code inside the `zema-be` backend image. Keep the backend focused on API, persistence, and domain logic.

The repository includes an Agent Skills package under:

```text
cli/skills/czm/
```

## Troubleshooting

`python` not found:

```bash
python3 --version
```

Pip index problems:

```bash
PIP_INDEX_URL=https://pypi.org/simple python3 -m pip install -e cli
```

`zema` not on `PATH`:

```bash
source .venv/bin/activate
.venv/bin/zema --help
```

Port `28173` already in use:

```bash
lsof -i :28173
```

Docker buildx warning:

- Docker Compose may warn that buildx is not installed.
- If the image still builds, you can continue.
- If builds fail, update Docker Desktop or install the buildx plugin.

Backend not ready:

```bash
docker compose ps
docker compose logs --tail=100 zema-be
curl -sS http://localhost:28173/health
```

Missing or invalid `CZM_API_KEY`:

- Run `zema setup`, or recreate an API key through `/auth/login` and `/api-keys`.
- Remember that the CLI uses `X-API-Key`, not the JWT bearer token.

Persisted adherence is empty:

- This is expected before `zema adherence rebuild`.
- Dynamic adherence remains available without persisted rows.

No adherence rows:

- Requested dates must be covered by episode phase history.
- A newly created episode usually has phase history starting on its creation date.

Wrong checkout:

```bash
test -d cli && test -f app/adherence.py && test -f docker/api.Dockerfile && test -f docker/cli.Dockerfile && echo "integrated checkout"
```

## Security Notes

- Change the default `admin/admin` credentials.
- Change `JWT_SECRET`.
- Do not commit API keys.
- Do not bake secrets into Docker images.
- Use environment variables or secret management for deployments.
- Do not expose `zema-be` publicly without TLS, authentication, and reverse-proxy hardening.

## Versioning / Changelog

The backend package version is tracked in `pyproject.toml`.

The CLI package is separate under `cli/pyproject.toml`.

See [`CHANGELOG.md`](CHANGELOG.md) for release notes.

## Roadmap / Non-Goals

- Telegram, Hermes, and OpenClaw gateway code is not included inside `zema-be`.
- The CLI does not own or duplicate business logic.
- The internal Python package rename from `czm_cli` to `zema` has not been done.
- `/episodes/due` is operational reminder logic, not historical adherence auditing.
- The project intentionally avoids GraphQL, Celery, Kafka, external workers, CQRS, and event sourcing.
