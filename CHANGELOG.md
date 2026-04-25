# Changelog

## 0.1.3

### Added

- Imported the CLI package under `cli/` while preserving it as a separate Python package.
- Added `zema` as the preferred CLI executable and kept `czm` as a compatibility alias.
- Added a separate `zema-cli` Docker runtime for CLI, tooling, and agent usage.
- Added persisted daily adherence snapshots via `episode_daily_adherence`.
- Added backend adherence calculation and rebuild services.
- Added adherence API endpoints for calendar, summary, missed days, per-episode adherence, and rebuild workflows.
- Added `zema adherence` CLI commands for calendar, summary, missed days, per-episode views, and rebuild workflows.
- Added a dedicated `docker/api.Dockerfile` for the backend image while preserving the root Dockerfile.

### Changed

- Docker Compose now separates the backend API runtime (`zema-be`) from the CLI/agent runtime (`zema-cli`).
- Backend remains the source of truth for adherence calculations; the CLI only calls backend APIs.
- GET adherence endpoints default to dynamic read-only calculation; `persisted=true` reads stored audit snapshots.

### Notes

- Existing `/episodes/due` behavior is unchanged.
- Adherence snapshots use a fixed protocol schedule anchored to each phase start date.
- Extra applications are capped via `credited_applications` and do not inflate adherence score.
- No Telegram/Hermes/OpenClaw gateway code is included in the backend image.

## 0.1.2

### Changed

- Changed the supported Python runtime target to Python >=3.11,<4.0.
- Updated the container base image to `python:3.11-slim`.
- Added a dedicated Runtime Requirements section to the README.

### Notes

- This release does not intentionally change the API, authentication behavior, database schema, or treatment data model.
