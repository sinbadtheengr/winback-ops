"""Restricted subprocess runner for generated segmentation scripts."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from app.core.models import SegmentationResult

ALLOWED_IMPORTS = {"pandas", "numpy", "datetime", "json", "re"}


class SandboxError(RuntimeError):
    pass


def _validate_source(source: str) -> None:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise SandboxError(f"Generated code has invalid syntax: {exc.msg}") from exc
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [item.name.split(".")[0] for item in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [(node.module or "").split(".")[0]]
        else:
            continue
        if any(name not in ALLOWED_IMPORTS for name in names):
            raise SandboxError("Generated code imports a module outside the sandbox allowlist.")


def execute(source: str, csv_path: Path) -> SegmentationResult:
    _validate_source(source)
    with tempfile.TemporaryDirectory(prefix="winback-segment-") as directory:
        script = Path(directory) / "segment.py"
        script.write_text(source, encoding="utf-8")
        try:
            completed = subprocess.run(
                [sys.executable, str(script), str(csv_path)],
                cwd=directory,
                capture_output=True,
                check=False,
                text=True,
                timeout=30,
            )
        except subprocess.TimeoutExpired as exc:
            raise SandboxError("Generated code exceeded the 30-second sandbox limit.") from exc
    if completed.returncode != 0:
        raise SandboxError(completed.stderr[-2000:] or "Generated code exited unsuccessfully.")
    try:
        return SegmentationResult.model_validate_json(completed.stdout)
    except (ValueError, json.JSONDecodeError) as exc:
        raise SandboxError("Generated code did not emit the required segmentation JSON.") from exc
