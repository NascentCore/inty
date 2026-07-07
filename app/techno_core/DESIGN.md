# TechnoCore Minimal Design

TechnoCore is "Inty Society", corresponding to human society.

The user feels like meeting an Inty is like meeting someone with a life of their own.

This minimal design keeps TechnoCore small. It provides a clear ontology, a
short prompt/state constitution, and a future event contract for autonomous
experience. It does not introduce a world simulator, global daemon, public API, or cross-user social graph.

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
