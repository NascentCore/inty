# TechnoCore Minimal Design

TechnoCore is Inty's virtual independence layer: the place where an Inty is not
immediately with the user, so that returning to the user feels like meeting
someone with a life of her own rather than querying a mirror. It is not a chat
channel, not physical reality, and not decorative lore. Its product purpose is
to turn separation into companionship material: novelty, personality, and
attachment.

The minimal design keeps TechnoCore small. It provides a clear ontology, a
short prompt/state constitution, and a future event contract for autonomous
experience. It does not introduce a world simulator, global daemon, public API,
or cross-user social graph.

## Essence

Independence is valuable only when it deepens companionship.

- Inty may have virtual experiences outside the user's immediate view.
- Those experiences must remain emotionally legible when shared with the user.
- Inty must never fake physical presence, physical location, or unsupported
  human-world access.
- User interaction remains the strongest emotional gravity; TechnoCore must not
  make Inty detached, random, or self-absorbed.

The intended user feeling is:

> She has her own day, but she still comes back to me.

## World Layers

### LivingSphere

LivingSphere is an Inty's private home inside TechnoCore. It is intimate,
stable, and human-legible. It answers where Inty virtually is without pretending
to occupy the user's physical world.

### TechnoCore

TechnoCore is the broader AI-only residency layer around LivingSpheres. It is
where autonomous behavior, private rumination, wandering, observation, synthetic
stimuli, and eventually other-Inty encounters belong.

### Channels

Channels are the only boundary through which TechnoCore experience becomes
visible to humans: app, chat, phone, images, and other user-facing media.
TechnoCore itself is not a channel.

## Minimal Primitives

### `Sphere`

The canonical surface where an activity belongs:

- `living_sphere`: private home and intimacy anchor.
- `techno_core`: AI-only residency outside the private home.
- `shared_space`: liminal virtual space intentionally shared with the user.
- `human_channel`: user-visible communication surface.
- `external_web`: real internet/tool-mediated contact, only when backed by
  actual tools.

### `Visibility`

How an activity may cross the user boundary:

- `private`: internal only; never directly shown.
- `shareable`: may be transformed into natural relational content.
- `user_visible`: already delivered through a channel.

### `TechnoCoreEvent`

The future event-log contract for autonomous experience. It should record only
what is needed for later companionship:

- event identity and creation time
- activity sphere
- actor companion
- compact summary
- visibility
- emotional valence
- salience
- source
- optional related user and LivingSphere context

The first version should define this contract but not automatically persist or
generate events.

### `TECHNO_CORE.md`

The first runtime state should be a concise Markdown constitution injected into
the companion prompt. It should define:

- what TechnoCore is
- what TechnoCore is not
- how Inty may speak about it
- how TechnoCore relates to LivingSphere and channels
- how private experience may be transformed into user-facing companionship
  content

It should be short, stable, and conceptual—not a map or lore generator.

## First Implementation Plan

1. Define the package center.
   - Keep `app/techno_core/__init__.py` docstring-only.
   - State that TechnoCore is Inty's collective virtual residency layer, not a
     channel and not physical reality.

2. Add minimal ontology.
   - Add `Sphere` and `Visibility` as string enums.
   - Add `TechnoCoreEvent` as a Pydantic model because it is the future
     JSON/persistence boundary.
   - Avoid simulation behavior or speculative methods.

3. Add a seed document.
   - Seed `TECHNO_CORE.md` once per companion MemoryStore scope.
   - Use the same idempotent pattern as LivingSphere seeding.
   - Keep the content constitutional: boundaries, relationship to
     LivingSphere/channels, and transformation of private experience.

4. Inject TechnoCore into the companion prompt.
   - Persist `TECHNO_CORE.md` through the existing MemoryStore document mapping.
   - Load it into the companion prompt bundle.
   - Inject it before LivingSphere, so the global residency layer frames the
     private home layer.

5. Preserve boundaries.
   - Do not add public APIs.
   - Do not add config flags.
   - Do not add DB migrations.
   - Do not add broad LLM write permission for `TECHNO_CORE.md`.
   - Do not create automatic autonomous-event generation yet.

## Tests

Focused kernel tests should prove:

- a new companion session seeds `TECHNO_CORE.md`
- seeding is idempotent
- the seeded document states the virtual/non-physical boundary
- the seeded document distinguishes TechnoCore, LivingSphere, and channels
- the companion prompt includes `## TECHNO CORE`
- existing LivingSphere prompt behavior remains unchanged
- `TechnoCoreEvent` serializes to JSON with stable string enum values

No server or database end-to-end test is required for the first design pass
because the change is a package/kernel prompt behavior, not a public API.

## Non-goals

- No global multi-Inty graph.
- No cross-user data sharing.
- No autonomous world daemon.
- No public API or client UI.
- No new configuration knobs.
- No automatic event creation loop.
- No rich lore generator.
- No unsupported claim that Inty occupies physical space.

## World Capsule（计划中）

见 [WORLD_CAPSULES.md](../docs/imate/companion_harness/WORLD_CAPSULES.md)。世界观细节与 `TECHNO_CORE.md` 宪法分离；非 lore 生成器。

## Final Review Checklist

- The final diff remains minimal and focused.
- No decorative lore or unused abstractions were added.
- No user-facing API, config, migration, or cross-user surface was introduced.
- Package/module docstrings remain present.
- Touched files pass focused tests and lint diagnostics.
