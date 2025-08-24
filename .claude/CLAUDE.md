# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Key instructions

* When writing FastAPI code, use ../FASTAPI_BEST_PRACTICES_ZH.md as guidelines
* Do not wrap everything inside try...except block, as we already have FastAPI to do that
  * We'll try...except in FastAPI handler functions
* When creating new folder, place an empty __init__.py file
* Do not use magic numbers, always define variable, constants, etc.
* When logging, prefer logger.debug(), which is turned off by default and in prod

## Overview

* This repo is a monorepo of Inty. Inty is an AI-driven intimacy simulation for young male adults.
  Such simulation is carried out through text, audio/voice, image exchanges between a human user,
  and an AI character of the user's desire, in a fictional turn-based role-play.
  Users use Android app (code in another repo) to access Inty.
* This repo has main backend of Inty under app/, and supporting tools not directly running
  inside Inty backend, but is used to generate content on Inty. Like AI character
  mobile app.
* The code is primarily written by human engineers using Cursor AI IDE.
  Claude Code is used to write independent tools like
  character evaluation tool under app/static/evaluation.
* app/ has all of the backend service code. They are written in Python.
  Uses FastAPI for app-backend API calling. Langchain for calling LLM APIs.

## Understanding this repo

* Read README.md in this repo to understand the conceptual structure.
* There are other *.md files that explains special aspects.

## Working with the code

* Focus on functionality, format and style is maitained using specialized tools like black,
  which should not be invoked directly.
* When writing documentation, write them into docs/ directory.

## Philosophy

### Core Beliefs

* __Incremental progress over big bangs__ - Small changes that compile and pass tests
* __Learning from existing code__ - Study and plan before implementing
* __Pragmatic over dogmatic__ - Adapt to project reality
* __Clear intent over clever code__ - Be boring and obvious

### Simplicity Means

* Single responsibility per function/class
* Avoid premature abstractions
* No clever tricks - choose the boring solution
* If you need to explain it, it's too complex

## Process

### 1. Planning & Staging

Break complex work into 3-5 stages. Document in `IMPLEMENTATION_PLAN.md`:

```markdown
## Stage N: [Name]
**Goal**: [Specific deliverable]
**Success Criteria**: [Testable outcomes]
**Tests**: [Specific test cases]
**Status**: [Not Started|In Progress|Complete]
```

* Update status as you progress

* Remove file when all stages are done

### 2. Implementation Flow

1. __Understand__ - Study existing patterns in codebase
2. __Test__ - Write test first (red)
3. __Implement__ - Minimal code to pass (green)
4. __Refactor__ - Clean up with tests passing
5. __Commit__ - With clear message linking to plan

### 3. When Stuck (After 3 Attempts)

__CRITICAL__: Maximum 3 attempts per issue, then STOP.

1. __Document what failed__:
   * What you tried
   * Specific error messages
   * Why you think it failed

2. __Research alternatives__:
   * Find 2-3 similar implementations
   * Note different approaches used

3. __Question fundamentals__:
   * Is this the right abstraction level?
   * Can this be split into smaller problems?
   * Is there a simpler approach entirely?

4. __Try different angle__:
   * Different library/framework feature?
   * Different architectural pattern?
   * Remove abstraction instead of adding?

## Technical Standards

### Architecture Principles

* __Composition over inheritance__ - Use dependency injection
* __Interfaces over singletons__ - Enable testing and flexibility
* __Explicit over implicit__ - Clear data flow and dependencies
* __Test-driven when possible__ - Never disable tests, fix them

### Code Quality

* __Every commit must__:
  * Compile successfully
  * Pass all existing tests
  * Include tests for new functionality
  * Follow project formatting/linting

* __Before committing__:
  * Run formatters/linters
  * Self-review changes
  * Ensure commit message explains "why"

### Error Handling

* Fail fast with descriptive messages
* Include context for debugging
* Handle errors at appropriate level
* Never silently swallow exceptions

## Decision Framework

When multiple valid approaches exist, choose based on:

1. __Testability__ - Can I easily test this?
2. __Readability__ - Will someone understand this in 6 months?
3. __Consistency__ - Does this match project patterns?
4. __Simplicity__ - Is this the simplest solution that works?
5. __Reversibility__ - How hard to change later?

## Project Integration

### Learning the Codebase

* Find 3 similar features/components
* Identify common patterns and conventions
* Use same libraries/utilities when possible
* Follow existing test patterns

### Tooling

* Use project's existing build system
* Use project's test framework
* Use project's formatter/linter settings
* Don't introduce new tools without strong justification

## Quality Gates

### Definition of Done

* [ ] Tests written and passing
* [ ] Code follows project conventions
* [ ] No linter/formatter warnings
* [ ] Commit messages are clear
* [ ] Implementation matches plan
* [ ] No TODOs without issue numbers

### Test Guidelines

* Test behavior, not implementation
* One assertion per test when possible
* Clear test names describing scenario
* Use existing test utilities/helpers
* Tests should be deterministic

## Important Reminders

__NEVER__:

* Use `--no-verify` to bypass commit hooks
* Disable tests instead of fixing them
* Commit code that doesn't compile
* Make assumptions - verify with existing code

__ALWAYS__:

* Commit working code incrementally
* Update plan documentation as you go
* Learn from existing implementations
* Stop after 3 failed attempts and reassess
