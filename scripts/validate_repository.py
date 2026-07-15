#!/usr/bin/env python3
"""Validate committed JSON Schema instances and repository-local Markdown links."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError

ROOT = Path(__file__).resolve().parents[1]

SCHEMA_CASES: dict[str, tuple[str, ...]] = {
    "schemas/capability-v0.1.schema.json": ("configs/models/starwam-capabilities-v0.1.json",),
    "schemas/intervention-v0.1.schema.json": (
        "schemas/examples/intervention-pointmass-v0.1.json",
        "schemas/examples/intervention-manipulation-v0.1.json",
    ),
    "schemas/result-v0.1.schema.json": (
        "examples/pointmass-demo/summary.json",
        "examples/blockpush-demo/summary.json",
        "examples/gripper-catch-demo/summary.json",
    ),
    "release/evidence-manifest-v0.1.schema.json": ("release/evidence-manifest-v0.1.json",),
}

INLINE_LINK = re.compile(
    r"!?\[[^\]\n]*\]\(\s*(?P<target><[^>\n]+>|[^\s)]+)",
)
REFERENCE_LINK = re.compile(
    r"^\s*\[[^\]\n]+\]:\s*(?P<target><[^>\n]+>|\S+)",
    flags=re.MULTILINE,
)
HEADING = re.compile(r"^ {0,3}#{1,6}\s+(?P<text>.+?)\s*#*\s*$", flags=re.MULTILINE)


class RepositoryValidationError(RuntimeError):
    """Raised when a committed repository contract is invalid."""


def _load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_schemas(root: Path) -> tuple[int, int]:
    """Check every public schema and its committed canonical instances."""

    failures: list[str] = []
    instance_count = 0
    for schema_name, instance_names in SCHEMA_CASES.items():
        schema_path = root / schema_name
        try:
            schema = _load_json(schema_path)
            Draft202012Validator.check_schema(schema)
            validator = Draft202012Validator(schema)
        except (OSError, json.JSONDecodeError, SchemaError) as error:
            failures.append(f"{schema_name}: invalid schema: {error}")
            continue

        for instance_name in instance_names:
            instance_count += 1
            try:
                instance = _load_json(root / instance_name)
            except (OSError, json.JSONDecodeError) as error:
                failures.append(f"{instance_name}: invalid JSON: {error}")
                continue
            errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
            for error in errors:
                location = "/".join(str(part) for part in error.absolute_path) or "<root>"
                failures.append(f"{instance_name}:{location}: {error.message}")

    if failures:
        raise RepositoryValidationError("JSON Schema validation failed:\n" + "\n".join(failures))
    return len(SCHEMA_CASES), instance_count


def _without_fenced_code(markdown: str) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in markdown.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker is not None:
            current = marker.group(1)[0]
            if fence is None:
                fence = current
            elif fence == current:
                fence = None
            output.append("")
        elif fence is None:
            output.append(line)
        else:
            output.append("")
    return "\n".join(output)


def _markdown_files(root: Path) -> list[Path]:
    command = [
        "git",
        "-C",
        str(root),
        "ls-files",
        "--cached",
        "--others",
        "--exclude-standard",
        "-z",
        "--",
        "*.md",
    ]
    try:
        result = subprocess.run(command, check=True, capture_output=True)
    except (OSError, subprocess.CalledProcessError):
        excluded = {
            ".git",
            ".venv",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            "dist",
            "runs",
            "site",
            "vendor",
        }
        return sorted(
            path
            for path in root.rglob("*.md")
            if not any(part in excluded for part in path.relative_to(root).parts)
        )
    return sorted(root / Path(name.decode("utf-8")) for name in result.stdout.split(b"\0") if name)


def _slug(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text).strip().lower()
    characters = [
        character
        for character in text
        if character in {" ", "-", "_"} or unicodedata.category(character).startswith(("L", "N"))
    ]
    return "".join(characters).replace(" ", "-")


def _anchors(path: Path) -> set[str]:
    markdown = _without_fenced_code(path.read_text(encoding="utf-8"))
    occurrences: defaultdict[str, int] = defaultdict(int)
    anchors: set[str] = set()
    for match in HEADING.finditer(markdown):
        base = _slug(match.group("text"))
        count = occurrences[base]
        occurrences[base] += 1
        anchors.add(base if count == 0 else f"{base}-{count}")
    return anchors


def _targets(markdown: str) -> list[str]:
    content = _without_fenced_code(markdown)
    matches = list(INLINE_LINK.finditer(content)) + list(REFERENCE_LINK.finditer(content))
    return [match.group("target").strip("<>") for match in matches]


def validate_markdown_links(root: Path) -> tuple[int, int]:
    """Check repository-local file targets and Markdown heading fragments."""

    failures: list[str] = []
    links_checked = 0
    root_resolved = root.resolve()
    for source in _markdown_files(root):
        relative_source = source.relative_to(root)
        try:
            targets = _targets(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError) as error:
            failures.append(f"{relative_source}: cannot read Markdown: {error}")
            continue
        for target in targets:
            parsed = urlsplit(target)
            if parsed.scheme or parsed.netloc or target.startswith("//"):
                continue
            links_checked += 1
            local_name = unquote(parsed.path)
            if local_name:
                if local_name.startswith("/"):
                    failures.append(
                        f"{relative_source}: repository-local link is absolute: {target}"
                    )
                    continue
                destination = (source.parent / local_name).resolve()
            else:
                destination = source.resolve()
            try:
                destination.relative_to(root_resolved)
            except ValueError:
                failures.append(f"{relative_source}: link escapes repository: {target}")
                continue
            if not destination.exists():
                failures.append(f"{relative_source}: missing link target: {target}")
                continue
            if parsed.fragment and destination.suffix.lower() == ".md":
                fragment = unquote(parsed.fragment).removeprefix("user-content-")
                if fragment not in _anchors(destination):
                    failures.append(f"{relative_source}: missing Markdown anchor: {target}")

    if failures:
        raise RepositoryValidationError("Markdown link validation failed:\n" + "\n".join(failures))
    return len(_markdown_files(root)), links_checked


def main() -> int:
    """Run all repository-level validation gates."""

    try:
        schema_count, instance_count = validate_schemas(ROOT)
        markdown_count, link_count = validate_markdown_links(ROOT)
    except RepositoryValidationError as error:
        print(error, file=sys.stderr)
        return 1
    print(f"Validated {instance_count} instances against {schema_count} Draft 2020-12 JSON Schemas")
    print(f"Checked {link_count} repository-local links across {markdown_count} Markdown files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
