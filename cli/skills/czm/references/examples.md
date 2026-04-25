# Examples

These examples map natural German requests to `czm` workflows.

## „Mein Ekzem ist am linken Ellenbogen wieder aufgeflammt.“

Command plan:

1. Resolve subject.
2. Resolve location `left_elbow`.
3. Create a new episode if one does not already exist.

Command pattern:

```bash
zema episode create --subject "<subject>" --location "left_elbow"
```

Expected interpretation:

- the episode starts in phase 1
- the backend returns the new episode ID
- if the location is ambiguous, ask for clarification before creating anything

## „Der Schub an meinem Hals ist verheilt.“

Command plan:

1. Resolve the episode for that subject/location.
2. Mark it healed.

Command pattern:

```bash
zema episode heal <episode-id>
```

Expected interpretation:

- the episode moves to `in_taper`
- the backend sets phase 2
- the user should now follow the taper schedule from `zema due list`

## „Meine rechte Hand hat wieder einen Rückfall.“

Command plan:

1. Resolve subject and location.
2. Find the current episode.
3. Report relapse if the episode is in taper.

Command pattern:

```bash
zema episode relapse <episode-id> [--reason "symptoms_returned"]
```

Expected interpretation:

- the episode returns to `active_flare`
- phase number resets to 1
- the backend records relapse as an event, not a permanent status

## „Was muss ich heute auftragen?“

Command plan:

1. Query the backend due list.
2. Summarize the due item(s) in plain language.

Command pattern:

```bash
zema due list
```

Expected interpretation:

- the agent tells the user what is due today
- the agent does not invent a schedule
- the answer comes from backend due logic

## „Ich habe um 20:30 Hydrocortison auf den linken Ellenbogen aufgetragen.“

Command plan:

1. Resolve the subject.
2. Resolve the location.
3. Resolve the episode.
4. Log the application.

Command pattern:

```bash
zema application log --episode <episode-id> --applied-at 2026-04-15T20:30:00 --treatment-type steroid --treatment-name "Hydrocortisone 1%" --quantity-text "thin layer"
```

Expected interpretation:

- the application is stored with the configured timezone interpreted as local time
- the backend converts and stores the timestamp in UTC
- the agent can then summarize the logged treatment back to the user
