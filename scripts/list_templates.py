#!/usr/bin/env python3
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for f in sorted((root / "assets/templates").glob("*.drawio")):
    print(f.name)
