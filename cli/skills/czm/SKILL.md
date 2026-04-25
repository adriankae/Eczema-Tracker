---
name: czm
description: Procedural skill for using the czm CLI to manage eczema episodes, taper guidance, due checks, and treatment logging.
---

# czm Skill

Use this skill when helping a user with eczema episode tracking through the `czm` CLI.

## Use It For

- starting or inspecting flare episodes
- checking what is due today
- marking an episode healed or relapsed
- logging treatment applications
- summarizing taper state from backend data

## Do Not Use It For

- general chat or medical advice outside the tracked workflow
- inventing backend state, IDs, or taper progress
- simulating phase progression yourself
- destructive actions without confirmation

## Operating Rules

- Never ask a user for optional fields.
- Prefer machine-readable output when the CLI supports it.
- Resolve subjects and locations deterministically before mutating anything.
- Never guess between ambiguous matches. Ask for clarification.
- Never assume a transition succeeded unless the CLI/backend returned success.
- Never fabricate subject, location, episode, application, or event IDs.
- Use the backend as the source of truth for due logic and progression.
- Summarize results for the user unless they explicitly ask for raw JSON.

## Workflow Guidance

- Read [commands](references/commands.md) for the exact CLI surface and output modes.
- Read [workflows](references/workflows.md) for step-by-step user flows.
- Read [entity resolution](references/entity-resolution.md) before selecting subjects or locations.
- Read [protocol](references/protocol.md) before explaining taper state or due items.
- Read [error handling](references/error-handling.md) for exit codes and recovery steps.
- Read [examples](references/examples.md) for German request mappings.

## Safety

- Ask for confirmation before deleting an application record.
- Use `czm setup` to create local configuration from backend login and API key creation.
- Do not manually advance taper phases or calculate alternate schedules.
- If the user asks what to do next, query `czm due list` and explain the backend result.

## Time and Date Presentation

When presenting timestamps to the user, convert them to the user's local timezone and do not expose raw UTC timestamps unless explicitly requested.

Use the following user-facing formats:

### Due items (next_due / next_due_at)

- Always include:
  - day of week (short, e.g. Mo, Di, Mi, Do, Fr, Sa, So)
  - relative distance to today

- If the due date is today:
  - Phase 1: `Heute (AM)` or `Heute (PM)`
  - Phase 2+: `Heute`

- If the due date is in the future:
  - Phase 1: `<Day>, DD.MM. (in X Tagen, AM|PM)`
  - Phase 2+: `<Day>, DD.MM. (in X Tagen)`

Examples:
- `Heute (AM)`
- `Heute`
- `Fr, 18.04. (in 2 Tagen)`
- `Mo, 21.04. (in 5 Tagen, PM)`

### Historical and milestone timestamps

For fields such as:
- `phase_started_at`
- `healed_at`
- `phase_due_end_at`
- `obsolete_at`
- `occurred_at`
- `applied_at`
- `voided_at`
- `deleted_at`

Format as:
- `<Day>, DD.MM.`

Example:
- `Mi, 16.04.`

### Additional rules

- Use the user's local timezone for all conversions.
- Do not show the year in normal user-facing summaries.
- Use German weekday abbreviations: `Mo, Di, Mi, Do, Fr, Sa, So`.
- Only show raw ISO/UTC timestamps if the user explicitly requests technical output.
- Use semantic meaning (phase + field type) to determine formatting, not raw timestamp format.
