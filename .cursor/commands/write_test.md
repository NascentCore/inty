# Write tests for current changes

## Overview

为当前工作区改动（staged + unstaged）补充测试，优先覆盖行为变化与高风险路径，并运行最小必要测试集验证通过。

## Steps

1. **Understand current changes**
   - Read `AGENTS.md` and nearby module guides first.
   - Inspect current diff and changed files.
   - List behavior/contract changes that require tests.

2. **Design tests before editing**
   - Prefer extending existing nearby tests; create new test files only when needed.
   - Cover at least:
     - 1 happy path for each changed behavior
     - critical edge cases and error paths
   - Keep tests deterministic and maintainable; avoid unnecessary mocking.

3. **Implement tests**
   - Follow repository conventions for test location and naming.
   - For Python tests, avoid creating `__init__.py` in directories containing `test_*.py`.
   - If manual runtime steps are important, document reproducible steps under `tests/docs/`.

4. **Run targeted validation**
   - Run the smallest relevant test commands for the modified area.
   - Fix failures caused by the new tests or related regressions.
   - Re-run until results are stable and green.

5. **Report**
   - Summarize what behavior is covered by each added/updated test.
   - Provide exact test commands and outcomes.
   - Call out remaining untested risks explicitly.

## Checklist

- [ ] Current diff reviewed and behavior changes identified
- [ ] Tests added/updated for all meaningful behavior changes
- [ ] Targeted tests executed and passing
- [ ] No unrelated code changes introduced
- [ ] Test commands and coverage summary included in response
