# Eczema Treatment Tracker

Self-hosted eczema episode tracking backend for one authenticated account, multiple subjects, account-owned body locations, and calendar-day-based taper progression.

## Table Of Contents

- [About](#about)
- [Release 0.1](#release-01)
- [Features](#features)
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

## Quick Start

### With Docker

```bash
docker compose up --build
```

The API container builds and uses its own Python virtual environment internally, so it does not rely on system `pip` during image build.

After startup:

- API: `http://localhost:8000`
- PostgreSQL: `localhost:5432`

### Health check

```bash
curl http://localhost:8000/health
```

### Login

```bash
curl -s http://localhost:8000/auth/login \
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

### Auth

- `POST /auth/login`
- `GET /auth/me`

### API Keys

- `POST /api-keys`
- `GET /api-keys`
- `POST /api-keys/{api_key_id}/revoke`

### Subjects

- `POST /subjects`
- `GET /subjects`
- `GET /subjects/{subject_id}`

### Locations

- `POST /locations`
- `GET /locations`

### Episodes

- `POST /episodes`
- `GET /episodes`
- `GET /episodes/{episode_id}`
- `POST /episodes/{episode_id}/heal`
- `POST /episodes/{episode_id}/relapse`
- `POST /episodes/{episode_id}/advance`

### Applications

- `POST /applications`
- `PATCH /applications/{application_id}`
- `DELETE /applications/{application_id}`
- `POST /applications/{application_id}/void`
- `GET /episodes/{episode_id}/applications`

### Events and Timeline

- `GET /episodes/{episode_id}/events`
- `GET /episodes/{episode_id}/timeline`

### Due View

- `GET /episodes/due`

### Authentication headers

Bearer token:

```bash
Authorization: Bearer <token>
```

API key:

```bash
X-API-Key: <api_key>
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
.venv/bin/uvicorn app.main:app --reload
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
