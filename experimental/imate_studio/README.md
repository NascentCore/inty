# iMate Studio (minimal interactive demo)

This demo sketches an interactive AI video generation studio for prosumers producing a 6-minute narrative video with rich character interaction.

Design inspiration: **be part of the story you enjoyed, and help others enjoy it too**.

## What this prototype demonstrates

- AI-native intent-first workflow (natural language prompt -> auto-scaffolded story plan).
- Create new characters through an "IntelliMate Dify workflow" style form.
- Select iMates from a character repository and cast them into scene roles.
- Plan and preview a 6-minute timeline (12 scenes x 30 seconds).
- Advance and rewind scenes while role-playing as any cast role.
- Detect missing story/design ingredients, then auto-fill concrete suggestions.
- Run natural-language studio commands (rewind, betray, mark payoff, smart cast).
- Run a licensed character ingestion agent with aspect-level controls:
  - import only bio and reborn into a new persona;
  - import only appearance for a romance lead;
  - import only voice/music style for performance roles.
- Run a music relevance agent that:
  - accepts mixed-media reference links;
  - excludes photo/visual content by default;
  - extracts audio traits and applies scene-level cues for the full 6-minute timeline.

## What was missing (and now added)

The original concept is strong, but these high-leverage pieces were missing:

1. **Story quality guardrails**  
   Added a "Missing Ideas Analyzer" to catch absent beats (inciting incident, twist, escalation, payoff, etc.).
2. **Role-play to timeline connection**  
   Added role actions that directly modify scene notes and progress plot coverage.
3. **Structured 6-minute pacing model**  
   Added a fixed 12-scene timeline for practical pacing and navigation.
4. **Character source unification**  
   Added casting from both existing repository iMates and newly generated Dify drafts.
5. **Session-level visibility**  
   Added an event log to make state transitions explainable for creators.

## Run

```bash
cd experimental/imate_studio
python3 -m http.server 8123
```

Open:

- `http://localhost:8123`

## Suggested next iteration ideas

- Shot-level board with camera angle and duration constraints.
- Token/cost budget bar by scene and model choice.
- Character chemistry simulator with dialogue turn quality scoring.
- Export to structured JSON for downstream video generation workflows.
- Collaborative mode with "director" and "writer" cursors.
- Production license compliance pipeline (contract verification, provenance watermarking, automated policy checks).
