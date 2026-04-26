# Commands

Use the real `zema` CLI (`czm` remains a compatibility alias) commands below. The skill should not invent extra flags or workflows.

## Setup

`zema setup`

Purpose:

- logs into the backend
- creates a CLI API key
- writes the local config file

Common usage:

```bash
zema setup --username admin --password admin --api-key-name czm-cli
```

Default backend base URL:

```text
http://localhost:28173
```

Override if needed:

```bash
zema setup --base-url http://localhost:28173 --username admin --password admin
```

Telegram config foundation:

```bash
zema setup telegram --api-key "$CZM_API_KEY" --bot-token "$ZEMA_TELEGRAM_BOT_TOKEN" --allowed-chat-id 123456789 --yes
zema telegram status
zema telegram test
zema telegram config show
zema telegram run
zema config show
```

Secrets are masked by default in config output.

Telegram runtime:

- Prefer `/start` or `/menu` for button-driven workflows.
- Buttons support due-now items, quick treatment logging, subject create/delete workflows, location workflows, location image photo upload, start episode, heal/relapse, and adherence.
- Typed slash commands are fallback shortcuts.
- The bot does not support arbitrary `/zema ...` passthrough or shell execution.

Telegram environment variables:

```text
ZEMA_TELEGRAM_BOT_TOKEN
ZEMA_TELEGRAM_ALLOWED_CHAT_IDS
ZEMA_TELEGRAM_ALLOWED_USER_IDS
ZEMA_TELEGRAM_ALLOW_WRITES
ZEMA_TELEGRAM_ALLOW_ADHERENCE_REBUILD
```

## Subjects

`zema subject create --display-name "<name>"`

`zema subject list`

`zema subject get <subject>`

Examples:

```bash
zema subject create --display-name "Child A"
zema subject list
zema subject get "Child A"
```

## Locations

`zema location create --code <code> --display-name "<label>" [--image <path>]`

`zema location list`

`zema location image set <location> <path>`

`zema location image get <location> --output <path>`

`zema location image remove <location>`

Examples:

```bash
zema location create --code left_elbow --display-name "Left elbow"
zema location create --code left_elbow --display-name "Left elbow" --image ./left-elbow.jpg
zema location image set left_elbow ./left-elbow.jpg
zema location image get left_elbow --output ./left-elbow.jpg
zema location image remove left_elbow
zema location list
```

## Episodes

`zema episode create --subject <subject> --location <location> [--protocol-version v1]`

`zema episode list [--subject <subject>] [--status <status>]`

`zema episode get <episode>`

`zema episode heal <episode> [--healed-at <local-timestamp>]`

`zema episode relapse <episode> [--reason <text>] [--reported-at <local-timestamp>]`

Examples:

```bash
zema episode create --subject "Child A" --location "Left elbow"
zema episode heal 1 --healed-at 2026-04-15T18:00:00
zema episode relapse 1 --reason symptoms_returned --reported-at 2026-04-15T21:00:00
```

## Applications

`zema application log --episode <episode> [--treatment-type <type>] [--applied-at <local-timestamp>] [--treatment-name <name>] [--quantity-text <text>] [--notes <text>]`

`zema application update <application> [--applied-at <local-timestamp>] [--treatment-type <type>] [--treatment-name <name>] [--quantity-text <text>] [--notes <text>]`

`zema application delete <application>`

`zema application list --episode <episode> [--include-voided]`

Example:

```bash
zema application log --episode 1 --treatment-type steroid --treatment-name "Hydrocortisone 1%" --quantity-text "thin layer"
```

For quick habit/adherence logging, only `--episode` is required. If omitted, `--treatment-type` is stored as `other`.

## Due and Events

`zema due list [--subject <subject>]`

`zema events list --episode <episode> [--event-type <type>]`

`zema events timeline --episode <episode>`

Examples:

```bash
zema due list
zema events list --episode 1
```

## Adherence

Use `zema adherence` commands for audit-style adherence workflows. These commands call backend APIs; they do not implement adherence logic locally.

Commands:

- `zema adherence calendar --last <days>`
- `zema adherence summary --last <days> [--json]`
- `zema adherence missed --from <YYYY-MM-DD> --to <YYYY-MM-DD> [--include-partial]`
- `zema adherence episode <episode-id> --last <days>`
- `zema adherence rebuild [--episode <episode-id>] --from <YYYY-MM-DD> --to <YYYY-MM-DD>`

For Telegram, Hermes, OpenClaw, and other gateways, call `zema` or `czm` as an external tool, or run the `zema-cli` container. Do not run gateway code inside `zema-be`. Prefer `--json` for agent-safe output.

## Legacy Alias Commands

The preferred executable is `zema`, but these `czm` compatibility aliases remain valid:

- `czm setup`
- `czm subject create`
- `czm subject list`
- `czm subject get`
- `czm location create`
- `czm location list`
- `czm location image set`
- `czm location image get`
- `czm location image remove`
- `czm episode create`
- `czm episode list`
- `czm episode get`
- `czm episode heal`
- `czm episode relapse`
- `czm application log`
- `czm application update`
- `czm application delete`
- `czm application list`
- `czm due list`
- `czm events list`
- `czm events timeline`

## Output Modes

- Use `--json` for machine-readable output
- Use `--quiet` to suppress human output on success
- Use `--no-color` for terminals that should not emit color

## Auth and Config

- The CLI authenticates with `X-API-Key`
- Configuration precedence is `CLI flag > environment variable > config file`
- The config file lives at `~/.config/czm/config.toml` or `$XDG_CONFIG_HOME/czm/config.toml`
