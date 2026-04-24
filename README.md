# Eczema Treatment Tracker

Self-hosted eczema episode tracking backend for one authenticated account, multiple subjects, account-owned body locations, and calendar-day-based taper progression.

## Table Of Contents

- [About](#about)
- [Release 0.1](#release-01)
- [Features](#features)
- [Runtime Requirements](#runtime-requirements)
- [Quick Start](#quick-start)
- [Getting Started](#getting-started)
- [API Documentation](#api-documentation)
- [Data Model](#data-model)
- [Development](#development)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## About

This project provides a production-ready v1 backend for tracking eczema treatment episodes. It is built with:

- FastAPI
- PostgreSQL
- SQLAlchemy 2.x
- Alembic migrations
- Pydantic models
- an in-process scheduler

The system is designed to stay simple and self-hostable while leaving room for a future CLI or agent client.

## Release 0.1

Version `0.1.0` is the first release of the backend and includes:

- authentication with username/password and JWT bearer tokens
- API keys for programmatic access
- account-scoped subjects and body locations
- eczema episode lifecycle management
- treatment application tracking
- event logging and episode timelines
- due calculations
- automatic phase progression
- Dockerized local deployment
- automated tests

## Features

### Authentication

- username/password login
- JWT bearer tokens
- API key support for service and CLI usage

### Core domain

- create and manage subjects
- create and manage body locations
- create episodes for a subject + location pair
- mark healed, relapse, and advance phases
- log, edit, void, and delete applications
- list events and timeline history
- view due episodes

### Automation

- background scheduler inside the API container
- daily phase evaluation at deployment local `00:05`
- automatic advancement from phases 2 through 7
- automatic obsoletion after phase 7

### Deployment

- Dockerfile for the API
- Docker Compose with API + PostgreSQL
- Alembic migration at container startup

## Runtime Requirements

This project targets Python 3.11.

Required:

- Python >=3.11,<4.0
- Docker / Docker Compose for containerized deployment
- PostgreSQL, if running outside Docker

The Docker image uses `python:3.11-slim`.

## Quick Start

### With Docker

```bash
docker compose up --build
```

The API container builds and uses its own Python virtual environment internally, so it does not rely on system `pip` during image build.

After startup:

- API: `http://localhost:28173`
- PostgreSQL: `localhost:5432`

### Health check

```bash
curl http://localhost:28173/health
```

### Login

```bash
curl -s http://localhost:28173/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}'
```

## Getting Started

### 1. Clone the repository

```bash
git clone git@eczema-tracker:adriankae/Eczema-Tracker.git
cd Eczema-Tracker
```

### 2. Start the stack

```bash
docker compose up --build
```

### 3. Log in

The first startup seeds a default account if the database is empty:

- username: `admin`
- password: `admin`

Override these with environment variables:

- `INITIAL_USERNAME`
- `INITIAL_PASSWORD`

### 4. Create your first data

Use the authenticated API to create:

1. a subject
2. a body location
3. an episode
4. treatment applications

### 5. Watch phase progression

When an episode is marked healed:

- it enters phase 2 immediately
- the scheduler later advances it through phases 3 to 7
- after phase 7 completes, the episode becomes obsolete

## API Documentation

All endpoints require authentication unless noted otherwise.

### Authentication headers

Use one of these headers for authenticated requests.

Bearer token:

```bash
Authorization: Bearer <token>
```

API key:

```bash
X-API-Key: <api_key>
```

### `POST /auth/login`

Logs a user in with username and password and returns a bearer token.

Mandatory fields:

- `username`
- `password`

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin"}'
```

### `GET /auth/me`

Returns the currently authenticated account.

Mandatory fields:

- none

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api-keys`

Creates a new API key for the authenticated account and returns the plaintext key once.

Mandatory fields:

- `name`

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"cli"}'
```

### `GET /api-keys`

Lists API keys for the authenticated account.

Mandatory fields:

- none

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/api-keys \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /api-keys/{api_key_id}/revoke`

Marks an API key inactive.

Mandatory fields:

- `api_key_id` path parameter

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/api-keys/1/revoke \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /subjects`

Creates a subject for the authenticated account.

Mandatory fields:

- `display_name`

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/subjects \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"display_name":"Child"}'
```

### `GET /subjects`

Lists the authenticated account’s subjects.

Mandatory fields:

- none

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/subjects \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /subjects/{subject_id}`

Returns one subject by id.

Mandatory fields:

- `subject_id` path parameter

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/subjects/1 \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /locations`

Creates a body location owned by the authenticated account.

Mandatory fields:

- `code`
- `display_name`

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/locations \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"code":"left_elbow","display_name":"Left elbow"}'
```

### `GET /locations`

Lists the authenticated account’s body locations.

Mandatory fields:

- none

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/locations \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /episodes`

Creates a new eczema episode for a subject/location pair.

Mandatory fields:

- `subject_id`
- `location_id`

Optional fields:

- `protocol_version` defaults to `v1`

Example request:

```bash
curl -s http://localhost:28173/episodes \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"subject_id":1,"location_id":1,"protocol_version":"v1"}'
```

### `GET /episodes`

Lists episodes for the authenticated account.

Mandatory fields:

- none

Optional fields:

- `subject_id`
- `status`

Example request:

```bash
curl -s "http://localhost:28173/episodes?subject_id=1&status=active_flare" \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /episodes/{episode_id}`

Returns one episode by id.

Mandatory fields:

- `episode_id` path parameter

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/episodes/1 \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /episodes/{episode_id}/heal`

Marks an episode as healed and moves it into phase 2 immediately.

Mandatory fields:

- `episode_id` path parameter

Optional fields:

- `healed_at` defaults to now

Example request:

```bash
curl -s http://localhost:28173/episodes/1/heal \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"healed_at":"2026-04-05T18:00:00Z"}'
```

### `POST /episodes/{episode_id}/relapse`

Resets a tapering episode back to phase 1.

Mandatory fields:

- `episode_id` path parameter
- `reason`

Optional fields:

- `reported_at` defaults to now

Example request:

```bash
curl -s http://localhost:28173/episodes/1/relapse \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"reported_at":"2026-04-06T18:00:00Z","reason":"symptoms_returned"}'
```

### `POST /episodes/{episode_id}/advance`

Manually advances a tapering episode one step, or marks it obsolete after phase 7.

Mandatory fields:

- `episode_id` path parameter

Optional fields:

- request body may be empty

Example request:

```bash
curl -s http://localhost:28173/episodes/1/advance \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{}'
```

### `POST /applications`

Logs a treatment application for an episode.

Mandatory fields:

- `episode_id`
- `treatment_type`

Optional fields:

- `applied_at` defaults to now
- `treatment_name`
- `quantity_text`
- `notes`

Example request:

```bash
curl -s http://localhost:28173/applications \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "episode_id":1,
    "applied_at":"2026-04-06T07:30:00Z",
    "treatment_type":"steroid",
    "treatment_name":"Hydrocortisone 1%",
    "quantity_text":"thin layer",
    "notes":"morning dose"
  }'
```

### `PATCH /applications/{application_id}`

Edits an existing application.

Mandatory fields:

- `application_id` path parameter

Optional fields:

- `applied_at`
- `treatment_type`
- `treatment_name`
- `quantity_text`
- `notes`

Example request:

```bash
curl -s -X PATCH http://localhost:28173/applications/1 \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"notes":"updated note"}'
```

### `DELETE /applications/{application_id}`

Soft-deletes an application.

Mandatory fields:

- `application_id` path parameter

Optional fields:

- none

Example request:

```bash
curl -s -X DELETE http://localhost:28173/applications/1 \
  -H "Authorization: Bearer $TOKEN"
```

### `POST /applications/{application_id}/void`

Voids an application without deleting it.

Mandatory fields:

- `application_id` path parameter
- `reason`

Optional fields:

- `voided_at` defaults to now

Example request:

```bash
curl -s http://localhost:28173/applications/1/void \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"voided_at":"2026-04-06T08:00:00Z","reason":"logged_by_mistake"}'
```

### `GET /episodes/{episode_id}/applications`

Lists applications for one episode.

Mandatory fields:

- `episode_id` path parameter

Optional fields:

- `include_voided` defaults to `false`

Example request:

```bash
curl -s "http://localhost:28173/episodes/1/applications?include_voided=true" \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /episodes/{episode_id}/events`

Lists raw events for one episode.

Mandatory fields:

- `episode_id` path parameter

Optional fields:

- `event_type`

Example request:

```bash
curl -s "http://localhost:28173/episodes/1/events?event_type=application_logged" \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /episodes/{episode_id}/timeline`

Returns the chronological timeline for one episode.

Mandatory fields:

- `episode_id` path parameter

Optional fields:

- none

Example request:

```bash
curl -s http://localhost:28173/episodes/1/timeline \
  -H "Authorization: Bearer $TOKEN"
```

### `GET /episodes/due`

Returns the episodes that are due today.

Mandatory fields:

- none

Optional fields:

- `subject_id`

Example request:

```bash
curl -s "http://localhost:28173/episodes/due?subject_id=1" \
  -H "Authorization: Bearer $TOKEN"
```

## Data Model

The database includes:

- `accounts`
- `account_api_keys`
- `subjects`
- `body_locations`
- `eczema_episodes`
- `taper_protocol_phases`
- `episode_phase_history`
- `treatment_applications`
- `episode_events`

## Development

### Python virtual environment

Create and activate a local venv:

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

### Run locally

```bash
.venv/bin/python -m app.server
```

### Migrations

```bash
.venv/bin/alembic upgrade head
```

### Tests

```bash
.venv/bin/pytest -q
```

## Testing

The test suite covers:

- authentication
- API key access
- subjects and locations
- episode lifecycle
- scheduler behavior
- application CRUD and due logic
- event emission
- account scoping

## Troubleshooting

### Docker Compose prints a buildx warning

This is a Docker tooling warning, not an application error. The stack can still build and run.

### PostgreSQL shows a locale warning

That is normal for the Alpine Postgres image and does not stop the database from starting.

### API container exits during startup

Check the logs:

```bash
docker compose logs api
docker compose logs postgres
```

### Database reset

If you want a fresh database:

```bash
docker compose down -v
```

## Contributing

The codebase is intentionally small and conventional. If you extend it later, keep the same principles:

- preserve account scoping
- keep calendar-day semantics
- keep the scheduler in-process
- keep migrations explicit

## License

See the repository license, if present.
