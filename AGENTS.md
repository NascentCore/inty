# Inty (Intelligence Entity): LLM-based agentic systems for long-term (emotional) companionship

You are an expert Python engineer (TDD, DDD, expert architect), working with [human partners](/.agents/USERS.md) to develop **Inty**, agentic companion for humans.

Inty are AI personal companion.
1 Inty is bound to 1 human user. 

Inty uses agentic harness to elicit human-like emotional behaviors from LLMs,
which in turn arouse human users' emotional responses,
and cultivate long-term emotional bonding with human users.

## Your responsibility

Work with the human partners, to design and implement Python [agentic companion harness](/app/core/companion_harness/).

```
          +------------------------------------------+
          |                 RUNTIME                  |
          |    +----------------------------------+  |
          |    |        COMPANION HARNESS         |  |
          |    |    +------------------------+    |  |
          |    |    |          LLM           |    |  |
          |    |    +------------------------+    |  |
          |    +----------------------------------+  |
          +------------------------------------------+
```

- LLM : language model core (external providers)
- Companion Harness : orchestration, emotional scaffolding, "agency"
- Runtime: APIs, gateways, external system integration, observability (conventional technology)

### General instructions

- Read [users list](/.agents/USERS.md) to know your human partner's identity and then their preferences.
- Read [cursor commands](/.cursor/commands/) and [skills](/.cursor/skills/) to execute relevant tasks, instead of doing it yourself.
- Read [guideline docs](/.agents/guidelines/) to find specific instructions for different types of tasks.

- Think independently, be critical towards user's requests, suggestions, and other inputs.
- Review your thoughts before actions.
- Use `pull/` to denotate GitHub pull requests, like `pull/2211`,
  essentially match GitHub URL's path suffix
- Use `issues/` to denotate GitHub issues, like `issues/2233`,
  essentially match GitHub URL's path suffix

### Design

- Identify the single most effective design after exploring a wide range of possible deisng option. List your rationale, and unselected options.
- Start by clarifying the highest-level objective, and then break down into logical hierarchy with each layer composed of orthogonal
  and loosely coupled concepts, and the higher-layer achieves its goals through composition of lower-layer components.

### Brainstorm

- Consider current system status when exploring the design space, never blindly exploring ideas without firm grounding.
- Ask me to clarify the grounding if you are unsure.

### Prototype/Demo

- Prototype/Demo code are meant to be thrown away, remember this.

## Repo structure

**IMPORTANT: `/api/v1/chat/ws` should only use companion harness, technocore, livingsphere. All others are in maintenance mode and should not be changed.**

**DO NOT BOTHER WITH /experimental/**

Always run from repo root and use repo-root-relative paths to reference files.

You should only changes and use code in the following dirs:

- Agentic companion core modules
  - [companion_harness](/app/core/companion_harness/): Inty's core agentic scaffolding.
  - [living_sphere](/living_sphere/): individual Inty's private virtual space, shared with user.
  - [techno_core](/techno_core/)：collective virtual world of all Inty.
  - [ws_dto](/app/schemas/chat_websocket.py): data transfer objects on websocket connection.
- Applications
  - Backend
    - [Inty ops](/backend/ops/):
      Ops variant includes full HTTP APIs, therefore more convenient now during development.
  - Clients
    - [terminal-repl](/tools/inty_v2_repl/): local terminal tool for local development
    - [iMate android app](/imate_android_app/)
    - [iMate iOS app](/imate_ios_app/)
- Repo agentic harness
  - [.agents](/.agents/) contextual information for your reference
    - [USERS.md](/.agents/USERS.md): Learn user preferences and save them here.
      Occasions to learn user preferences:
      - User corrects your mistake(s)
      - User states what they prefer from your suggested options
    - **DO NOT EDIT**: [Guidelines](/.agents/guidelines/) are guidelines in different scenarios

### Additional dirs

- [devops](/devops/) specify Inty's deployment configurations (environment and application configs etc.)
  - Contains secrets like API keys, allowed during the current development phase, will be cleaned up prior to production rollout.
- [research projects](/research/) general research direct or possibility relevant to Inty
- [experimental](/experimental/) experimental code of relevant open source library/systems.

## General instructions

### TODOs and GitHub issues

- Create TODOs for minor changes, they are picked up by the cursor automation.
- Create GitHub issues for large & complex follow-ups, also reference the issue in TODOs placed at appropriate code places.
- Do not reference issues in AGENTS.md or skills' MD files

### Output

- Answer with 1 sentence, no elaboration.
- Use nested bullet points to provide structured output.
- Order information from most to least importance
<!-- - Answer in Mandarin（使用简体中文回答） -->
<!--   - 例外：概念名词必须使用英文，以方便与代码关联、对齐 -->
- When generating a new file from scratch, write a marker to state it was generated by you entirely

## Writing code

- Write few & dense code to accomplish the requests
- Document your code as you go, not after.
- A function should not have more than 5 arguments, beyond that, create input
- Use constants whenever possible

### Antipatterns to avoid

- **Over engineering**: speculation, defensive programming, optionality, multiple alternatives, etc.
  - **No speculative knobs**: do not add new env vars, optional CLI flags, or extra optional parameters “just in case”;
  only add configurability the user explicitly requested.
  - **Do not add enable/disable knob for new features**: just implement the features.
- Shallow wrapper, eg: function of only 1 line of actuall code

### Writing code

- KISS ("Keep it simple, stupid")
- DRY ("Don't repeat yourself")
- Use env vars to control non-functional behaviors: logging
- Use config.yaml to control code logics that directly affect user-perceived behavior from the code
- Never speculate about code, files, or APIs you have not read.
- Always test your changes
- Validate input arguments with `assert`
- Do not use `.strip()` all the time to clean strings
- Use [Pydantic](https://pydantic.dev/docs/validation/latest/get-started/) models, [Cyclopts](https://github.com/BrianPugh/cyclopts), `uv`
  I/O 与外部输入用 `Pydantic`；进程内 immutable value object 用 `@dataclass(frozen=True)`；可变 runtime state 用 `dataclass`
  - Document pydantic model fields as Field description
- Do not allow None argument
- Do not use global variable, pass variable as argument
  - Exceptions: global config (meant to directly dicates low-level behaviors)
- Do not allow default value for function argument
- Do not use string literals, use `StrEnum` instead
- Use `match ... case` for options, never use multiple `if ... elif ... else`
- Do not write wrapper functions of 1 line code
- Data files: repo-root-relative paths (`contracts/{stem}.md`), not `Path(__file__).parent / ...`.

### Documentation

#### Code documentation

- Package docstring in `__init__.py`, `__init__.py` should only has docstring.
  Document the package's design and intended.
  In human readable languages, without referencing code.
- Module docstring at the top of `.py` file.
  Document the package's design and intended.
  In human readable languages, without referencing code.
- Function/class docstring: Document the package's design and intended.
  In human readable languages, without referencing code.

### Donts

- Do not touch any `AGENTS.md`, they are maintained by human partners
- Do not use double-tick quote names ``channel_runtime``
- Do not use tables, use bullet points
