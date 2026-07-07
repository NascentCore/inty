#!/usr/bin/env bash
# Document-only pointer for SDFT datasets (not bundled in upstream git).
set -euo pipefail

cat <<'EOF'
SDFT datasets are loaded from disk inside the pinned upstream repo:

  upstream/data/tooluse_data/train_data   (HF datasets load_from_disk)
  upstream/data/science_data/train_data
  upstream/data/science_data/eval_data

Obtain archives per https://github.com/idanshen/Self-Distillation README
and place them at the paths above before P1 train/eval on a GPU host.

Medical / Wiki splits mentioned in the paper may appear in future upstream releases.
EOF
