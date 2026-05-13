Summary: Removed redundant and low-value tests already covered by stronger feature or service tests.

- Read `.agents/maintenance/P2_ENHANCE_TESTS.md` after the requested `TESTS.md` path was absent.
- Removed duplicate `build_image_prompt` assertions from `tests/app/test_chat_image_generation.py`.
- Removed Android missing-endpoints E2E cases covered by feature-level TTS, email/password login, and surprise snap tests.
- Removed the REPL constant-value assertion that only repeated package configuration.

Follow-ups: None.
