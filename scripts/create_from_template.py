#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a drawio file from a style template")
    parser.add_argument("--template", required=True, help="Template name: handdrawn|clean|dark-tech")
    parser.add_argument("--output", required=True, help="Output .drawio path")
    parser.add_argument(
        "--replacements",
        help="Optional JSON object for text replacements, e.g. '{\"Architecture Diagram (Dark Tech Template)\":\"My System\"}'",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    templates = {
        "handdrawn": root / "assets/templates/architecture-handdrawn.drawio",
        "clean": root / "assets/templates/architecture-clean.drawio",
        "dark-tech": root / "assets/templates/architecture-dark-tech.drawio",
    }

    if args.template not in templates:
        raise SystemExit(f"Unknown template '{args.template}'. Use one of: {', '.join(templates)}")

    src = templates[args.template]
    out = Path(args.output).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    content = src.read_text(encoding="utf-8")

    if args.replacements:
        mapping = json.loads(args.replacements)
        for old, new in mapping.items():
            content = content.replace(str(old), str(new))

    out.write_text(content, encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
