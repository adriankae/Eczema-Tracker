# Workflows

This file gives procedural guidance for common agent tasks.

## Start a New Flare Episode

1. Resolve the subject name.
2. Resolve the body location.
3. Create the episode.
4. Confirm the returned episode shows `status = active_flare` and `current_phase_number = 1`.

Commands:

```bash
czm subject list
czm location list
czm episode create --subject "Child A" --location "Left elbow"
```

Tell the user:

- the episode has started
- the backend created phase 1
- the exact episode ID returned by the CLI

## Ask What Is Due Today

1. Run `czm due list`.
2. If needed, filter by subject.
3. Summarize the due status and next due date from the backend response.

Commands:

```bash
czm due list
czm due list --subject "Child A"
```

Tell the user:

- whether anything is due today
- when the next due time is
- whether the episode is in flare or taper

## Mark a Flare Healed

1. Resolve the episode.
2. Call `czm episode heal`.
3. Confirm the backend returned `status = in_taper` and `current_phase_number = 2`.

Commands:

```bash
czm episode heal 1
```

If the user gave a local time, include `--healed-at`.

Tell the user:

- taper has started
- the episode is now phase 2
- the backend is authoritative for the new due schedule

## Report Relapse

1. Resolve the episode.
2. Confirm the episode is currently in taper.
3. Run `czm episode relapse`.
4. Confirm the backend reset the episode to phase 1 / `active_flare`.

Commands:

```bash
czm episode relapse 1 [--reason symptoms_returned]
```

Tell the user:

- relapse was recorded
- the episode is back in flare state
- a new taper cycle may begin only after a future heal action

## Log Treatment Application

1. Resolve the episode.
2. Collect the application time and treatment details.
3. Log the application.
4. Confirm the application ID returned by the backend.

Commands:

```bash
czm application log --episode 1 --treatment-type steroid --treatment-name "Hydrocortisone 1%" --quantity-text "thin layer" --notes "morning dose"
```

Tell the user:

- the application was recorded
- the exact time used
- the episode it was attached to

## Daily Taper Guidance

1. Ask the backend what is due today.
2. If the episode is in flare, guide the user to the phase 1 schedule using the backend response.
3. If the episode is in taper, use `czm due list` and `czm events list` to explain the current state.
4. Never guess the next phase or due time yourself.

Commands:

```bash
czm due list
czm events list --episode 1
```

Tell the user:

- the current phase
- whether anything is due now
- what action, if any, the backend indicates
