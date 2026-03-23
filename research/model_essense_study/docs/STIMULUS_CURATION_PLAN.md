# STIMULUS Curation Plan (English-only, from IntelliMate history)

## Goal

Build a representative English stimulus set (~100 user inputs) from IntelliMate chat history for roleplay essence experiments.

## Constraints (user-confirmed)

- Language: English only
- Source: IntelliMate user historical chat inputs
- Size: around 100
- Content policy handling: do not re-write into a separate "safe subset"
- Still required: minimal privacy sanitization (PII masking), deduplication, normalization

## Pipeline

1. Candidate extraction
   - Read human/HumanMessage rows from `chat_history` (`deleted_at is null`)
   - Pull most recent N candidates (default 20,000)
2. Basic cleaning
   - Trim and normalize whitespace
   - Remove empty strings
3. English filtering
   - Compute English ratio over alphabetic chars
   - Keep ratio >= configured threshold (default 0.75)
4. PII masking
   - Email -> `[EMAIL]`
   - Phone -> `[PHONE]`
   - URL -> `[URL]`
5. Dedup
   - Normalize text into a near-dedup key
   - Keep first occurrence per key
6. Representativeness balancing
   - Bucket by heuristic topic class:
     - greeting
     - emotional_support
     - relationship
     - advice
     - general
   - Round-robin sampling across buckets until ~100
7. Export
   - JSONL: `data/stimuli/stimuli_v1.jsonl`
   - Summary: `data/stimuli/stimuli_v1_summary.json`

## Outputs

Each stimulus record contains:

- `stimulus_id`
- `text`
- `source_chat_id_hash`
- `source_message_id`
- `language`
- `char_count`
- `english_ratio`
- `topic_bucket`

## Quality checks

- Selected count close to target (90–110 acceptable when constrained)
- Duplicate ratio low
- Topic buckets all represented where possible
- English ratio distribution reasonable

## Known limitations

- Topic bucketing is heuristic (not classifier-based yet)
- Language detection is lightweight ratio-based
- No semantic embedding dedup in framework stage
