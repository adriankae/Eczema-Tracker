# Eczema Treatment Tracker

Self-hosted eczema episode tracking backend for local Docker deployment.

## What is included

- FastAPI JSON API
- PostgreSQL schema via Alembic
- username/password login
- bearer JWT auth
- API key auth
- subjects, locations, episodes, applications, due view, events
- in-process background scheduler for phase progression
- automated tests

## Default bootstrap account

On first startup, the app seeds a default account if none exists:

- username: `admin`
- password: `admin`

Override it with environment variables:

- `INITIAL_USERNAME`
- `INITIAL_PASSWORD`

## Run with Docker

```bash
docker compose up --build
```

The API container creates and uses its own Python virtual environment during the image build, so the Docker run path does not use system `pip`.

API:

- `http://localhost:8000`

Postgres:

- `localhost:5432`

## Local development

Create and activate a Python virtual environment first:

```bash
python3 -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/uvicorn app.main:app --reload
```

If you see a warning about running `pip` as root, stop and make sure the `.venv` is activated. You should not need `sudo` for any local development command.

## Migrations

Apply migrations with Alembic:

```bash
.venv/bin/alembic upgrade head
```

## Tests

```bash
.venv/bin/pytest
```

## API highlights

- `POST /auth/login`
- `POST /subjects`
- `GET /subjects`
- `GET /subjects/{subject_id}`
- `POST /locations`
- `GET /locations`
- `POST /episodes`
- `GET /episodes`
- `GET /episodes/{episode_id}`
- `POST /episodes/{episode_id}/heal`
- `POST /episodes/{episode_id}/relapse`
- `POST /episodes/{episode_id}/advance`
- `POST /applications`
- `PATCH /applications/{application_id}`
- `DELETE /applications/{application_id}`
- `POST /applications/{application_id}/void`
- `GET /episodes/{episode_id}/applications`
- `GET /episodes/{episode_id}/events`
- `GET /episodes/{episode_id}/timeline`
- `GET /episodes/due`
