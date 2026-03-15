---
name: drawio-studio
description: Create, edit, and export drawio diagrams with template-first workflow and full diagram operations. Use when asked to generate architecture charts, process flows, system diagrams, or style-customized drawio files.
---

# Drawio Studio

Use this skill to quickly create and refine drawio diagrams.

## Workflow

1. If user needs fast output, start with template creation (`template create`).
2. If user needs precise editing, use operation groups (`project/shape/connect/page/export`).
3. Export as PNG/PDF/SVG when requested.

## Commands

### Template operations

```bash
python3 scripts/diagram_studio.py template list
python3 scripts/diagram_studio.py template create --style handdrawn --output ~/Desktop/ai/demo.drawio
python3 scripts/diagram_studio.py template create --style dark-tech --output ~/Desktop/ai/demo.drawio --replacements '{"Architecture Diagram (Dark Tech Template)":"My Architecture"}'
```

### Engine lifecycle

```bash
python3 scripts/diagram_studio.py engine install
python3 scripts/diagram_studio.py engine status
```

### Full operation groups

```bash
python3 scripts/diagram_studio.py project new --preset 16:9 -o ~/Desktop/ai/demo.drawio
python3 scripts/diagram_studio.py shape add rectangle -l "Gateway" --x 120 --y 120
python3 scripts/diagram_studio.py connect add <source_id> <target_id> --style orthogonal -l "API"
python3 scripts/diagram_studio.py export render ~/Desktop/ai/demo.png -f png
```

Use `python3 scripts/diagram_studio.py help-ops` for all supported operation groups.

## Styles

- `handdrawn` — whiteboard / storytelling
- `clean` — business report
- `dark-tech` — presentation / demo

Templates are in `assets/templates/`.
