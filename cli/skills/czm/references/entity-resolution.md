# Entity Resolution

The CLI resolves subjects and locations deterministically. Do not guess.

## Subject Resolution

Use the real CLI behavior:

1. exact match
2. case-insensitive match
3. substring match

If a reference matches more than one subject at the same precedence level, the result is ambiguous.

Rules:

- never silently choose one match
- never fabricate a subject ID
- if ambiguous, ask the user to narrow it down
- if not found, say so clearly and ask for a better reference or an ID

## Location Resolution

Location resolution follows the same deterministic order:

1. exact match
2. case-insensitive match
3. substring match

The CLI checks both location `code` and `display_name`.

Rules:

- use the most specific location reference available
- never guess between two similar body locations
- if ambiguous, ask for clarification
- if not found, suggest creating the location or using the exact code

## Episode Selection

The backend spec defines episode selection for a subject/location pair like this:

1. fetch all episodes for the subject and location
2. if none, treat it as not found
3. if one active episode exists, use it
4. if multiple active episodes exist, treat it as ambiguous
5. otherwise use the most recent episode in any state

The CLI does not expose a direct subject+location episode resolver, so agents should only rely on IDs returned by the CLI or on the backend responses they just fetched.

Preferred sequence:

1. resolve subject
2. resolve location
3. create or inspect the episode by returned ID

If the CLI/backend prevents duplicate active or tapering episodes for the same subject/location, do not attempt to work around that.

## Forbidden Behavior

- do not infer IDs from memory
- do not select the first returned result when there are multiple matches
- do not assume a typo should resolve to a subject or location
- do not fabricate a fallback subject or location
