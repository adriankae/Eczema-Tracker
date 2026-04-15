# Event Specification

Version: 1.0
Status: Normative
Scope: Eczema Treatment Tracker backend

---

## 1. Purpose

This document defines the event model for the first version of the Eczema Treatment Tracker.

The goal is to keep the event system simple and useful.

The event model exists to provide:

* a chronological audit trail
* explainability for users and agents
* a reliable episode timeline
* a clear record of who did what and when

This is **not** a full event-sourcing design.

---

## 2. Design Principles

The first version follows these principles:

1. **Keep operational data in normal tables**

   * `eczema_episodes` stores current state
   * `episode_phase_history` stores phase transitions
   * `treatment_applications` stores application records

2. **Use events as an audit trail**

   * `episode_events` records meaningful actions
   * events help explain decisions and reconstruct history

3. **Keep events append-only**

   * insert new events
   * do not edit or hard-delete old events in normal operation

4. **Write events in the same transaction as the state change**

   * this avoids mismatches between state and history

5. **Keep payloads small**

   * include only the most important facts needed for explanation

---

## 3. Source of Truth

The system uses the following source-of-truth model:

| Concern                              | Source of truth          |
| ------------------------------------ | ------------------------ |
| current episode state                | `eczema_episodes`        |
| phase transition history             | `episode_phase_history`  |
| treatment application records        | `treatment_applications` |
| audit trail / timeline / explanation | `episode_events`         |

This means:

* `episode_events` is the historical log
* `episode_events` does not replace the main relational tables

---

## 4. Event Table

Table name:

* `episode_events`

Recommended PostgreSQL schema:

```sql
CREATE TABLE episode_events (
    id              BIGSERIAL PRIMARY KEY,
    event_uuid      UUID NOT NULL UNIQUE,
    episode_id      BIGINT NOT NULL REFERENCES eczema_episodes(id),
    event_type      TEXT NOT NULL,
    actor_type      TEXT NOT NULL CHECK (actor_type IN ('user', 'agent', 'system')),
    actor_id        TEXT NULL,
    occurred_at     TIMESTAMPTZ NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Recommended indexes:

```sql
CREATE INDEX ix_episode_events_episode_id_occurred_at
ON episode_events (episode_id, occurred_at, id);

CREATE INDEX ix_episode_events_event_type_occurred_at
ON episode_events (event_type, occurred_at, id);
```

---

## 5. Common Event Fields

Each event row must contain:

| Field         | Type        | Required | Meaning                      |
| ------------- | ----------- | -------: | ---------------------------- |
| `id`          | bigint      |      yes | internal database id         |
| `event_uuid`  | uuid        |      yes | stable unique event id       |
| `episode_id`  | bigint      |      yes | related episode              |
| `event_type`  | text        |      yes | event type                   |
| `actor_type`  | text        |      yes | `user`, `agent`, or `system` |
| `actor_id`    | text        |       no | actor identifier             |
| `occurred_at` | timestamptz |      yes | when the event happened      |
| `payload`     | jsonb       |      yes | event-specific data          |
| `created_at`  | timestamptz |      yes | when the row was stored      |

---

## 6. Actor Rules

Allowed `actor_type` values:

* `user`
* `agent`
* `system`

Meaning:

* `user` = authenticated human user
* `agent` = assistant or automation acting on behalf of a user
* `system` = backend-generated action such as automatic phase advance

`actor_id` should be a simple stable string.

Examples:

* `user:42`
* `agent:openclaw`
* `system:phase-advance`

---

## 7. Event Types

The first version should support only these event types:

* `episode_created`
* `healed_marked`
* `phase_entered`
* `relapse_marked`
* `application_logged`
* `application_voided`
* `episode_obsoleted`

This set is intentionally small.

---

## 8. Event Type Specifications

## 8.1 `episode_created`

### Meaning

A new eczema episode was created.

### Emitted when

A new `eczema_episodes` row is inserted successfully.

### Required payload fields

| Field                  | Type    | Meaning                |
| ---------------------- | ------- | ---------------------- |
| `location_id`          | integer | body location id       |
| `location_code`        | string  | location code snapshot |
| `initial_phase_number` | integer | usually `1`            |
| `protocol_version`     | string  | protocol used          |

### Example payload

```json
{
  "location_id": 12,
  "location_code": "left_elbow",
  "initial_phase_number": 1,
  "protocol_version": "v1"
}
```

---

## 8.2 `healed_marked`

### Meaning

The episode was explicitly marked as healed.

### Emitted when

`POST /episodes/{id}/heal` succeeds.

### Required payload fields

| Field               | Type            | Meaning                     |
| ------------------- | --------------- | --------------------------- |
| `from_phase_number` | integer         | previous phase, usually `1` |
| `to_phase_number`   | integer         | new phase, usually `2`      |
| `healed_at`         | datetime string | effective heal timestamp    |

### Example payload

```json
{
  "from_phase_number": 1,
  "to_phase_number": 2,
  "healed_at": "2026-04-15T08:00:00Z"
}
```

---

## 8.3 `phase_entered`

### Meaning

The episode entered a new phase.

### Emitted when

A valid phase transition occurs.

Examples:

* phase 1 → phase 2 after healing
* phase 2 → phase 3 after duration ends
* phase 4 → phase 1 after relapse

### Required payload fields

| Field               | Type                    | Meaning                 |
| ------------------- | ----------------------- | ----------------------- |
| `from_phase_number` | integer                 | previous phase          |
| `to_phase_number`   | integer                 | new phase               |
| `started_at`        | datetime string         | start time of new phase |
| `due_end_at`        | datetime string or null | expected phase end      |
| `reason`            | string                  | why phase changed       |

### Allowed `reason`

* `healed_marked`
* `auto_advance`
* `relapse`

### Example payload

```json
{
  "from_phase_number": 2,
  "to_phase_number": 3,
  "started_at": "2026-05-13T00:00:00Z",
  "due_end_at": "2026-05-27T00:00:00Z",
  "reason": "auto_advance"
}
```

---

## 8.4 `relapse_marked`

### Meaning

Symptoms returned and the episode was reset to active flare.

### Emitted when

`POST /episodes/{id}/relapse` succeeds.

### Required payload fields

| Field               | Type            | Meaning               |
| ------------------- | --------------- | --------------------- |
| `from_phase_number` | integer         | previous phase        |
| `to_phase_number`   | integer         | new phase, always `1` |
| `reported_at`       | datetime string | relapse timestamp     |
| `reason`            | string          | short reason          |

### Example payload

```json
{
  "from_phase_number": 4,
  "to_phase_number": 1,
  "reported_at": "2026-05-20T09:30:00Z",
  "reason": "symptoms_returned"
}
```

---

## 8.5 `application_logged`

### Meaning

A treatment application was logged.

### Emitted when

A new `treatment_applications` row is inserted successfully.

### Required payload fields

| Field                   | Type            | Meaning                     |
| ----------------------- | --------------- | --------------------------- |
| `application_id`        | integer         | linked application row id   |
| `applied_at`            | datetime string | application timestamp       |
| `treatment_type`        | string          | e.g. `steroid`, `emollient` |
| `phase_number_snapshot` | integer         | phase at logging time       |

### Optional payload fields

| Field            | Type   | Meaning                   |
| ---------------- | ------ | ------------------------- |
| `treatment_name` | string | optional product name     |
| `quantity_text`  | string | optional free-text amount |
| `notes`          | string | optional note             |

### Example payload

```json
{
  "application_id": 987,
  "applied_at": "2026-04-16T07:30:00Z",
  "treatment_type": "steroid",
  "phase_number_snapshot": 2,
  "treatment_name": "Hydrocortisone 1%",
  "quantity_text": "thin layer"
}
```

---

## 8.6 `application_voided`

### Meaning

A previously logged application was invalidated.

### Emitted when

An application is explicitly voided.

### Required payload fields

| Field            | Type            | Meaning                   |
| ---------------- | --------------- | ------------------------- |
| `application_id` | integer         | linked application row id |
| `voided_at`      | datetime string | void timestamp            |
| `reason`         | string          | why it was voided         |

### Example payload

```json
{
  "application_id": 987,
  "voided_at": "2026-04-16T08:00:00Z",
  "reason": "logged_by_mistake"
}
```

### Note

For v1, prefer voiding over hard deletion.

---

## 8.7 `episode_obsoleted`

### Meaning

The episode completed the protocol and became obsolete.

### Emitted when

The episode is marked obsolete after the final phase is complete.

### Required payload fields

| Field                | Type            | Meaning              |
| -------------------- | --------------- | -------------------- |
| `final_phase_number` | integer         | usually `7`          |
| `obsoleted_at`       | datetime string | obsoletion timestamp |
| `reason`             | string          | closure reason       |

### Example payload

```json
{
  "final_phase_number": 7,
  "obsoleted_at": "2026-07-01T00:00:00Z",
  "reason": "protocol_completed"
}
```

---

## 9. Emission Rules

Events must be written in the same database transaction as the related state change.

### Episode creation

```text
BEGIN
  insert eczema_episodes
  insert phase history for phase 1
  insert episode_created event
COMMIT
```

### Mark healed

```text
BEGIN
  update eczema_episodes
  update/close previous phase history
  insert new phase history for phase 2
  insert healed_marked event
  insert phase_entered event
COMMIT
```

### Log application

```text
BEGIN
  insert treatment_applications returning id
  insert application_logged event
COMMIT
```

### Report relapse

```text
BEGIN
  update eczema_episodes to phase 1
  update/close previous phase history
  insert new phase history for phase 1
  insert relapse_marked event
  insert phase_entered event
COMMIT
```

### Mark obsolete

```text
BEGIN
  update eczema_episodes to obsolete
  insert episode_obsoleted event
COMMIT
```

---

## 10. Immutability Rules

For v1:

* events are append-only
* do not update old events
* do not hard-delete old events in normal operation

If a previous action was wrong:

* create a corrective event instead of changing history

Example:

* wrong application entry → emit `application_voided`

---

## 11. Validation Rules

The backend must validate before inserting an event:

* `event_uuid` is a valid UUID
* `event_type` is allowed
* `actor_type` is allowed
* `episode_id` exists
* payload matches the required fields for the event type

For `application_logged` and `application_voided`:

* `application_id` must exist

---

## 12. Ordering Rules

Canonical timeline ordering:

1. `occurred_at` ascending
2. `id` ascending

This should be the default for timeline views and audit outputs.

---

## 13. API Exposure

The API may expose events through endpoints such as:

* `GET /episodes/{id}/events`
* `GET /episodes/{id}/timeline`

For v1, a simple event list is enough.

Recommended response behavior:

* sort ascending by time
* include all envelope fields
* include payload as stored

---

## 14. Example Timeline

Example: create episode, heal, log application, relapse

```text
2026-04-01T09:00:00Z  episode_created
2026-04-05T18:00:00Z  healed_marked
2026-04-05T18:00:00Z  phase_entered
2026-04-07T07:30:00Z  application_logged
2026-05-20T09:30:00Z  relapse_marked
2026-05-20T09:30:00Z  phase_entered
```

---

## 15. Integrity Expectations

The system should maintain these expectations:

* every episode has exactly one `episode_created` event
* every logged application has exactly one `application_logged` event
* every relapse action has exactly one `relapse_marked` event
* every real phase transition has exactly one `phase_entered` event
* every obsolete episode has exactly one `episode_obsoleted` event

---

## 16. Out of Scope for v1

This spec does **not** define:

* full event-sourcing
* complex payload versioning
* causal event chains
* idempotency keys
* advanced correction workflows
* separate note events
* family-level event aggregation
* permissions and auth rules

These can be added later if needed.

---

## 17. Summary

The first event model is intentionally simple:

* one `episode_events` table
* a small fixed set of event types
* one event written for each meaningful action
* append-only behavior
* small JSON payloads
* events used for audit trail and explanation, not as the only source of truth

This is sufficient for:

* auditing
* timeline views
* agent explanations
* debugging
* future extension
