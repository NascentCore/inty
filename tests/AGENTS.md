# Tests

- Do not write tests for
  `/tools/`
  `/experimental/`
  `/research/`
- Tests for non-Python code are not under this dir.
  For instance, `/web_app/` `/imate_android_app/` `/imate_ios_app/` have their own tests dir, respectively.

- Add test files for a source file with the same relative paths

- Never use mocks or monkeypatch in tests, always assume tests can access local service instance
- When checking multiline text, split text to array of lines and compare with the expected array.
  ```python
  text_lines = text.split("\n")
  assert text_lines == ["line1", "line2", ...]
  ```
- Do not add trivial tests like
  ```
  def test_build_bgm_system_message_contains_catalog() -> None:
    msg = build_bgm_system_message()
    assert msg["role"] == "system"
    content = msg["content"]
    assert "calm_evening_01" in content
    assert "set_bgm" in content
  ```
