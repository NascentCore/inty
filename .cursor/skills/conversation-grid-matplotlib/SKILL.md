---
name: conversation-grid-matplotlib
description: >-
  Renders a rectangular labeled grid diagram (axes + matrix cells) from a YAML
  file using matplotlib and writes PNG. Use when the user needs a strict table
  layout for bilingual or Chinese taxonomy grids (e.g. intelligence x
  realtime conversation map), reproducible exports, or CI-friendly figures without
  relying on Mermaid layout.
---

# Conversation grid (matplotlib + YAML)

## When to use

- Need a **true matrix** (aligned rows/columns), not Mermaid `flowchart` auto-layout.
- Content is **edited as data** (YAML); output is **PNG** (slides, docs, PR attachments).

## Setup

From repo root (once per environment):

```bash
pip install -r .cursor/skills/conversation-grid-matplotlib/requirements.txt
```

Requires `matplotlib` and `PyYAML`. Uses `Agg` backend (no display).

## Run

```bash
python3 .cursor/skills/conversation-grid-matplotlib/scripts/draw_labeled_grid.py \
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

See [.cursor/skills/conversation-grid-matplotlib/examples/conversation_intelligence_realtime_grid.yaml](examples/conversation_intelligence_realtime_grid.yaml).

## Verify

```bash
python3 .cursor/skills/conversation-grid-matplotlib/scripts/draw_labeled_grid.py \
  .cursor/skills/conversation-grid-matplotlib/examples/conversation_intelligence_realtime_grid.yaml \
  -o /tmp/conversation_grid_matplotlib.png
```

In this repo the doc figure is checked in as `docs/conversation_intelligence_realtime_grid.png` (same command with `-o docs/conversation_intelligence_realtime_grid.png` from repo root).

Open the PNG to confirm CJK fonts (macOS: PingFang SC in default stack).
