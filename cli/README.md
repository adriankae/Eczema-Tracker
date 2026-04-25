# zema

`zema` is the preferred production CLI client for the eczema treatment tracker backend. The legacy `czm` command remains available as a compatibility alias.

It talks to the real API over HTTP, uses API-key auth only, and follows the backend contract for subjects, locations, episodes, applications, due items, and events.
It supports Python 3.11 and Python 3.12.

## Quick Start

1. Follow the full getting-started tutorial: [docs/getting-started.md](docs/getting-started.md)
2. Read the command reference for the full command-by-command manual: [docs/reference.md](docs/reference.md)
3. Read the implementation notes below if you want the non-obvious behavior explained.

## Agent Skill

This repository now includes an Agent Skills-compatible skill package at [`skills/czm`](skills/czm). It is procedural guidance for agents that need to use `zema` or the legacy `czm` alias to manage eczema episodes, check what is due, log treatment applications, and inspect adherence.

Suggested use:

1. Read [skills/czm/SKILL.md](skills/czm/SKILL.md) first. In an Agent Skills-compatible runtime, this file is the entry point that the agent loader reads to decide when the skill applies and what to do next.
2. Read the reference files under [`skills/czm/references`](skills/czm/references) for exact workflows, commands, and error handling.
3. Use `zema setup` first, then `zema due list`, `zema adherence summary --last 30 --json`, `zema episode get`, `zema episode heal`, `zema episode relapse`, and `zema application log` as needed.

How loading works:

- `SKILL.md` is plain markdown with YAML frontmatter.
- The agent runtime indexes that file, looks at the `name` and `description`, and matches it to the user request.
- If the skill matches, the runtime reads the routing rules in `SKILL.md` and then the referenced files for details.
- Nothing in `skills/czm` is executed by the CLI itself; it is guidance for an agent that knows how to consume Agent Skills.

What the user has to do:

- Usually nothing inside `zema` itself.
- The skill must be available to the OpenClaw or Agent Skills runtime as files on disk, either by checking out this repository where the runtime can read it or by copying/symlinking `skills/czm` into the runtime's configured skill directory.
- If OpenClaw runs as a different Unix user, that user must also be able to read the skill files.
- Once the runtime can see the skill, requests about eczema tracking are routed to this skill automatically.
- For backend setup, `zema setup` accepts an optional `--base-url` when your backend is not on the default local Docker port.

Installer helper:

If you want a one-command install from this repository clone into a skill directory you control, run:

```bash
python3 scripts/install_skill.py --target-dir /path/to/openclaw/skills
```

That command copies `skills/czm` into `/path/to/openclaw/skills/czm`. If you prefer a symlink instead of a copy, add `--mode symlink`.

More detail: [docs/skill-install.md](docs/skill-install.md)

Example backend bootstrap with a custom URL:

```bash
zema setup \
  --username admin \
  --password admin \
  --api-key-name czm-cli \
  --timezone Europe/Berlin \
  --base-url http://backend-host:28173
```

Layout:

- [`skills/czm/SKILL.md`](skills/czm/SKILL.md)
- [`skills/czm/references/commands.md`](skills/czm/references/commands.md)
- [`skills/czm/references/workflows.md`](skills/czm/references/workflows.md)
- [`skills/czm/references/entity-resolution.md`](skills/czm/references/entity-resolution.md)
- [`skills/czm/references/error-handling.md`](skills/czm/references/error-handling.md)
- [`skills/czm/references/examples.md`](skills/czm/references/examples.md)
- [`skills/czm/references/protocol.md`](skills/czm/references/protocol.md)

## Commands

- `zema setup`
- `zema subject create`
- `zema subject list`
- `zema subject get`
- `zema location create`
- `zema location list`
- `zema location image set`
- `zema location image get`
- `zema location image remove`
- `zema episode create`
- `zema episode list`
- `zema episode get`
- `zema episode heal`
- `zema episode relapse`
- `zema application log`
- `zema application update`
- `zema application delete`
- `zema application list`
- `zema due list`
- `zema adherence calendar`
- `zema adherence summary`
- `zema adherence missed`
- `zema adherence episode <episode-id>`
- `zema adherence rebuild`
- `zema events list`

`czm` remains a backwards-compatible alias for every command above.

## Adherence

Adherence commands call the backend adherence API. GET commands are read-only by default and dynamically calculate adherence. Pass `--persisted` to read stored audit snapshots only. Use `zema adherence rebuild` to persist or rebuild snapshots.

Examples:

```bash
zema adherence calendar --last 30
zema adherence summary --last 30 --json
zema adherence missed --from 2026-04-01 --to 2026-04-30 --include-partial
zema adherence episode 1 --last 14
zema adherence rebuild --episode 1 --from 2026-04-01 --to 2026-04-30
```

For agent and gateway usage, prefer `--json` and run `zema` as an external tool or via the `zema-cli` container. Do not run Telegram, Hermes, or OpenClaw gateway code inside the backend container.

## Implementation Notes

- Config precedence is `CLI flag > environment variable > config file`.
- The config file lives at the XDG path `~/.config/czm/config.toml` by default, or the matching `XDG_CONFIG_HOME` path when that variable is set.
- The CLI uses `X-API-Key` for authentication.
- Subject resolution is deterministic: exact match, then case-insensitive match, then substring match.
- Location resolution follows the same rule set, checking both `code` and `display_name`.
- Naive local timestamps are interpreted in the configured CLI timezone and converted to UTC before being sent to the backend.
- Human-readable output renders dates in `DD.MM.YY`; phase 1 due items use `AM`/`PM` plus the date.
- JSON mode prints the backend-shaped payloads directly so the output stays strict and predictable.
- Exit codes are deterministic:
  - `0` success
  - `2` invalid request/config
  - `3` not found
  - `4` ambiguous reference
  - `5` auth failure
  - `6` conflict
  - `7` transport/server failure

## Development

Run the tests:

```bash
python3 -m pytest
```

Install editable:

```bash
PIP_INDEX_URL=https://pypi.org/simple python3 -m pip install -e .
```
