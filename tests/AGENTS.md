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
