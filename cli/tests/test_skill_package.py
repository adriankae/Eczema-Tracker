from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "skills" / "czm"


def test_skill_structure_exists():
    expected = [
        SKILL_DIR / "SKILL.md",
        SKILL_DIR / "references" / "commands.md",
        SKILL_DIR / "references" / "workflows.md",
        SKILL_DIR / "references" / "entity-resolution.md",
        SKILL_DIR / "references" / "error-handling.md",
        SKILL_DIR / "references" / "examples.md",
        SKILL_DIR / "references" / "protocol.md",
    ]
    for path in expected:
        assert path.exists(), f"missing skill file: {path}"


def test_skill_frontmatter_and_references():
    skill = (SKILL_DIR / "SKILL.md").read_text(encoding="utf-8")
    assert skill.startswith("---\n")
    assert re.search(r"^name:\s*czm\s*$", skill, re.MULTILINE)
    assert re.search(r"^description:\s*.*czm CLI.*$", skill, re.MULTILINE)
    for ref in [
        "references/commands.md",
        "references/workflows.md",
        "references/entity-resolution.md",
        "references/protocol.md",
        "references/error-handling.md",
        "references/examples.md",
    ]:
        assert ref in skill


def test_protocol_reference_mentions_backend_rules():
    protocol = (SKILL_DIR / "references" / "protocol.md").read_text(encoding="utf-8")
    for token in [
        "active_flare",
        "in_taper",
        "obsolete",
        "Phase 1",
        "Phase 7",
        "relapse is not a persistent status",
        "backend-owned automatic transitions",
        "czm due list",
    ]:
        assert token.lower() in protocol.lower()


def test_command_reference_mentions_real_commands():
    commands = (SKILL_DIR / "references" / "commands.md").read_text(encoding="utf-8")
    for command in [
        "czm setup",
        "czm subject create",
        "czm subject list",
        "czm subject get",
        "czm location create",
        "czm location list",
        "czm episode create",
        "czm episode list",
        "czm episode get",
        "czm episode heal",
        "czm episode relapse",
        "czm application log",
        "czm application update",
        "czm application delete",
        "czm application list",
        "czm due list",
        "czm events list",
        "czm events timeline",
    ]:
        assert command in commands
