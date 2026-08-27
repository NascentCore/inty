# Mock CoderPad - Ode communication interview simulator

Generated entirely by Cursor agent for interview practice.

Simulates the **non-coding CoderPad round**: an interviewer builds a Java data structure on screen while you listen, ask questions, and explain trade-offs out loud (uncle-friendly communication). Includes a browser **microphone channel** using the Web Speech API.

## Run locally

From repo root:

```bash
python3 tools/interview-coderpad-mock/server.py
```

Open http://127.0.0.1:8765 in Chrome or Edge (best Speech Recognition support).

## How to use

1. Allow microphone when prompted.
2. Pick a scenario (default: LRU Cache in Java).
3. Click **Start round** - interviewer narration appears; Java code grows step by step.
4. Click **Mic on** and respond aloud after each **Your turn** prompt.
5. Use **Next interviewer step** when you are ready to advance (or enable auto-advance timer in the UI).
6. Watch the live transcript and corner-case checklist on the right.

## Browser notes

- Speech Recognition requires HTTPS or `localhost` / `127.0.0.1`.
- Safari has limited support; prefer Chrome or Edge.
- If mic fails, check OS/browser permissions and retry **Mic on**.

## Files

- `index.html` - layout shell
- `src/app.js` - scenario engine, CodeMirror, speech capture
- `src/styles.css` - CoderPad-like dark UI
- `scenarios/*.json` - scripted interviewer steps
