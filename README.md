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

---

### 2.6 Events

Append-only log of all meaningful actions:

* episode creation
* healing
* phase transitions
* relapse
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

* `status`
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

---

### 5.6 Treatment Applications

Logs real-world usage.

---

### 5.7 Episode Events

Append-only event stream for:

* debugging
* explainability
* agent reasoning

---

## 6. State Machine

```
created
→ active_flare
→ healed
→ phase 2
→ phase 3
→ ...
→ phase 7
→ obsolete
```

---

## 7. Multi-User Model

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

## 8. API Design (Conceptual)

### Endpoints

#### Create episode

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

#### Advance phase

```
POST /episodes/{id}/advance
```

#### Get due treatments

```
GET /episodes/due
```

---

## 9. CLI Design (Conceptual)

Examples:

```bash
eczema episode create --location left_elbow
eczema episode heal 42
eczema apply log 42 --type steroid
eczema episode due
eczema episode timeline 42
```

---

## 10. Agent Integration

The system is designed for agents to:

* prompt a user to log medication application
* create a new episode
* read event history
* determine next required actions
* detect anomalies (missed treatments)

---

## 11. Future Extensions

### Planned

* Treatment plan instances
* Notification system
* Mobile interface
* Analytics (adherence, relapse probability)

---

## 12. Design Principles

* deterministic protocol logic
* explicit state tracking
* append-only history
* agent-first design
* multi-user support from start

---

## 13. Deployment

Recommended:

```bash
docker-compose up
```

Services:

* API server
* PostgreSQL

---

## 14. Why this architecture

This system separates:

* **state** (episodes)
* **rules** (protocol)
* **history** (events)
* **actions** (applications)

This ensures:

* correctness
* explainability
* scalability
* agent compatibility

---

## 15. Status

Early-stage design, optimized for:

* correctness
* extensibility
* real-world usage
* future automation
