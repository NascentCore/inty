# Stimulus Curation Log

## Purpose
Track major decisions and evidence for the English stimulus curation pipeline.

## Current Phase
Framework-only scaffolding.

## Entries

### 2026-03-21 — Initial scaffold
- Added DB candidate extractor for user messages from `chat_history`.
- Added sanitization for basic PII patterns:
  - emails -> `[EMAIL]`
  - phone numbers -> `[PHONE]`
  - URLs -> `[URL]`
- Added English ratio filtering and near-dedup normalization.
- Added representative bucket sampling:
  - greeting
  - emotional_support
  - relationship
  - advice
  - general
- Added mock candidate generator for offline smoke tests.

### 2026-03-21 — Availability probe scaffold
- Added model availability probe command in framework CLI to track provider readiness.
- Probe list includes configured experiment models and the Claude TODO baseline
  (`anthropic/claude-3.5-sonnet`) by default.
- Probe output writes to:
  - `research/model_essense_study/docs/MODEL_AVAILABILITY_LATEST.json`

### 2026-03-21 — Run planning scaffold
- Added run-planning command to estimate:
  - total requests/tokens for full run matrix
  - estimated model-level and total cost (USD)
  - estimated runtime vs configured execution window
- Added explicit repeat semantics artifact to reduce ambiguity:
  - `cell-level repeats: each (model, persona, stimulus) cell is repeated N times`
- Planning output writes to:
  - `research/model_essense_study/docs/RUN_PLAN_LATEST.json`

### 2026-03-21 — Availability TODO resolved (live probe)
- Ran a live availability probe (non-dry-run) for configured models plus Claude TODO model.
- Probe evidence written to:
  - `research/model_essense_study/docs/MODEL_AVAILABILITY_LATEST.json`
- Current result snapshot:
  - `google/gemini-2.5-pro`: available
  - `google/gemini-2.5-flash`: available
  - `google/gemini-2.5-flash-lite`: available
  - `anthropic/claude-3.5-sonnet`: available

### Next planned entries
- DB-backed dry run statistics:
  - candidate count before/after filters
  - dedup rate
  - topic distribution
  - average text length
- Manual audit notes on representativeness and privacy.
