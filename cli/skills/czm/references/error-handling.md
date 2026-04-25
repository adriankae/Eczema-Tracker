# Error Handling

The agent should respond to CLI/backend failures deterministically and without guessing.

## Exit Codes

The CLI currently uses these exit codes:

- `0` success
- `2` invalid request or configuration
- `3` not found
- `4` ambiguous reference
- `5` auth failure
- `6` conflict
- `7` transport or server failure

## Invalid Request or Config

Examples:

- missing `base_url`
- missing `api_key`
- invalid timestamps or IDs

Agent action:

- explain what is missing
- ask the user to run `czm setup` or supply the missing flag

## Not Found

Examples:

- subject does not exist
- location does not exist
- episode does not exist
- application does not exist

Agent action:

- tell the user the entity was not found
- ask for a different reference or a numeric ID

## Ambiguity

Examples:

- multiple subjects match the same name fragment
- multiple locations match the same code/name fragment

Agent action:

- stop
- ask for clarification
- do not continue with a guessed match

## Auth Failures

Examples:

- invalid API key
- expired or rejected backend token during setup

Agent action:

- tell the user to rerun `czm setup`
- verify the backend URL and credentials

## Conflict or State-Transition Failure

Examples:

- trying to heal an episode that is not in phase 1
- trying to relapse when the backend rejects the current state
- trying to delete or update a record that no longer exists in the expected state

Agent action:

- explain that the backend rejected the state transition
- do not claim success
- ask the user to inspect the current episode state with `czm episode get` or `czm events list`

## Transport or Server Failure

Examples:

- backend not reachable
- connection refused
- server returns an unexpected error

Agent action:

- confirm the backend is running
- confirm the base URL
- retry only if the user asks

