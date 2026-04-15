# API Contract Specification

Version: 1.0
Status: Normative
Scope: Eczema Treatment Tracker backend API
Style: Simple first version

---

## 1. Purpose

This document defines the API contract for the first version of the Eczema Treatment Tracker.

The API is designed to:

* support a self-hosted backend
* provide a clean interface for CLI clients
* provide a stable interface for future agent integration
* expose the core domain operations only
* stay simple for the first version

This is a **REST-style JSON API**.

---

## 2. API Design Principles

The first version follows these principles:

1. **Keep the API small**

   * only expose the endpoints needed for core episode tracking

2. **Keep payloads explicit**

   * use simple request and response bodies
   * avoid hidden behavior

3. **Prefer server-controlled state transitions**

   * clients request domain actions
   * server applies business rules

4. **Return structured JSON**

   * every successful response returns JSON
   * every error response returns JSON

5. **Do not over-engineer v1**

   * no pagination unless actually needed
   * no advanced filtering DSL
   * no versioned public media types
   * no GraphQL
   * no event-sourcing API surface

---

## 3. Base URL

Example:

```text
http://localhost:28173
```

All routes below are relative to the API root.

---

## 4. Content Type

Requests with JSON bodies must use:

```text
Content-Type: application/json
```

Responses use:

```text
Content-Type: application/json
```

---

## 5. Authentication

For v1, keep authentication simple.

Recommended v1 approach:

* authenticated API using a bearer token
* CLI stores token locally
* agent may also use bearer token

Request header:

```text
Authorization: Bearer <token>
```

If authentication is not yet implemented in the first coding pass, the backend may temporarily run without auth in local development only.
However, the contract should be written with authentication in mind.

---

## 6. Time Format

All timestamps must use ISO 8601 with timezone.

Example:

```text
2026-04-15T08:00:00Z
```

All server timestamps in responses must be timezone-aware.

---

## 7. General Response Style

### 7.1 Success responses

Success responses return JSON objects.

### 7.2 Error responses

All error responses must return this shape:

```json
{
  "error": {
    "code": "string_code",
    "message": "Human-readable explanation"
  }
}
```

Optional extra fields may be added later, but v1 should keep this simple.

Example:

```json
{
  "error": {
    "code": "episode_not_found",
    "message": "Episode 42 was not found."
  }
}
```

---

## 8. Resource Overview

The first version should expose these core resources and actions:

* locations
* episodes
* applications
* events / timeline
* due view

---

## 9. Data Shapes

The API uses the following core response shapes.

## 9.1 Location object

```json
{
  "id": 12,
  "code": "left_elbow",
  "display_name": "Left elbow",
  "created_at": "2026-04-01T09:00:00Z"
}
```

### Fields

| Field          | Type            | Required | Meaning              |
| -------------- | --------------- | -------: | -------------------- |
| `id`           | integer         |      yes | location id          |
| `code`         | string          |      yes | stable location code |
| `display_name` | string          |      yes | human-readable name  |
| `created_at`   | datetime string |      yes | creation timestamp   |

---

## 9.2 Episode object

```json
{
  "id": 42,
  "subject_id": 7,
  "location_id": 12,
  "status": "active_flare",
  "current_phase_number": 1,
  "phase_started_at": "2026-04-01T09:00:00Z",
  "phase_due_end_at": null,
  "protocol_version": "v1",
  "healed_at": null,
  "obsolete_at": null,
  "created_at": "2026-04-01T09:00:00Z",
  "updated_at": "2026-04-01T09:00:00Z"
}
```

### Fields

| Field                  | Type                    | Required | Meaning                |
| ---------------------- | ----------------------- | -------: | ---------------------- |
| `id`                   | integer                 |      yes | episode id             |
| `subject_id`           | integer                 |      yes | tracked person id      |
| `location_id`          | integer                 |      yes | body location id       |
| `status`               | string                  |      yes | current episode status |
| `current_phase_number` | integer                 |      yes | current phase          |
| `phase_started_at`     | datetime string         |      yes | current phase start    |
| `phase_due_end_at`     | datetime string or null |      yes | expected phase end     |
| `protocol_version`     | string                  |      yes | protocol version       |
| `healed_at`            | datetime string or null |      yes | heal timestamp         |
| `obsolete_at`          | datetime string or null |      yes | obsoletion timestamp   |
| `created_at`           | datetime string         |      yes | creation timestamp     |
| `updated_at`           | datetime string         |      yes | last update timestamp  |

### Allowed `status` values for v1

* `active_flare`
* `in_taper`
* `obsolete`

Note: relapse is modeled as an event plus reset to `active_flare`, not as a separate long-lived status.

---

## 9.3 Application object

```json
{
  "id": 987,
  "episode_id": 42,
  "applied_at": "2026-04-16T07:30:00Z",
  "treatment_type": "steroid",
  "treatment_name": "Hydrocortisone 1%",
  "quantity_text": "thin layer",
  "phase_number_snapshot": 2,
  "is_voided": false,
  "voided_at": null,
  "notes": "morning dose",
  "created_at": "2026-04-16T07:31:00Z"
}
```

### Fields

| Field                   | Type                    | Required | Meaning                  |
| ----------------------- | ----------------------- | -------: | ------------------------ |
| `id`                    | integer                 |      yes | application id           |
| `episode_id`            | integer                 |      yes | related episode          |
| `applied_at`            | datetime string         |      yes | application time         |
| `treatment_type`        | string                  |      yes | treatment category       |
| `treatment_name`        | string or null          |      yes | product/medication name  |
| `quantity_text`         | string or null          |      yes | free-text amount         |
| `phase_number_snapshot` | integer                 |      yes | phase at time of logging |
| `is_voided`             | boolean                 |      yes | whether invalidated      |
| `voided_at`             | datetime string or null |      yes | void timestamp           |
| `notes`                 | string or null          |      yes | note                     |
| `created_at`            | datetime string         |      yes | row creation timestamp   |

### Allowed `treatment_type` values for v1

* `steroid`
* `emollient`
* `other`

---

## 9.4 Event object

```json
{
  "id": 501,
  "event_uuid": "b8dfb1e6-17dd-45af-916f-c8f1f8ae6d73",
  "episode_id": 42,
  "event_type": "application_logged",
  "actor_type": "user",
  "actor_id": "user:42",
  "occurred_at": "2026-04-16T07:30:00Z",
  "payload": {
    "application_id": 987,
    "applied_at": "2026-04-16T07:30:00Z",
    "treatment_type": "steroid",
    "phase_number_snapshot": 2
  },
  "created_at": "2026-04-16T07:31:00Z"
}
```

### Fields

| Field         | Type            | Required | Meaning                   |
| ------------- | --------------- | -------: | ------------------------- |
| `id`          | integer         |      yes | event row id              |
| `event_uuid`  | uuid string     |      yes | stable event id           |
| `episode_id`  | integer         |      yes | related episode           |
| `event_type`  | string          |      yes | event type                |
| `actor_type`  | string          |      yes | `user`, `agent`, `system` |
| `actor_id`    | string or null  |      yes | actor id                  |
| `occurred_at` | datetime string |      yes | domain event time         |
| `payload`     | object          |      yes | event payload             |
| `created_at`  | datetime string |      yes | persistence timestamp     |

---

## 9.5 Due item object

```json
{
  "episode_id": 42,
  "subject_id": 7,
  "location_id": 12,
  "current_phase_number": 2,
  "treatment_due_today": true,
  "next_due_at": "2026-04-16T00:00:00Z",
  "last_application_at": "2026-04-14T07:30:00Z"
}
```

### Fields

| Field                  | Type                    | Required | Meaning                 |
| ---------------------- | ----------------------- | -------: | ----------------------- |
| `episode_id`           | integer                 |      yes | episode id              |
| `subject_id`           | integer                 |      yes | tracked person id       |
| `location_id`          | integer                 |      yes | body location id        |
| `current_phase_number` | integer                 |      yes | current phase           |
| `treatment_due_today`  | boolean                 |      yes | whether due today       |
| `next_due_at`          | datetime string or null |      yes | next due timestamp      |
| `last_application_at`  | datetime string or null |      yes | last logged application |

---

## 10. Endpoint List

The first version should provide these endpoints:

* `POST /locations`
* `GET /locations`
* `POST /episodes`
* `GET /episodes/{episode_id}`
* `GET /episodes`
* `POST /episodes/{episode_id}/heal`
* `POST /episodes/{episode_id}/relapse`
* `POST /episodes/{episode_id}/advance`
* `POST /applications`
* `POST /applications/{application_id}/void`
* `GET /episodes/{episode_id}/applications`
* `GET /episodes/{episode_id}/events`
* `GET /episodes/{episode_id}/timeline`
* `GET /episodes/due`

---

## 11. Locations

## 11.1 Create location

### Endpoint

```http
POST /locations
```

### Purpose

Create a new body location.

### Request body

```json
{
  "code": "left_elbow",
  "display_name": "Left elbow"
}
```

### Request fields

| Field          | Type   | Required | Meaning                      |
| -------------- | ------ | -------: | ---------------------------- |
| `code`         | string |      yes | stable machine-friendly code |
| `display_name` | string |      yes | human-readable name          |

### Validation rules

* `code` must be unique
* `code` should be lowercase and underscore-safe
* `display_name` must not be empty

### Success response

Status:

```http
201 Created
```

Body:

```json
{
  "location": {
    "id": 12,
    "code": "left_elbow",
    "display_name": "Left elbow",
    "created_at": "2026-04-01T09:00:00Z"
  }
}
```

### Error responses

* `409 Conflict` if location code already exists
* `422 Unprocessable Entity` for invalid input

---

## 11.2 List locations

### Endpoint

```http
GET /locations
```

### Purpose

Return all known body locations.

### Success response

```http
200 OK
```

```json
{
  "locations": [
    {
      "id": 12,
      "code": "left_elbow",
      "display_name": "Left elbow",
      "created_at": "2026-04-01T09:00:00Z"
    }
  ]
}
```

---

## 12. Episodes

## 12.1 Create episode

### Endpoint

```http
POST /episodes
```

### Purpose

Create a new eczema episode.

### Request body

```json
{
  "subject_id": 7,
  "location_id": 12,
  "protocol_version": "v1"
}
```

### Request fields

| Field              | Type    | Required | Meaning                        |
| ------------------ | ------- | -------: | ------------------------------ |
| `subject_id`       | integer |      yes | tracked person                 |
| `location_id`      | integer |      yes | body location                  |
| `protocol_version` | string  |       no | protocol version, default `v1` |

### Validation rules

* `subject_id` must exist
* `location_id` must exist
* `protocol_version` must exist
* for v1, only one non-obsolete episode should be allowed per `subject_id + location_id`

### Behavior

On success the server must:

* create the episode in phase 1
* set `status = active_flare`
* set `current_phase_number = 1`
* set `phase_started_at = now`
* create phase history row
* emit `episode_created` event

### Success response

```http
201 Created
```

```json
{
  "episode": {
    "id": 42,
    "subject_id": 7,
    "location_id": 12,
    "status": "active_flare",
    "current_phase_number": 1,
    "phase_started_at": "2026-04-01T09:00:00Z",
    "phase_due_end_at": null,
    "protocol_version": "v1",
    "healed_at": null,
    "obsolete_at": null,
    "created_at": "2026-04-01T09:00:00Z",
    "updated_at": "2026-04-01T09:00:00Z"
  }
}
```

### Error responses

* `404 Not Found` if subject or location does not exist
* `409 Conflict` if an active/tapering episode already exists for same subject and location
* `422 Unprocessable Entity` for invalid input

---

## 12.2 Get episode by id

### Endpoint

```http
GET /episodes/{episode_id}
```

### Purpose

Return one episode by id.

### Success response

```http
200 OK
```

```json
{
  "episode": {
    "id": 42,
    "subject_id": 7,
    "location_id": 12,
    "status": "active_flare",
    "current_phase_number": 1,
    "phase_started_at": "2026-04-01T09:00:00Z",
    "phase_due_end_at": null,
    "protocol_version": "v1",
    "healed_at": null,
    "obsolete_at": null,
    "created_at": "2026-04-01T09:00:00Z",
    "updated_at": "2026-04-01T09:00:00Z"
  }
}
```

### Error responses

* `404 Not Found` if episode does not exist

---

## 12.3 List episodes

### Endpoint

```http
GET /episodes
```

### Purpose

List episodes.

### Query parameters for v1

All query parameters are optional.

| Query param  | Type    | Meaning           |
| ------------ | ------- | ----------------- |
| `subject_id` | integer | filter by subject |
| `status`     | string  | filter by status  |

### Example

```http
GET /episodes?subject_id=7&status=active_flare
```

### Success response

```http
200 OK
```

```json
{
  "episodes": [
    {
      "id": 42,
      "subject_id": 7,
      "location_id": 12,
      "status": "active_flare",
      "current_phase_number": 1,
      "phase_started_at": "2026-04-01T09:00:00Z",
      "phase_due_end_at": null,
      "protocol_version": "v1",
      "healed_at": null,
      "obsolete_at": null,
      "created_at": "2026-04-01T09:00:00Z",
      "updated_at": "2026-04-01T09:00:00Z"
    }
  ]
}
```

---

## 12.4 Mark episode as healed

### Endpoint

```http
POST /episodes/{episode_id}/heal
```

### Purpose

Mark the episode as healed and move it into phase 2.

### Request body

```json
{
  "healed_at": "2026-04-05T18:00:00Z"
}
```

### Request fields

| Field       | Type            | Required | Meaning                          |
| ----------- | --------------- | -------: | -------------------------------- |
| `healed_at` | datetime string |       no | effective heal time; default now |

### Validation rules

* episode must exist
* episode must currently be in phase 1
* episode must not be obsolete

### Behavior

On success the server must:

* set `status = in_taper`
* set `current_phase_number = 2`
* set `healed_at`
* set `phase_started_at = healed_at`
* calculate `phase_due_end_at`
* close previous phase history row
* create phase 2 history row
* emit `healed_marked`
* emit `phase_entered`

### Success response

```http
200 OK
```

```json
{
  "episode": {
    "id": 42,
    "subject_id": 7,
    "location_id": 12,
    "status": "in_taper",
    "current_phase_number": 2,
    "phase_started_at": "2026-04-05T18:00:00Z",
    "phase_due_end_at": "2026-05-03T18:00:00Z",
    "protocol_version": "v1",
    "healed_at": "2026-04-05T18:00:00Z",
    "obsolete_at": null,
    "created_at": "2026-04-01T09:00:00Z",
    "updated_at": "2026-04-05T18:00:00Z"
  }
}
```

### Error responses

* `404 Not Found` if episode does not exist
* `409 Conflict` if episode is not in phase 1
* `422 Unprocessable Entity` for invalid timestamp

---

## 12.5 Report relapse

### Endpoint

```http
POST /episodes/{episode_id}/relapse
```

### Purpose

Reset an episode back to active flare because symptoms returned.

### Request body

```json
{
  "reported_at": "2026-05-20T09:30:00Z",
  "reason": "symptoms_returned"
}
```

### Request fields

| Field         | Type            | Required | Meaning                   |
| ------------- | --------------- | -------: | ------------------------- |
| `reported_at` | datetime string |       no | relapse time; default now |
| `reason`      | string          |      yes | short reason              |

### Validation rules

* episode must exist
* episode must not be obsolete
* episode may relapse from phase 2 to 7
* for v1, relapse from phase 1 is not allowed

### Behavior

On success the server must:

* set `status = active_flare`
* set `current_phase_number = 1`
* set `phase_started_at = reported_at`
* set `phase_due_end_at = null`
* close prior phase history row
* create phase 1 history row
* emit `relapse_marked`
* emit `phase_entered`

### Success response

```http
200 OK
```

```json
{
  "episode": {
    "id": 42,
    "subject_id": 7,
    "location_id": 12,
    "status": "active_flare",
    "current_phase_number": 1,
    "phase_started_at": "2026-05-20T09:30:00Z",
    "phase_due_end_at": null,
    "protocol_version": "v1",
    "healed_at": "2026-04-05T18:00:00Z",
    "obsolete_at": null,
    "created_at": "2026-04-01T09:00:00Z",
    "updated_at": "2026-05-20T09:30:00Z"
  }
}
```

### Error responses

* `404 Not Found` if episode does not exist
* `409 Conflict` if relapse is not valid in current phase/status
* `422 Unprocessable Entity` for invalid input

---

## 12.6 Advance phase

### Endpoint

```http
POST /episodes/{episode_id}/advance
```

### Purpose

Advance an episode to the next phase if allowed.

### Why this exists in v1

Even if phase progression may later be automated, v1 should expose a simple explicit action for controlled advancing.

### Request body

```json
{}
```

No fields required.

### Validation rules

* episode must exist
* episode must be in taper
* episode must not be obsolete
* advancing must be allowed under server business rules

### Behavior

If the current phase is:

* `2` → advance to `3`
* `3` → advance to `4`
* `4` → advance to `5`
* `5` → advance to `6`
* `6` → advance to `7`
* `7` → mark obsolete

On success the server must:

* update episode state
* update phase timestamps
* close old phase history row
* create next phase history row if applicable
* emit `phase_entered` or `episode_obsoleted`

### Success response for normal phase advance

```http
200 OK
```

```json
{
  "episode": {
    "id": 42,
    "subject_id": 7,
    "location_id": 12,
    "status": "in_taper",
    "current_phase_number": 3,
    "phase_started_at": "2026-05-03T18:00:00Z",
    "phase_due_end_at": "2026-05-17T18:00:00Z",
    "protocol_version": "v1",
    "healed_at": "2026-04-05T18:00:00Z",
    "obsolete_at": null,
    "created_at": "2026-04-01T09:00:00Z",
    "updated_at": "2026-05-03T18:00:00Z"
  }
}
```

### Success response for obsoletion after phase 7

```http
200 OK
```

```json
{
  "episode": {
    "id": 42,
    "subject_id": 7,
    "location_id": 12,
    "status": "obsolete",
    "current_phase_number": 7,
    "phase_started_at": "2026-06-17T18:00:00Z",
    "phase_due_end_at": "2026-07-01T18:00:00Z",
    "protocol_version": "v1",
    "healed_at": "2026-04-05T18:00:00Z",
    "obsolete_at": "2026-07-01T18:00:00Z",
    "created_at": "2026-04-01T09:00:00Z",
    "updated_at": "2026-07-01T18:00:00Z"
  }
}
```

### Error responses

* `404 Not Found`
* `409 Conflict` if phase cannot be advanced
* `422 Unprocessable Entity`

---

## 13. Applications

## 13.1 Log application

### Endpoint

```http
POST /applications
```

### Purpose

Log one treatment application for an episode.

### Request body

```json
{
  "episode_id": 42,
  "applied_at": "2026-04-16T07:30:00Z",
  "treatment_type": "steroid",
  "treatment_name": "Hydrocortisone 1%",
  "quantity_text": "thin layer",
  "notes": "morning dose"
}
```

### Request fields

| Field            | Type            | Required | Meaning                       |
| ---------------- | --------------- | -------: | ----------------------------- |
| `episode_id`     | integer         |      yes | target episode                |
| `applied_at`     | datetime string |       no | application time; default now |
| `treatment_type` | string          |      yes | treatment category            |
| `treatment_name` | string          |       no | product name                  |
| `quantity_text`  | string          |       no | amount                        |
| `notes`          | string          |       no | note                          |

### Validation rules

* episode must exist
* episode must not be obsolete
* `treatment_type` must be allowed

### Behavior

On success the server must:

* insert application row
* snapshot the current phase into `phase_number_snapshot`
* emit `application_logged`

### Success response

```http
201 Created
```

```json
{
  "application": {
    "id": 987,
    "episode_id": 42,
    "applied_at": "2026-04-16T07:30:00Z",
    "treatment_type": "steroid",
    "treatment_name": "Hydrocortisone 1%",
    "quantity_text": "thin layer",
    "phase_number_snapshot": 2,
    "is_voided": false,
    "voided_at": null,
    "notes": "morning dose",
    "created_at": "2026-04-16T07:31:00Z"
  }
}
```

### Error responses

* `404 Not Found`
* `409 Conflict` if application cannot be logged for episode state
* `422 Unprocessable Entity`

---

## 13.2 Void application

### Endpoint

```http
POST /applications/{application_id}/void
```

### Purpose

Invalidate a previously logged application without deleting audit history.

### Request body

```json
{
  "voided_at": "2026-04-16T08:00:00Z",
  "reason": "logged_by_mistake"
}
```

### Request fields

| Field       | Type            | Required | Meaning                       |
| ----------- | --------------- | -------: | ----------------------------- |
| `voided_at` | datetime string |       no | void time; default now        |
| `reason`    | string          |      yes | why the application is voided |

### Validation rules

* application must exist
* application must not already be voided

### Behavior

On success the server must:

* mark `is_voided = true`
* set `voided_at`
* emit `application_voided`

### Success response

```http
200 OK
```

```json
{
  "application": {
    "id": 987,
    "episode_id": 42,
    "applied_at": "2026-04-16T07:30:00Z",
    "treatment_type": "steroid",
    "treatment_name": "Hydrocortisone 1%",
    "quantity_text": "thin layer",
    "phase_number_snapshot": 2,
    "is_voided": true,
    "voided_at": "2026-04-16T08:00:00Z",
    "notes": "morning dose",
    "created_at": "2026-04-16T07:31:00Z"
  }
}
```

### Error responses

* `404 Not Found`
* `409 Conflict` if already voided
* `422 Unprocessable Entity`

---

## 13.3 List applications for an episode

### Endpoint

```http
GET /episodes/{episode_id}/applications
```

### Purpose

Return all applications for one episode.

### Query parameters for v1

| Query param      | Type    | Meaning         |
| ---------------- | ------- | --------------- |
| `include_voided` | boolean | default `false` |

### Success response

```http
200 OK
```

```json
{
  "applications": [
    {
      "id": 987,
      "episode_id": 42,
      "applied_at": "2026-04-16T07:30:00Z",
      "treatment_type": "steroid",
      "treatment_name": "Hydrocortisone 1%",
      "quantity_text": "thin layer",
      "phase_number_snapshot": 2,
      "is_voided": false,
      "voided_at": null,
      "notes": "morning dose",
      "created_at": "2026-04-16T07:31:00Z"
    }
  ]
}
```

### Error responses

* `404 Not Found` if episode does not exist

---

## 14. Events and Timeline

## 14.1 List episode events

### Endpoint

```http
GET /episodes/{episode_id}/events
```

### Purpose

Return raw event rows for one episode.

### Query parameters for v1

| Query param  | Type   | Meaning         |
| ------------ | ------ | --------------- |
| `event_type` | string | optional filter |

### Success response

```http
200 OK
```

```json
{
  "events": [
    {
      "id": 501,
      "event_uuid": "b8dfb1e6-17dd-45af-916f-c8f1f8ae6d73",
      "episode_id": 42,
      "event_type": "episode_created",
      "actor_type": "user",
      "actor_id": "user:42",
      "occurred_at": "2026-04-01T09:00:00Z",
      "payload": {
        "location_id": 12,
        "location_code": "left_elbow",
        "initial_phase_number": 1,
        "protocol_version": "v1"
      },
      "created_at": "2026-04-01T09:00:00Z"
    }
  ]
}
```

### Error responses

* `404 Not Found`

---

## 14.2 Get episode timeline

### Endpoint

```http
GET /episodes/{episode_id}/timeline
```

### Purpose

Return a simple chronological timeline for one episode.

### v1 behavior

For v1, this may return the same data as `/events`, ordered chronologically.

This route exists to give CLI and agent clients a stable semantic endpoint.

### Success response

```http
200 OK
```

```json
{
  "timeline": [
    {
      "id": 501,
      "event_uuid": "b8dfb1e6-17dd-45af-916f-c8f1f8ae6d73",
      "episode_id": 42,
      "event_type": "episode_created",
      "actor_type": "user",
      "actor_id": "user:42",
      "occurred_at": "2026-04-01T09:00:00Z",
      "payload": {
        "location_id": 12,
        "location_code": "left_elbow",
        "initial_phase_number": 1,
        "protocol_version": "v1"
      },
      "created_at": "2026-04-01T09:00:00Z"
    }
  ]
}
```

### Error responses

* `404 Not Found`

---

## 15. Due View

## 15.1 Get due episodes

### Endpoint

```http
GET /episodes/due
```

### Purpose

Return episodes that currently require user attention.

### v1 semantics

For v1, this endpoint should return episodes where treatment is due **today** according to the current phase rules and logged non-voided applications.

This endpoint is intentionally simple.

### Query parameters for v1

| Query param  | Type    | Meaning         |
| ------------ | ------- | --------------- |
| `subject_id` | integer | optional filter |

### Success response

```http
200 OK
```

```json
{
  "due": [
    {
      "episode_id": 42,
      "subject_id": 7,
      "location_id": 12,
      "current_phase_number": 2,
      "treatment_due_today": true,
      "next_due_at": "2026-04-16T00:00:00Z",
      "last_application_at": "2026-04-14T07:30:00Z"
    }
  ]
}
```

### Error responses

* `422 Unprocessable Entity` for invalid query parameters

---

## 16. Phase Semantics Used by API

The API relies on these v1 phase rules:

| Phase |   Duration | Frequency    |
| ----- | ---------: | ------------ |
| 1     | open-ended | 2x daily     |
| 2     |    28 days | every 2 days |
| 3     |    14 days | every 3 days |
| 4     |    14 days | every 4 days |
| 5     |    14 days | every 5 days |
| 6     |    14 days | every 6 days |
| 7     |    14 days | every 7 days |

For v1, the API contract assumes:

* healing moves phase 1 → phase 2 immediately
* relapse moves current taper phase → phase 1 immediately
* `advance` is an explicit action
* the backend calculates `phase_due_end_at`

More detailed adherence logic can be specified separately if needed.

---

## 17. HTTP Status Code Rules

### Success

* `200 OK` for successful reads and updates
* `201 Created` for successful creation

### Client errors

* `400 Bad Request` for malformed request syntax
* `401 Unauthorized` if authentication is missing or invalid
* `403 Forbidden` if authenticated but not allowed
* `404 Not Found` if resource does not exist
* `409 Conflict` if request violates domain rules
* `422 Unprocessable Entity` for validation errors

### Server errors

* `500 Internal Server Error` for unexpected failures

---

## 18. Domain Error Codes

Recommended v1 error codes:

* `invalid_request`
* `unauthorized`
* `forbidden`
* `location_not_found`
* `subject_not_found`
* `episode_not_found`
* `application_not_found`
* `location_code_already_exists`
* `episode_already_exists_for_subject_location`
* `episode_not_in_phase_1`
* `episode_not_in_taper`
* `episode_is_obsolete`
* `invalid_relapse_state`
* `application_already_voided`
* `invalid_treatment_type`
* `invalid_event_type`

Example:

```json
{
  "error": {
    "code": "episode_not_found",
    "message": "Episode 42 was not found."
  }
}
```

---

## 19. Transaction Requirements

The backend must treat the following operations as transactional:

* create episode
* mark healed
* report relapse
* advance phase
* log application
* void application

Each transaction must update relational state and write matching events together.

---

## 20. Minimal Auth Contract for v1

If auth is implemented in v1, keep it minimal.

Recommended simple contract:

### Request

Client sends:

```text
Authorization: Bearer <token>
```

### Server behavior

* reject missing token with `401`
* reject invalid token with `401`
* reject insufficient permissions with `403`

The full auth system can be documented separately.

---

## 21. Minimal Permissions Model for v1

For the first version, keep permissions simple.

Assume:

* an authenticated actor may read and modify only subjects they are allowed to manage
* permission checks happen before domain action
* forbidden access returns `403`

A more detailed family permission spec can be added separately.

---

## 22. Out of Scope for v1

This API contract does **not** define:

* user registration flows
* login/token issuance endpoints
* advanced pagination
* bulk endpoints
* note endpoints
* image upload
* food-tracker linkage
* analytics endpoints
* background notification endpoints
* webhooks
* idempotency keys

These can be added later.

---

## 23. Suggested Implementation Notes

These are recommendations, not contract requirements.

Recommended stack:

* FastAPI
* PostgreSQL
* SQLAlchemy 2.x
* Alembic

Recommended response modeling:

* Pydantic request models
* Pydantic response models
* service layer for business logic
* event writes inside same DB transaction as state change

---

## 24. Example End-to-End Flow

### 1. Create location

```http
POST /locations
```

### 2. Create episode

```http
POST /episodes
```

### 3. Mark healed

```http
POST /episodes/42/heal
```

### 4. Log application

```http
POST /applications
```

### 5. View timeline

```http
GET /episodes/42/timeline
```

### 6. Report relapse

```http
POST /episodes/42/relapse
```

---

## 25. Summary

The first API contract is intentionally small and practical.

It provides:

* simple JSON endpoints
* explicit episode lifecycle actions
* application logging
* event/timeline access
* due view for CLI and agents

It avoids unnecessary complexity while still being structured enough to support:

* a Dockerized FastAPI backend
* PostgreSQL persistence
* future CLI usage
* future agent integration
