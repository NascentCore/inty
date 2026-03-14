# iMate Studio TODOs

## Licensed character ingestion (agentic) - production backlog

- [ ] Connect ingestion agent to real source connectors (licensed biography feeds, image libraries, voice/music vaults).
- [ ] Add hard license gate: block ingestion when `license_deal_id` cannot be validated by contract service.
- [ ] Persist provenance for every imported aspect (`source`, `deal_id`, `aspect_mode`, `transform_prompt`, timestamp).
- [ ] Add policy checks for disallowed combinations (for example, direct voice + unlicensed likeness).
- [ ] Add “derived-only” transformation pipeline with audit trail to support reborn personas.
- [ ] Add rights expiry and territory constraints into casting eligibility.
- [ ] Add commercial export report (what aspects were used in each scene and under which deal).
- [ ] Integrate with Dify workflow as an autonomous multi-step pipeline (discover -> ingest -> normalize -> verify -> publish to repo).

## Demo follow-ups

- [ ] Add repository filters by aspect type (bio/look/voice/music).
- [ ] Add one-click “cast this aspect pack as love-interest template”.
- [ ] Add timeline badges that show where licensed aspects are used.
