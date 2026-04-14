# Eczema Treatment Tracker

A self-hosted backend system for tracking eczema episodes, managing treatment phases, and supporting agent-driven care workflows.

---

## 1. Overview

This system tracks eczema progression per body location and enforces a structured tapering protocol for treatment.

It is designed to:

* support **multi-user environments** (families, parents, children)
* provide a **deterministic treatment schedule**
* offer a **CLI interface** for daily usage
* allow **agent-based automation and reasoning**
* maintain a **complete audit trail**

---

## 2. Core Concepts

### 2.1 Body Location

A normalized anatomical location (e.g., `glabella ossis frontalis`, `left_elbow`, `neck`).

---

### 2.2 Eczema Episode

A single occurrence of eczema at a specific location.

Lifecycle:

```
active_flare
→ healed
→ taper phases (2–7)
→ obsolete

(relapse can occur from healed or any taper phase → back to active_flare)
```

---

### 2.3 Taper Protocol

A deterministic treatment plan:

| Phase | Duration | Frequency    |
| ----- | -------- | ------------ |
| 1     | open     | 2x daily     |
| 2     | 28 days  | every 2 days |
| 3     | 14 days  | every 3 days |
| 4     | 14 days  | every 4 days |
| 5     | 14 days  | every 5 days |
| 6     | 14 days  | every 6 days |
| 7     | 14 days  | every 7 days |

---

### 2.4 Phase State

Each episode maintains:

* current phase
* phase start timestamp
* expected end timestamp

---

### 2.5 Treatment Applications

Logs of actual cream/medication usage.

Each application:

* belongs to an episode
* has a timestamp (`applied_at`)
* includes treatment type (e.g. steroid, emollient)
* is used to evaluate adherence and derive next actions

---

### 2.6 Events

Append-only log of all meaningful actions:

* episode creation
* healing
* phase transitions
* relapse (explicit user-reported state change back to flare)
* application logging
* completion

---

## 3. Architecture

```
      AI Agent
          │
          ▼
    Headless CLI 
          │
          ▼
      API Server
          │
          ▼
     PostgreSQL
```

---

## 4. Technology Stack

* Database: PostgreSQL
* Backend: API server (recommended: Python/FastAPI or Node.js)
* Interface:

  * CLI tool
  * Agent (OpenClaw / Hermes)
* Deployment: Docker

---

## 5. Database Schema

### Tables

* `users`
* `families`
* `family_members`
* `body_locations`
* `eczema_episodes`
* `taper_protocol_phases`
* `episode_phase_history`
* `treatment_applications`
* `episode_events`

---

### 5.1 Users & Families

Supports multi-user setups.

```sql
users
families
family_members (user ↔ family mapping)
```

---

### 5.2 Body Locations

Normalized list of anatomical areas.

---

### 5.3 Eczema Episodes

Tracks lifecycle and current state.

Key fields:

* `status` (includes `active_flare`, `in_taper`, `obsolete`)
* `current_phase_number`
* `phase_started_at`
* `phase_due_end_at`
* `protocol_version`

---

### 5.4 Taper Protocol

Defines treatment logic.

Versioned via `protocol_version`.

---

### 5.5 Phase History

Tracks all transitions between phases.

Includes:

* phase start
* phase end
* transition reason (`healed`, `auto_advance`, `relapse`)

---

### 5.6 Treatment Applications

Logs real-world usage.

Each record represents:

* one application event
* used for:

  * adherence tracking
  * next-dose calculation
  * agent reasoning

---

### 5.7 Episode Events

Append-only event stream for:

* debugging
* explainability
* agent reasoning

Important event types:

* `episode_created`
* `healed_marked`
* `phase_entered`
* `relapse_marked`
* `application_logged`
* `episode_obsoleted`

---

## 6. State Machine

```
created
→ active_flare (phase 1)
→ phase 2
→ phase 3
→ ...
→ phase 7
→ obsolete
```

relapse:
phase 2–7 → active_flare (phase 1 restart)

---

## 7. Relapse Handling

Relapse is explicitly user-driven.

### Trigger

User reports:

> symptoms returned

### Effect

* event: `relapse_marked`
* episode state:

  * `status → active_flare`
  * `current_phase_number → 1`
* new phase history entry is created

### Design choice

Relapse is modeled as:

* event (source of truth)
* plus state transition

This ensures:

* auditability
* agent explainability
* deterministic recovery logic

---

## 8. Multi-User Model

### Structure

```
Family
 ├── Parent
 ├── Parent
 ├── Child
 └── Child
```

Each episode belongs to:

* a **user**
* optionally a **family context**

---

## 9. API Design (Conceptual)

### Endpoints

#### Create location

```
POST /locations
```

#### Create episode

```
POST /episodes
```

#### Mark healed

```
POST /episodes/{id}/heal
```

#### Log application

```
POST /applications
```

#### Report relapse

```
POST /episodes/{id}/relapse
```

#### Advance phase

```
POST /episodes/{id}/advance
```

#### Get due treatments

```
GET /episodes/due
```

---

## 10. CLI Design (Conceptual)

Examples:

```bash
eczema episode create --location left_elbow
eczema episode heal 42
eczema episode relapse 42
eczema apply log 42 --type steroid
eczema episode due
eczema episode timeline 42
```

---

## 11. Agent Integration

The system is designed for agents to:

* prompt users to log medication application
* detect missing applications
* create episodes
* read event history
* determine next required actions
* detect relapse patterns
* explain decisions based on event stream

---

## 12. Future Extensions

### Planned

* Treatment plan instances
* Notification system (missed dose, phase change)
* Analytics (adherence, relapse probability)
* Gamification
* Picture of location
* Link to food tracker for pattern and trigger recognition

---

## 13. Design Principles

* deterministic protocol logic
* explicit state tracking
* append-only history
* agent-first design
* multi-user support from start

---

## 14. Deployment

Recommended:

```bash
docker-compose up
```

Services:

* API server
* PostgreSQL

---

## 15. Why this architecture

This system separates:

* **state** (episodes)
* **rules** (protocol)
* **history** (events)
* **actions** (applications)

Additionally:

* relapse is modeled explicitly as an event + state transition
* application logging is first-class and drives system behavior

This ensures:

* correctness
* explainability
* scalability
* agent compatibility

---

## 16. Status

Early-stage design, optimized for:

* correctness
* extensibility
* real-world usage
* future automation
