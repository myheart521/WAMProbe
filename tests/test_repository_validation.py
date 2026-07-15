import subprocess
import sys
from pathlib import Path


def test_repository_schemas_and_markdown_links_are_valid() -> None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [sys.executable, "scripts/validate_repository.py"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Draft 2020-12 JSON Schemas" in result.stdout
    assert "repository-local links" in result.stdout
