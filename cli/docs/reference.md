# Command Reference

This page lists every `zema` command, what it does, and a working example. The legacy `czm` command remains available as a compatibility alias.

Human-readable output shows dates in `DD.MM.YY` format. Phase 1 due items use `AM, DD.MM.YY` or `PM, DD.MM.YY` based on the local display timezone.

All commands use the same configuration rules:

1. CLI flags
2. environment variables
3. config file at `~/.config/czm/config.toml` or `$XDG_CONFIG_HOME/czm/config.toml`

If you are just getting started, run `zema setup` first and then read [Getting Started](getting-started.md).

All examples prefer `zema`; replace it with `czm` if you need the compatibility alias.

## `czm setup`

Create the local config file automatically by logging into the backend, creating an API key, and writing `config.toml`.

By default this command uses `http://localhost:28173`. Pass `--base-url` if your backend is running somewhere else, such as a Docker service name or a non-default port.

Example:

```bash
czm setup \
  --username admin \
  --password admin \
  --api-key-name czm-cli \
  --timezone Europe/Berlin \
  --base-url http://backend-host:28173
```

Output:

```text
Wrote config to ~/.config/czm/config.toml
Next: run `czm subject list`
```

## `czm subject create`

Create a tracked subject for your account.

Arguments:

- `--display-name` subject name shown in lists and resolution

Example:

```bash
czm subject create --display-name "Child A"
```

Example output:

```text
id            1
display_name  Child A
```

## `czm subject list`

List all subjects for the authenticated account.

Example:

```bash
czm subject list
```

Example output:

```text
Subjects:
- 1: Child A
- 2: Child B
```

## `czm subject get`

Get one subject by numeric ID or by resolved text reference.

Resolution order:

1. exact match
2. case-insensitive match
3. substring match

Example:

```bash
czm subject get "Child A"
```

Example output:

```text
id            1
display_name  Child A
```

## `czm location create`

Create a body location.

Arguments:

- `--code` machine-friendly unique code
- `--display-name` human-readable label

Example:

```bash
czm location create --code left_elbow --display-name "Left elbow"
```

Example output:

```text
id            1
code          left_elbow
display_name  Left elbow
```

## `czm location list`

List all locations for the authenticated account.

Example:

```bash
czm location list
```

Example output:

```text
Locations:
- 1: left_elbow (Left elbow)
```

## `czm episode create`

Create an episode for a subject at a location.

Arguments:

- `--subject` subject name or ID
- `--location` location code, display name, or ID
- `--protocol-version` protocol version, defaults to `v1`

Example:

```bash
czm episode create --subject "Child A" --location "Left elbow"
```

Example output:

```text
id                    1
subject_id            1
location_id           1
status                active_flare
current_phase_number  1
phase_started_at      15.04.26
phase_due_end_at      None
healed_at             None
obsolete_at           None
```

## `czm episode list`

List episodes, optionally filtered by subject or status.

Arguments:

- `--subject` subject reference
- `--status` episode status such as `active_flare`, `in_taper`, or `obsolete`

Example:

```bash
czm episode list --subject "Child A"
```

Example output:

```text
Episodes:
- 1: subject 1, location 1, phase 1, active_flare
```

## `czm episode get`

Get one episode by numeric ID.

Example:

```bash
czm episode get 1
```

Example output:

```text
id                    1
subject_id            1
location_id           1
status                active_flare
current_phase_number  1
phase_started_at      15.04.26
phase_due_end_at      None
healed_at             None
obsolete_at           None
```

## `czm episode heal`

Mark an active episode as healed and move it into phase 2.

Arguments:

- `episode` episode ID
- `--healed-at` optional local timestamp in the configured timezone

Example:

```bash
czm episode heal 1 --healed-at 2026-04-15T18:00:00
```

Example output:

```text
status                in_taper
current_phase_number  2
phase_started_at      15.04.26
phase_due_end_at      13.05.26
```

## `czm episode relapse`

Reset an episode back to phase 1 after relapse.

Syntax:

```bash
czm episode relapse <episode> [--reason <text>] [--reported-at <local-timestamp>]
```

Arguments:

- `episode` episode ID
- `--reported-at` optional local timestamp in the configured timezone
- `--reason` optional human-readable relapse reason; if omitted, the CLI uses the repo-defined relapse transition reason

Example:

```bash
czm episode relapse 1 --reported-at 2026-04-15T21:00:00 --reason symptoms_returned
```

Example output:

```text
status                active_flare
current_phase_number  1
phase_started_at      15.04.26
```

## `czm application log`

Log a treatment application against an episode.

Arguments:

- `--episode` episode ID
- `--applied-at` optional local timestamp
- `--treatment-type` optional; one of `steroid`, `emollient`, or `other`; defaults to `other`
- `--treatment-name` optional product name
- `--quantity-text` optional amount text
- `--notes` optional note

Example:

```bash
czm application log \
  --episode 1 \
  --applied-at 2026-04-15T20:30:00 \
  --treatment-type steroid \
  --treatment-name "Hydrocortisone 1%" \
  --quantity-text "thin layer" \
  --notes "evening dose"
```

Example output:

```text
id                 1
episode_id         1
applied_at         15.04.26
treatment_type     steroid
treatment_name     Hydrocortisone 1%
quantity_text      thin layer
phase_number_snapshot  2
is_voided          False
voided_at          None
deleted_at         None
notes              evening dose
```

## `czm application update`

Edit an existing application.

Arguments:

- `application` application ID
- `--applied-at` optional local timestamp
- `--treatment-type` optional new treatment type
- `--treatment-name` optional new treatment name
- `--quantity-text` optional new amount text
- `--notes` optional replacement notes

Example:

```bash
czm application update 1 --notes "updated note"
```

Example output:

```text
id                 1
episode_id         1
notes              updated note
```

## `czm application delete`

Mark an application as deleted.

Arguments:

- `application` application ID

Example:

```bash
czm application delete 1
```

Example output:

```text
id                 1
is_deleted         True
deleted_at         15.04.26
```

## `czm application list`

List applications for an episode.

Arguments:

- `--episode` episode ID
- `--include-voided` include voided entries as well as active ones

Example:

```bash
czm application list --episode 1
```

Example output:

```text
Applications:
- 1: 15.04.26 steroid (phase 2)
```

## `zema due list`

Show which episodes are due for treatment today.

Arguments:

- `--subject` optional subject reference to filter the list

Example:

```bash
zema due list
```

Example output:

```text
Due items:
- episode 1: phase 2, due_today=False, next_due=17.04.26
```

## `zema adherence calendar`

Show adherence days over an explicit date range or the last N local days. GET adherence commands dynamically calculate by default and do not persist rows.

Arguments:

- `--from YYYY-MM-DD` and `--to YYYY-MM-DD`, or `--last N`
- `--episode` optional episode ID
- `--subject` optional subject reference
- `--location` optional location reference
- `--persisted` read stored audit rows only

Example:

```bash
zema adherence calendar --last 30
```

Example output:

```text
Adherence calendar 2026-04-01 -> 2026-04-30

2026-04-03  missed  0/1  episode=1 phase=2
```

## `zema adherence summary`

Show adherence totals and score. The score is credited applications divided by expected applications.

Example:

```bash
zema adherence summary --last 30 --json
```

## `zema adherence missed`

Show missed adherence days. Add `--include-partial` to include partial days.

Example:

```bash
zema adherence missed --from 2026-04-01 --to 2026-04-30 --include-partial
```

## `zema adherence episode`

Show adherence summary and days for one episode.

Example:

```bash
zema adherence episode 1 --last 14
```

## `zema adherence rebuild`

Persist or rebuild adherence snapshots. This is the explicit write operation for stored audit rows.

Example:

```bash
zema adherence rebuild --episode 1 --from 2026-04-01 --to 2026-04-30
```

## `zema events list`

List episode events in timeline order.

Arguments:

- `--episode` episode ID
- `--event-type` optional event type filter

Example:

```bash
zema events list --episode 1
```

Example output:

```text
Events:
- 1: 15.04.26 episode_created (agent)
- 2: 15.04.26 healed_marked (agent)
- 3: 15.04.26 phase_entered (agent)
```

## `zema events timeline`

Show the same event stream as a timeline view.

Example:

```bash
zema events timeline --episode 1
```

Example output:

```text
Events:
- 1: 15.04.26 episode_created (agent)
- 2: 15.04.26 healed_marked (agent)
- 3: 15.04.26 phase_entered (agent)
```

## Output modes

- Use `--json` for machine-readable output
- Use `--quiet` to suppress human output for successful commands
- Use `--no-color` for terminals that should not receive colored text

## Common troubleshooting

- If you see `missing required configuration`, run `zema setup`
- If you see `unauthorized`, make sure the config contains the plaintext API key
- If a name is ambiguous, use a more specific reference or a numeric ID
