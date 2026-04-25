# CZM CLI Specification (v1.1, Codex-Ready)

## 0. Purpose

This document defines a **fully deterministic, agent-first CLI** for the Eczema Tracker backend.

This spec is **implementation-complete**:

* no ambiguous behavior
* no implicit contracts
* all commands, schemas, and endpoints defined
* suitable for **one-pass implementation by Codex**

---

## 1. Core Principles

* CLI is a **stateless HTTP client**
* Backend is **single source of truth**
* CLI performs:

  * input normalization
  * entity resolution
  * deterministic output formatting

---

## 2. Implementation Targets

### 2.1 Language & Stack

* Python ≥ 3.12
* `typer` (CLI)
* `httpx` (HTTP client)
* `pydantic` (schemas)
* `rich` (optional human output)

### 2.2 Packaging

```text
package name: czm_cli
executable: czm
```

### 2.3 Repo Layout

```text
czm-cli/
  pyproject.toml
  czm_cli/
    __init__.py
    main.py
    config.py
    client.py
    errors.py
    resolution.py
    schemas.py
    commands/
      subject.py
      location.py
      episode.py
      application.py
      due.py
      events.py
  tests/
  README.md
```

### 2.4 Tooling

| Tool   | Purpose     |
| ------ | ----------- |
| pytest | tests       |
| mypy   | typing      |
| ruff   | lint/format |

---

## 3. Configuration

### 3.1 Location

```bash
~/.config/czm/config.toml
```

### 3.2 Precedence

```text
CLI flag > ENV > config file
```

### 3.3 Config schema

```toml
base_url = "https://api.example.com"
api_key = "sk-..."
timezone = "Europe/Berlin"
```

---

## 4. Authentication

* API key only

```http
Authorization: Bearer <API_KEY>
```

---

## 5. JSON Contract (STRICT)

### 5.1 Success (ALL commands)

```json
{
  "data": <payload>,
  "meta": {
    "request_id": "string",
    "timestamp": "ISO8601"
  }
}
```

### 5.2 Error

```json
{
  "error": {
    "code": "string",
    "message": "string",
    "details": {}
  }
}
```

### 5.3 Exit Codes

| Code | Meaning    |
| ---- | ---------- |
| 0    | success    |
| 2    | validation |
| 3    | not found  |
| 4    | ambiguity  |
| 5    | auth       |
| 6    | API error  |

---

## 6. Entity Resolution (STRICT)

### 6.1 Matching priority

1. exact match
2. case-insensitive match
3. substring match

### 6.2 Scope

* always account-scoped

### 6.3 Episode resolution

When using:

```text
--subject + --location
```

Resolution:

```text
1. fetch all episodes for subject+location
2. if none → NOT_FOUND
3. if one active episode → use it
4. if multiple active → AMBIGUOUS
5. else → use most recent episode (any state: healed/tapering/obsolete)
```

### 6.4 Ambiguity response

```json
{
  "error": {
    "code": "ambiguous",
    "details": {
      "candidates": [...]
    }
  }
}
```

---

## 7. Time Handling

* input: local or ISO
* convert → UTC
* output JSON: UTC only

---

## 8. Schemas

### 8.1 Subject

```json
{
  "id": "string",
  "display_name": "string",
  "created_at": "ISO8601"
}
```

### 8.2 Location

```json
{
  "id": "string",
  "code": "string",
  "display_name": "string"
}
```

### 8.3 Episode

```json
{
  "id": "string",
  "subject_id": "string",
  "location_id": "string",
  "state": "active_flare|healed|phase_2|...|phase_7|obsolete",
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

### 8.4 Application

```json
{
  "id": "string",
  "episode_id": "string",
  "product": "string",
  "amount": "string",
  "applied_at": "ISO8601"
}
```

### 8.5 Due

```json
{
  "episode_id": "string",
  "due_at": "ISO8601"
}
```

### 8.6 Event

```json
{
  "id": "string",
  "type": "string",
  "timestamp": "ISO8601",
  "payload": {}
}
```

---

## 9. Command → Endpoint Mapping

| CLI                | Method | Endpoint               |
| ------------------ | ------ | ---------------------- |
| subject create     | POST   | /subjects              |
| subject list       | GET    | /subjects              |
| subject get        | GET    | /subjects/{id}         |
| location create    | POST   | /locations             |
| location list      | GET    | /locations             |
| episode create     | POST   | /episodes              |
| episode list       | GET    | /episodes              |
| episode get        | GET    | /episodes/{id}         |
| episode heal       | POST   | /episodes/{id}/heal    |
| episode relapse    | POST   | /episodes/{id}/relapse |
| application log    | POST   | /applications          |
| application update | PATCH  | /applications/{id}     |
| application delete | DELETE | /applications/{id}     |
| application list   | GET    | /applications          |
| due list           | GET    | /due                   |
| events list        | GET    | /events                |

---

## 10. Commands (FULL SPEC)

## 10.1 subject create

```bash
czm subject create --name "Child A"
```

Request:

```json
{ "display_name": "Child A" }
```

Response:

```json
{
  "data": {
    "id": "sub_1",
    "display_name": "Child A",
    "created_at": "..."
  },
  "meta": {}
}
```

---

## 10.2 subject list

```bash
czm subject list
```

Query params:

* limit (default 50)
* cursor

Response:

```json
{
  "data": [Subject],
  "meta": { "cursor": "..." }
}
```

---

## 10.3 subject get

```bash
czm subject get --subject "Child A"
```

---

## 10.4 location create

```bash
czm location create --code left_elbow --name "Left Elbow"
```

---

## 10.5 location list

```bash
czm location list
```

---

## 10.6 episode create

```bash
czm episode create --subject "Child A" --location left_elbow
```

Request:

```json
{
  "subject_id": "...",
  "location_id": "..."
}
```

---

## 10.7 episode list

```bash
czm episode list --subject "Child A"
```

Filters:

* subject
* location

---

## 10.8 episode get

```bash
czm episode get --subject "Child A" --location left_elbow
```

---

## 10.9 episode heal

```bash
czm episode heal --subject "Child A" --location left_elbow
```

---

## 10.10 episode relapse

```bash
czm episode relapse --subject "Child A" --location left_elbow
```

---

## 10.11 application log

```bash
czm application log \
  --subject "Child A" \
  --location left_elbow \
  --product "Steroid" \
  --amount "thin"
```

---

## 10.12 application update

```bash
czm application update --id app_1 --amount "thick"
```

---

## 10.13 application delete

```bash
czm application delete --id app_1
```

---

## 10.14 application list

```bash
czm application list --subject "Child A"
```

---

## 10.15 due list

```bash
czm due list
```

---

## 10.16 events list

```bash
czm events list
```

---

## 11. Defaults & Behavior

### 11.1 List commands

* default limit: 50
* sorted: newest first

### 11.2 Output modes

| Flag    | Behavior    |
| ------- | ----------- |
| --json  | strict JSON |
| --quiet | no output   |

---

## 12. Agent Contract (SKILL.md)

### Rules

* ALWAYS use `--json`
* NEVER parse human output
* ALWAYS resolve ambiguity
* NEVER assume IDs

---

## 13. Workflow Library

### Daily loop

```bash
czm due list --json
→ iterate → application log
```

---

## 14. Test Requirements

* resolution logic
* ambiguity
* endpoint mapping
* JSON schema
* exit codes

---

## END
