Seeded a first-version LivingSphere Markdown anchor into companion runtime bootstrap.

- Added random `LIVING_SPHERE.md` seed generation under `/living_sphere/`.
- Wired the seed into `CompanionManager.get_or_create_session`.
- Loaded the seeded document into the companion system prompt.
- Added focused kernel coverage for seeding idempotence and prompt injection.

Follow-ups: evolve the Markdown anchor into a richer TechnoCore-backed state only after TechnoCore exists.
