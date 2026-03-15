---
name: drawio-studio
description: Create and refine drawio diagrams in multiple styles (hand-drawn, clean business, dark tech), especially for architecture charts, process flows, and technical explanation visuals. Use when asked to generate, beautify, or template-driven produce .drawio outputs for sharing or documentation.
---

# Drawio Studio

Use template-first workflow to produce consistent drawio outputs quickly.

## Workflow

1. Choose style template:
   - `handdrawn` (whiteboard style)
   - `clean` (business/report style)
   - `dark-tech` (presentation style)
2. Copy template to target output path.
3. Apply optional text replacements.
4. Return the generated `.drawio` file path.

## Commands

```bash
python3 scripts/list_templates.py
python3 scripts/create_from_template.py --template clean --output ~/Desktop/ai/my-architecture.drawio
python3 scripts/create_from_template.py --template dark-tech --output ~/Desktop/ai/my-architecture.drawio --replacements '{"Architecture Diagram (Dark Tech Template)":"My Product Architecture"}'
```

## Templates

- `assets/templates/architecture-handdrawn.drawio`
- `assets/templates/architecture-clean.drawio`
- `assets/templates/architecture-dark-tech.drawio`

## Editing guidance

- Prefer short layer labels and consistent arrow semantics.
- Keep one main reading direction (top-down or left-right).
- Avoid crossing arrows unless necessary.
- Keep one legend/note block describing the main flow.
