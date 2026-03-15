#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

ENGINE_GROUPS = {"project", "shape", "connect", "page", "export", "session", "repl"}


def _run(cmd: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=check)


def _run_capture(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def _parse_version(text: str) -> tuple[int, int, int] | None:
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    if not m:
        return None
    major = int(m.group(1))
    minor = int(m.group(2))
    patch = int(m.group(3) or 0)
    return (major, minor, patch)


def _python_ok(py: str) -> bool:
    p = _run_capture([py, "--version"])
    out = (p.stdout + " " + p.stderr).strip()
    ver = _parse_version(out)
    return bool(ver and ver >= (3, 10, 0))


def _best_python() -> str:
    candidates = [
        os.environ.get("DRAWIO_STUDIO_PYTHON", ""),
        "/opt/homebrew/bin/python3",
        sys.executable,
        "python3",
    ]
    for py in candidates:
        if not py:
            continue
        if shutil.which(py) or Path(py).exists():
            if _python_ok(py):
                return py
    raise SystemExit("No Python >=3.10 found. Set DRAWIO_STUDIO_PYTHON to a valid interpreter.")


def _runtime_dir(root: Path) -> Path:
    return root / ".runtime"


def _engine_bin(root: Path) -> Path:
    return _runtime_dir(root) / "venv" / "bin" / "cli-anything-drawio"


def _engine_candidates(root: Path) -> Iterable[str]:
    env_engine = os.environ.get("DRAWIO_STUDIO_ENGINE")
    if env_engine:
        yield env_engine
    local = _engine_bin(root)
    if local.exists():
        yield str(local)
    path_engine = shutil.which("cli-anything-drawio")
    if path_engine:
        yield path_engine


def find_engine(root: Path) -> str | None:
    for c in _engine_candidates(root):
        return c
    return None


def install_engine(root: Path) -> str:
    runtime = _runtime_dir(root)
    runtime.mkdir(parents=True, exist_ok=True)

    src_repo = runtime / "CLI-Anything"
    if not src_repo.exists():
        _run(["git", "clone", "--depth", "1", "https://github.com/HKUDS/CLI-Anything.git", str(src_repo)])

    harness = src_repo / "drawio" / "agent-harness"
    if not harness.exists():
        raise SystemExit(f"Drawio harness not found: {harness}")

    python_bin = _best_python()
    venv = runtime / "venv"
    if not venv.exists():
        _run([python_bin, "-m", "venv", str(venv)])

    pip = venv / "bin" / "pip"
    _run([str(pip), "install", "-U", "pip"])
    _run([str(pip), "install", "-e", str(harness)])

    engine = _engine_bin(root)
    if not engine.exists():
        raise SystemExit("Engine install finished but executable not found.")
    return str(engine)


def ensure_engine(root: Path) -> str:
    engine = find_engine(root)
    if engine:
        return engine
    raise SystemExit(
        "Drawing engine not found. Run:\n"
        "  python3 scripts/diagram_studio.py engine install\n"
        "or set DRAWIO_STUDIO_ENGINE=/path/to/cli-anything-drawio"
    )


def cmd_template_list(root: Path) -> int:
    tdir = root / "assets" / "templates"
    for f in sorted(tdir.glob("*.drawio")):
        print(f.name)
    return 0


def cmd_template_create(root: Path, style: str, output: str, replacements: str | None) -> int:
    style_map = {
        "handdrawn": "architecture-handdrawn.drawio",
        "clean": "architecture-clean.drawio",
        "dark-tech": "architecture-dark-tech.drawio",
    }
    if style not in style_map:
        raise SystemExit(f"Unknown style: {style}. Choose from: {', '.join(style_map)}")

    src = root / "assets" / "templates" / style_map[style]
    if not src.exists():
        raise SystemExit(f"Template not found: {src}")

    out = Path(output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    content = src.read_text(encoding="utf-8")

    if replacements:
        mapping = json.loads(replacements)
        for old, new in mapping.items():
            content = content.replace(str(old), str(new))

    out.write_text(content, encoding="utf-8")
    print(out)
    return 0


def cmd_engine_status(root: Path) -> int:
    engine = find_engine(root)
    if not engine:
        print("engine: NOT_FOUND")
        return 1
    print(f"engine: {engine}")
    p = _run_capture([engine, "--help"])
    print("healthy:", "yes" if p.returncode == 0 else "no")
    return 0 if p.returncode == 0 else 1


def cmd_engine_install(root: Path) -> int:
    engine = install_engine(root)
    print(f"installed: {engine}")
    return 0


def passthrough_to_engine(root: Path, argv: list[str]) -> int:
    engine = ensure_engine(root)
    result = _run([engine] + argv, check=False)
    return int(result.returncode)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Drawio Studio toolkit: templates + full diagram operations",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    sub = parser.add_subparsers(dest="sub")

    t = sub.add_parser("template", help="Template operations")
    tsub = t.add_subparsers(dest="template_sub")
    tsub.add_parser("list", help="List built-in templates")
    tc = tsub.add_parser("create", help="Create diagram from template")
    tc.add_argument("--style", required=True, choices=["handdrawn", "clean", "dark-tech"])
    tc.add_argument("--output", required=True)
    tc.add_argument("--replacements", help="JSON replacements map")

    e = sub.add_parser("engine", help="Drawing engine operations")
    esub = e.add_subparsers(dest="engine_sub")
    esub.add_parser("status", help="Check engine status")
    esub.add_parser("install", help="Install local drawing engine runtime")

    sub.add_parser("help-ops", help="Show diagram operation groups")
    return parser


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    if len(sys.argv) > 1 and sys.argv[1] in ENGINE_GROUPS:
        return passthrough_to_engine(root, sys.argv[1:])

    parser = build_parser()
    args = parser.parse_args()

    if args.sub == "template":
        if args.template_sub == "list":
            return cmd_template_list(root)
        if args.template_sub == "create":
            return cmd_template_create(root, args.style, args.output, args.replacements)
        parser.error("template requires a subcommand: list|create")

    if args.sub == "engine":
        if args.engine_sub == "status":
            return cmd_engine_status(root)
        if args.engine_sub == "install":
            return cmd_engine_install(root)
        parser.error("engine requires a subcommand: status|install")

    if args.sub == "help-ops":
        print("Operation groups available:")
        print("  project  - new/open/save/info/xml/presets")
        print("  shape    - add/remove/list/label/move/resize/style/info/types")
        print("  connect  - add/remove/label/style/list/styles")
        print("  page     - add/remove/rename/list")
        print("  export   - render/formats")
        print("  session  - status/undo/redo/save-state/list")
        print("  repl     - interactive mode")
        print("\nExample:")
        print("  python3 scripts/diagram_studio.py project new --preset 16:9 -o ~/Desktop/ai/demo.drawio")
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
