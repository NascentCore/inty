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

### Next planned entries
- DB-backed dry run statistics:
  - candidate count before/after filters
  - dedup rate
  - topic distribution
  - average text length
- Manual audit notes on representativeness and privacy.
