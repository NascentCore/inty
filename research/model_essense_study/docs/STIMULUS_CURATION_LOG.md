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

### Next planned entries
- DB-backed dry run statistics:
  - candidate count before/after filters
  - dedup rate
  - topic distribution
  - average text length
- Manual audit notes on representativeness and privacy.
