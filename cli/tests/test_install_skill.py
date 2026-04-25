from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install_skill.py"


def test_install_skill_copy_mode(tmp_path):
    target = tmp_path / "skills"
    result = subprocess.run(
        ["python3", str(SCRIPT), "--target-dir", str(target)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert (target / "czm" / "SKILL.md").exists()
    assert (target / "czm" / "references" / "commands.md").exists()
    assert "Installed czm skill" in result.stdout


def test_install_skill_requires_overwrite(tmp_path):
    target = tmp_path / "skills"
    (target / "czm").mkdir(parents=True)
    result = subprocess.run(
        ["python3", str(SCRIPT), "--target-dir", str(target)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "already exists" in result.stderr
