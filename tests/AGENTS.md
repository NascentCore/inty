# Tests

- Use actual deps, or fakes, avoid mocks.
- Use skill `inty-backend-ci-local` to setup test environment and run tests
- When checking multiline texts, split lines to array and compare results array with the expected array
  Do not compare lines individually.
  Prefer
  
  ```python
  text_lines = text.split("\n")
  assert text_lines == ["line1", "line2", ...]
  ```

  over

  ```python
  assert "line1" in text
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
