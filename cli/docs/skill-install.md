# Skill Install Helper

This repository ships an install helper for the `czm` Agent Skill.

## What It Does

The helper copies or symlinks the repository's `skills/czm` folder into a skill directory that your agent runtime already watches.

It does not modify `czm` itself and it does not guess the runtime's skill directory.

## Command

```bash
python3 scripts/install_skill.py --target-dir /path/to/openclaw/skills
```

This creates:

```text
/path/to/openclaw/skills/czm/SKILL.md
/path/to/openclaw/skills/czm/references/...
```

## Options

- `--mode copy` copies files into the target directory. This is the default.
- `--mode symlink` creates a symlink to the repository's `skills/czm` folder.
- `--overwrite` replaces an existing `czm` skill install at the destination.

## Example

```bash
python3 scripts/install_skill.py \
  --target-dir ~/.config/openclaw/skills \
  --mode copy
```

## After Installation

Tell your OpenClaw or Agent Skills runtime to read the target skill directory. Once it can see `SKILL.md`, it can route eczema-tracking requests to the `czm` skill automatically.
