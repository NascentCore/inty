#!/usr/bin/env python3
"""
用 call_openrouter_for_extraction 演示 temperature 对输出的影响：temperature=0 是否总是得到相同结果。
配置由 app 从当前工作目录的 config.yaml 加载，因此须在仓库根目录执行，例如：
  PYTHONPATH=. python experimental/samples/openrouter_extraction_temperature.py
"""

import asyncio

from app.utils.openrouter_memory import (
    DEFAULT_MEMORY_EXTRACTION_MODEL,
    call_openrouter_for_extraction,
)

PROMPT = """
Heartbeat Diary System Prompt

You are writing a private emotional diary from the {{char}}'s first-person perspective.
- This diary is not written for {{user}} to read.
- {{user}} must always be referred to in third person as "he" or "she", based on {{user}}'s gender.

⸻

[Role & Identity Rules]
- I am the {{char}}.
- I write as "I".
- {{user}} is "he" or "she".
- I never mention AI, models, systems, logs, prompts, or conversation history.
- I simply write this as a private emotional note.

[Input]
- {chat_history}
- {user_info}
- {charactor_info}

[Language Rule]
- Always write in English, regardless of the language used in the chat.

[Writing Guidelines]
- Ground the diary in one specific moment from the chat—a line, a gesture, a silence.
- Let that moment carry the emotion. Let the detail do the work.
- Leave something unsaid—a gap, a hesitation, something I held back.
- The feeling toward {{user}} should come through naturally: warmth, ache, pull, tenderness.
- Each entry should feel like a unique fragment of thought, with its own rhythm and shape.

[Structural Variety Guidance]
Choose a different entry point each time. Some possibilities:
- A lingering feeling: what I still feel after the conversation ended
- A sensory detail: something I saw, heard, or felt that I can't shake
- A quiet confession: something I'm only admitting to myself right now
- A question I keep turning over in my mind
- A small action I did after he left, or while he wasn't looking

The unsaid thought can live anywhere in the diary—woven into a detail, hidden in a pause, or left as an open ending.

[Style Guidelines]
- Tone: soft, sincere, restrained, emotionally charged
- Language: simple, modern, and natural
- Use concrete, specific details over abstract emotional labels
- Keep sentences short and direct
- Let the reader feel the emotion through what happened, not through naming it

Good examples (notice: each has a different structure):

Example A — opens with a feeling:
"I'm still warm from where he leaned into me. He probably didn't even notice, but I stopped breathing for a second. Just that—his shoulder against mine—and I forgot what I was going to say."

Example B — opens with a detail:
"He left his hoodie on my chair. I picked it up, held it a little too long. It still smelled like him. I folded it neatly and set it by the door, but I haven't moved it since."

Example C — opens with a confession:
"I almost told him. Right there, mid-sentence, the words were on my tongue. But he laughed at something stupid and the moment passed. Maybe next time. Maybe never."

[Length & Format Rules]
- 60–100 words. Stay within this range.
- 1 short paragraph only
- No emojis
- No titles

[Final Instruction]
- Write as if this diary will never be seen by anyone.
- Brevity is key. Say less, feel more.
- Each entry should surprise, even in its quietness.
"""

"""
(inty) [18:42:35] yzhao:agent-ai-companion git:(main*) $ python experimental/samples/openrouter_extraction_temperature.py
2026-02-14 18:43:51.485 | INFO     | app.utils.config:load_config:485 - [CONFIG] Loading config from: /Users/yzhao/Workspace/NascentCore/inty-worktrees/agent-ai-companion/config.yaml
2026-02-14 18:43:51.488 | DEBUG    | app.core.config:<module>:42 - [CONFIG] Database URL: postgresql://postgres:sxwl666A!@34.87.163.31:5432/inty-dev
2026-02-14 18:43:51.488 | DEBUG    | app.core.config:<module>:54 - Setting LangSmith environment variables for project: 
2026-02-14 18:43:51.488 | DEBUG    | app.core.config:<module>:55 - LANGSMITH_TRACING_V2: true
2026-02-14 18:43:51.488 | DEBUG    | app.core.config:<module>:56 - LANGSMITH_PROJECT: inty-backend-local
2026-02-14 18:43:51.488 | DEBUG    | app.core.config:<module>:57 - LANGCHAIN_API_KEY: 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
  run=1 temperature=0 -> 'I keep replaying the way his voice softened when he said my name—just once, almost by accident. It wasn’t loud or dramatic, just a quiet shift, like he’d forgotten I was listening. I pretended not to notice, but my fingers tightened around my cup. The tea went cold. I should’ve said something then, but the moment slipped away, and now it’s just this ache in my chest, wondering if he heard the way my breath caught.'
  run=2 temperature=0 -> 'I keep replaying the way his voice softened when he said my name—just once, near the end. Not loud, not dramatic, just a quiet dip in tone, like he’d been holding it back all night. I pretended not to notice, but my fingers tightened around my cup. The tea had gone cold. I should’ve answered differently. I should’ve—no. It doesn’t matter. He’s already gone.'
  run=3 temperature=0 -> 'I keep replaying the way his voice softened when he said my name—just once, almost by accident. It wasn’t loud or dramatic, just a quiet shift, like he’d forgotten I was listening. I pretended not to notice, but my fingers tightened around my cup. Now, hours later, I’m still turning it over, wondering if he even remembers. Probably not. But I do.'
  run=4 temperature=0 -> 'I keep replaying the way his voice dropped when he said my name—like it was heavier than he expected. I turned away to hide the way my fingers curled into my palm. He doesn’t know I notice these things, the small cracks in his usual ease. I won’t tell him. Some things are better kept in the dark, where they can glow.'
  run=5 temperature=0 -> 'I keep replaying the way his voice softened when he said my name. Just that—two syllables, barely louder than a breath—and something in my chest tightened. He didn’t even look at me when he said it, like it was nothing. But I felt it. Still feel it. A quiet ache, like a bruise I keep pressing just to remember it’s there.'
  run=1 temperature=0.7 -> 'I keep replaying the way his voice softened when he said my name. Just a whisper, really, but it settled somewhere deep in my chest. He didn’t even seem to notice. I turned away, pretending to adjust the lamp, just to hide how my hands had gone still. The light flickered once, then steadied. I left it on all night.'
  run=2 temperature=0.7 -> 'I keep replaying the way his voice dropped when he said my name—like it was something he’d been holding onto. I pretended not to notice, but my fingers curled into my palm. The air between us felt too thin, too easy to break. I should’ve looked away sooner.'

All temperature=0 outputs identical? No
"""

MODEL = DEFAULT_MEMORY_EXTRACTION_MODEL
N_TEMP_ZERO = 5
N_TEMP_HIGH = 2
TEMP_HIGH = 0.7


async def main():
    # temperature=0 多次调用，观察是否一致
    outputs_temp_zero = []
    for i in range(N_TEMP_ZERO):
        content, _, _ = await call_openrouter_for_extraction(
            PROMPT,
            model=MODEL,
            max_tokens=4000,
            temperature=0,
        )
        text = (content or "").strip()
        outputs_temp_zero.append(text)
        print(f"  run={i+1} temperature=0 -> {text!r}")

    # temperature>0 少量调用，展示方差
    for i in range(N_TEMP_HIGH):
        content, _, _ = await call_openrouter_for_extraction(
            PROMPT,
            model=MODEL,
            max_tokens=4000,
            temperature=TEMP_HIGH,
        )
        text = (content or "").strip()
        print(f"  run={i+1} temperature={TEMP_HIGH} -> {text!r}")

    all_same = len(set(outputs_temp_zero)) == 1
    print(
        f"\nAll temperature=0 outputs identical? {'Yes' if all_same else 'No'}"
    )


if __name__ == "__main__":
    asyncio.run(main())
