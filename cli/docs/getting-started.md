# Getting Started

This is the only onboarding guide you need. It covers install, backend startup, bootstrap, config creation, and the first commands that actually work.

Supported Python versions: 3.11 and 3.12.

`zema` is the preferred command name. `czm` remains available as a backwards-compatible alias.

## 1. Install `zema`

Create a virtual environment and install the CLI:

```bash
python3 -m venv .venv
source .venv/bin/activate
PIP_INDEX_URL=https://pypi.org/simple python3 -m pip install -e .
```

If `zema` is not on your `PATH`, use the binary from the virtual environment or add the user bin directory shown by `pip` to `PATH`.

## 2. Start the backend

Open the backend repository and start Docker:

```bash
cd /path/to/Eczema-Tracker
docker compose up -d --build
```

Confirm the API is alive:

```bash
curl -sS http://localhost:28173/health
```

Expected response:

```json
{"status":"ok"}
```

This tutorial assumes the backend is on `http://localhost:28173`. If your backend is running on a different host or port, pass `--base-url` to `zema setup`.

For example, if the backend is reachable at a Docker service name or another host:

```bash
zema setup \
  --username admin \
  --password admin \
  --api-key-name czm-cli \
  --timezone Europe/Berlin \
  --base-url http://backend-host:28173
```

## 3. Create the config automatically

This is the part that was missing before. Instead of manually copying a bearer token and then manually creating an API key, use `zema setup`.

The backend seeds these credentials on first start:

- username: `admin`
- password: `admin`

Run:

```bash
zema setup \
  --username admin \
  --password admin \
  --api-key-name czm-cli \
  --timezone Europe/Berlin
```

What this does:

1. logs into the backend with the username/password
2. creates an API key through the backend
3. writes `~/.config/czm/config.toml` or `$XDG_CONFIG_HOME/czm/config.toml`

Example config that gets written:

```toml
base_url = "http://localhost:28173"
api_key = "plaintext-api-key-from-the-backend"
timezone = "Europe/Berlin"
```

If your backend is running in another timezone, pass that timezone here instead. The CLI uses it to interpret naive local timestamps.

## 4. Run your first command

Now the CLI should work without extra flags:

```bash
zema subject list
```

If nothing exists yet, the output should be:

```text
No subjects.
```

## 5. Create your first subject and location

```bash
zema subject create --display-name "Child A"
zema location create --code left_elbow --display-name "Left elbow"
```

List them to confirm:

```bash
zema subject list
zema location list
```

## 6. Create an episode

Use the exact names you just created:

```bash
zema episode create --subject "Child A" --location "Left elbow"
```

The CLI resolves text references in this order:

1. exact match
2. case-insensitive match
3. substring match

If multiple items match at the same step, the CLI stops and tells you the reference is ambiguous instead of guessing.

## 7. Heal, log, and inspect

Once you have an episode, try the rest of the workflow:

```bash
zema episode heal 1
zema application log --episode 1 --treatment-type steroid --treatment-name "Hydrocortisone 1%" --quantity-text "thin layer" --notes "morning dose"
zema application list --episode 1
zema due list
zema adherence summary --last 30
zema events list --episode 1
```

Add `--json` if you want machine-readable output instead of the human format.

## 8. If something fails

- `missing required configuration`: run `zema setup`
- `unauthorized`: check that the API key came from `zema setup`, not the bearer token from login
- `reference '...' is ambiguous`: use a fuller name or the numeric ID
- `transport_error`: confirm the backend is still running on `http://localhost:28173`

## 9. Read the command reference

When you are ready to explore every command in detail, including descriptions and examples, open:

- [docs/reference.md](reference.md)

## 10. What the setup command looks like under the hood

If you want to understand the manual backend flow, `zema setup` is replacing this sequence:

```bash
ACCESS_TOKEN=$(
  curl -sS -X POST http://localhost:28173/auth/login \
    -H 'Content-Type: application/json' \
    -d '{"username":"admin","password":"admin"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])'
)

curl -sS -X POST http://localhost:28173/api-keys \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"name":"czm-cli"}'
```

You no longer need to do that by hand for normal use. It is there only to show what the bootstrap step is doing for you.
