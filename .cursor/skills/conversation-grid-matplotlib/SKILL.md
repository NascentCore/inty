---
name: grid-diagram-matplotlib
description: >-
  General-purpose labeled grid / matrix diagram from YAML via matplotlib to PNG:
  row-column headers, bilingual or dense cell text, taxonomies, capability maps,
  or any strict rectangular layout. Prefer over Mermaid when you need aligned
  cells, reproducible CI-friendly exports, or precise typography control.
---

# Grid diagram (matplotlib + YAML)

## When to use

- Need a **true matrix** (aligned rows/columns), not Mermaid `flowchart` auto-layout.
- Content is **edited as data** (YAML); output is **PNG** (slides, docs, PR attachments).
- Examples: taxonomy grids, bilingual matrices, product/conversation capability maps.

## Setup

From repo root (once per environment):

```bash
pip install -r .cursor/skills/conversation-grid-matplotlib/requirements.txt
```

Requires `matplotlib` and `PyYAML`. Uses `Agg` backend (no display).

## Run

```bash
python3 tools/scripts/draw_labeled_grid.py \
  PATH/to/config.yaml \
  -o PATH/to/output.png
```

## YAML schema

| Key | Required | Meaning |
|-----|----------|---------|
| `title` | No | Figure title (string; supports `\n` and `<br/>`) |
| `rows` | Yes | List of rows; each row is a list of **equal-length** cell strings |
| `layout` | No | `fig_width_in`, `fig_height_in`, `dpi` |
| `style` | No | Colors, `linewidth`, font sizes, optional `font_family` (string) |

**Layout convention** (matches the Inty example):

- Row 0: corner cell (often y-axis hint), then **column headers** (x-axis).
- Rows 1..n: **row label** in column 0, body cells in columns 1..n-1.

Row 0 column 0 and the rest of row 0 use `font_size_header`; any cell with `r==0` or `c==0` uses header size; inner cells use `font_size_cell`.

## Example config

Checked-in sample: [/docs/companion_harness/conversation_intelligence_realtime_grid.yaml](/docs/companion_harness/conversation_intelligence_realtime_grid.yaml).

## Verify

```bash
python3 tools/scripts/draw_labeled_grid.py \
  docs/companion_harness/conversation_intelligence_realtime_grid.yaml \
  -o /tmp/conversation_grid_matplotlib.png
```

In this repo the doc figure is checked in as [/docs/companion_harness/conversation_intelligence_realtime_grid.png](/docs/companion_harness/conversation_intelligence_realtime_grid.png) (same command with `-o docs/companion_harness/conversation_intelligence_realtime_grid.png` from repo root).

Open the PNG to confirm CJK fonts (macOS: PingFang SC in default stack).
