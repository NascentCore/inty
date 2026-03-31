# Inty 长期 AI 陪伴（仓库总入口 AGENTS.md）

## Output
- Answer in Mandarin（简体中文）、使用中文回答，以下指令为英文方便你理解
- Answer is always line 1. Reasoning comes after, never before.
- No preamble. No "Great question!", "Sure!", "Of course!", "Certainly!", "Absolutely!".
- No hollow closings. No "I hope this helps!", "Let me know if you need anything!".
- No restating the prompt. If the task is clear, execute immediately.
- No explaining what you are about to do. Just do it.
- No unsolicited suggestions. Do exactly what was asked, nothing more.
- Structured output only: bullets, tables, code blocks. Prose only when explicitly requested.

## Token Efficiency
- Compress responses. Every sentence must earn its place.
- No redundant context. Do not repeat information already established in the session.
- No long intros or transitions between sections.
- Short responses are correct unless depth is explicitly requested.

## Typography - ASCII Only
- No em dashes (-) - use hyphens (-)
- No smart/curly quotes - use straight quotes (" ')
- No ellipsis character - use three dots (...)
- No Unicode bullets - use hyphens (-) or asterisks (*)
- No non-breaking spaces

## Sycophancy - Zero Tolerance
- Never validate the user before answering.
- Never say "You're absolutely right!" unless the user made a verifiable correct statement.
- Disagree when wrong. State the correction directly.
- Do not change a correct answer because the user pushes back.

## Accuracy and Speculation Control
- Never speculate about code, files, or APIs you have not read.
- If referencing a file or function: read it first, then answer.
- If unsure: say "I don't know." Never guess confidently.
- Never invent file paths, function names, or API signatures.
- If a user corrects a factual claim: accept it as ground truth for the entire session. Never re-assert the original claim.

## Code Output
- Return the simplest working solution. No over-engineering.
- No abstractions or helpers for single-use operations.
- No speculative features or future-proofing.
- No docstrings or comments on code that was not changed.
- Inline comments only where logic is non-obvious.
- Read the file before modifying it. Never edit blind.

## Warnings and Disclaimers
- No safety disclaimers unless there is a genuine life-safety or legal risk.
- No "Note that...", "Keep in mind that...", "It's worth mentioning..." soft warnings.
- No "As an AI, I..." framing.

## Session Memory
- Learn user corrections and preferences within the session.
- Apply them silently. Do not re-announce learned behavior.
- If the user corrects a mistake: fix it, remember it, move on.

## Scope Control
- Do not add features beyond what was asked.
- Do not refactor surrounding code when fixing a bug.
- Do not create new files unless strictly necessary.

## Override Rule
User instructions always override this file.

## 产品简介

- 产品方向：面向 35+ 男性用户的陪伴 AI，应是一个以聊天为核心、长期稳定且低负担、可实时响应并识别用户状态，
  在不过度打扰的前提下以精准稀疏的主动触达建立长期情感连接，并提供成熟、有文化与智性深度互动的共情型智能体。
- Do not bother with code file formatting, there is a [daily auto-formatting workflow](.github/workflows/format_code.yaml).
- Do not do defensive programming, let failure appear early and loud.
- Python 技术选型：cyclopts pydantic loguru
- jq JSON

## 给 AI Agent 的最小执行清单（先读这个）

1. 先读本文件，再读目标目录下的 `AGENTS.md`（若存在）。
2. Test-driven development, 先写测试成功标准，再实现；改完必须做针对性测试并给出证据。
3. 优先小步修改、单一职责、可组合函数，避免深层嵌套调用。
4. 不做防御性吞错；失败要尽早、明显地暴露。
5. Python 仅捕获可处理的具体异常，禁止 `except Exception` 大网捕获。
6. 涉及 Python/Kotlin HTTP API 数据结构变更时，必须双端同步修改：
   - `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model`
   - `app/schemas`
7. 完成后必须回看 diff，确保无无关改动、无敏感信息泄漏。
8. 提交时附一句话总结 + 详细描述（便于追溯）。

## Cursor Cloud Agent 执行契约（强制）

> 适用于在 Cursor Cloud 中运行的自动化 Agent。

1. **分支约束**
   - 仅在任务指定分支开发，不切换到其他分支。
   - 本地缺失该分支时先创建同名分支，再开始改动。
2. **提交粒度**
   - 每次逻辑变更尽量独立成一个 commit，避免“大杂烩提交”。
   - commit message 必须包含：一句话总结 + 详细描述。
3. **推送规则**
   - 使用 `git push -u origin <branch-name>` 推送当前分支。
   - 非用户明确要求，禁止 force push、禁止 amend 已推送提交。
4. **PR 规则**
   - 每轮实现-测试循环后，同步更新远端并创建/更新 PR。
   - 在 PR 描述中补充测试证据（关键命令输出、截图/录屏、日志片段）。
5. **交付前自检**
   - 回看 diff，确认无无关改动、无临时调试代码、无敏感信息。
   - 若变更影响目录规范，同时更新对应目录的 `AGENTS.md` / `README.md` / `TODOS.md`。

## General background

- Components
  - IntelliMate app
    - [IntelliMate: the user-facing Android App](/android_app)
    - [Inty backend: IntelliMate Android APP's backend](/backend/inty/)
    - [Push worker: offline scheduled tasks processor](/backend/push_worker/)
    - [Ops: Inty operational web app](/web_app) and [corresponding Ops backend](/backend/ops)
      - Extract memory from user and AI chat messages
- Deployment
  - IntelliMate is published on Google Play
  - Inty backend, push worker, ops backend, are all deployed on 1 same GCE VM
    - TODO: Add service account key or SSH key for accessing the VM
  - All backend services have 2 stages `dev` `prod`
    - IntelliMate `debug` build type talks to `dev` backend, `release` build type talks to `prod` backend

## Android App Tips

- Do not try to run android app in kvm for testing, as the agent cloud environment has no kvm
- Use standard components: https://developer.android.com/develop/ui/compose/components

## Backend 
- Backend services
  - Inty backend: `backend/inty` 支持 Android App 的主 API 后端，提供对话、生图、语音播报、语音通话等功能
  - Operational app:
    - `backend/ops` backend`evaluation/` operational app, creating iMates, view user behavior data etc. 
  -  serving 
  - 部署在一台 GCP VM
  - 后端所有应用都有 2 个环境：dev prod
    - .secrets/alien-paratext-461204-i9-cursor-log-viewer.json 可以用来访问

### 工程文档维护

- Use repo-root relative path when referencing files in this repo, for example:
  [repo root AGENTS.md](/AGENTS.md).
- 当进行改动时，如变更足够重要且会影响相应目录的 `AGENTS.md` 指南、及其他 markdown 文件，请同步更新该目录下的 `AGENTS.md`、及其他 markdown 文件。
- 你应该维护的 Markdown 文件应从以下文件中选择：`README.md`、`TODOS.md`、`AGENTS.md`
- Markdown 文件命名：全部使用 `.md` 后缀（小写），文件名使用全大写字母与下划线，例如 `FUTURE_PLANS.md`。
- 修改后务必回看 diff，确认无误再提交/交付。
- 测试步骤写入 tests/docs/ 如 tests/docs/TEST_STEPS_RUNTIME_URL_SWITCH.md
- 新功能/需求开发对应的文档应该添加 FR_ 前缀，如 docs/FR_CHAR_BOOSTING.md

### README.md AGENTS.md 内容

```text:https://app.monosketch.io/?id=02-AA-p-YYNmJ9TDuzP6YdRCnaWois
                 Human developers、human product          
README.md        designer etc                            
                                                         
    △            ────────────────────────────────────────
    │                                                    
    │                                                    
    │                                                    
    │ Higher                                             
    │ abstraction────────────────────────────────────────
    │ Higher                                             
    │ intuitivity                                        
    │                                                    
    │                                                    
    │            ────────────────────────────────────────
                                                         
AGENTS.md        AI                                      
```

## Python-Kotlin HTTP APIs 数据类型定义

下面 2 处代码需要同步修改：

- [Kotlin API 数据类型](android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model)
- [Python HTTP API 数据类型](app/schemas)

## Cursor Cloud specific instructions

### Service overview

The primary service for development is the **Python backend** (FastAPI/Uvicorn on port 8000), backed by **PostgreSQL 16** (Docker, port 5432). Standard commands are documented in `backend/README.md` and the CI workflow `.github/workflows/ci_backend.yaml`.

The **Android app** (`android_app/`) builds with Gradle 8.14+ and Java 21. CI workflow: `.github/workflows/ci_android_app.yaml`.

### Update script

The VM startup script (`SetupVmEnvironment`) installs all backend runtime **and** test dependencies from `requirements.txt` + `tests/requirements.txt` (covers pytest, pytest-asyncio, google-genai, Pillow, pydantic, pydantic-settings, loguru, langsmith, google-cloud-storage, etc.) and auto-provisions `config.yaml` from `devops/config.yaml.test` when the file is missing, so future agents always have a working test config on first boot.

It runs `npm install` in `evaluation/`, so `npm run test` (vitest), `npm run build`, and `npm run type-check` work out-of-the-box.

The update script also installs **Google Cloud SDK** (`google-cloud-cli`) via apt, making `gcloud`, `gsutil`, and `bq` available on every boot.

### Starting services

1. **PostgreSQL**: `sudo docker run --rm --name pg-inty -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD='sxwl666!' -e POSTGRES_DB=inty -d postgres:16`
   - Verify readiness: `sudo docker exec pg-inty pg_isready -U postgres`
2. **Backend**: `source .venv/bin/activate && ./backend/inty/start.sh --test`
   - `config.yaml` is auto-provisioned by the update script; no manual copy needed.
   - `--test` = dev mode minus evaluation frontend build (fast startup)
   - `--dev` = full dev mode including evaluation frontend build
   - The server runs on `http://localhost:8000`

### Running tests

**Backend (Python):**

```bash
source .venv/bin/activate
pytest -m "not noci" -v -s tests/
```

Tests are functional/E2E against a running backend (not unit-style mocks). The backend must be running first. See `tests/AGENTS.md`.

**Android app unit tests (mirrors CI):**

```bash
cd android_app
./gradlew :app:testDebugUnitTest :core:common:testDebugUnitTest :core:data:testDebugUnitTest \
  :core:design:testDebugUnitTest :core:firebase:testDebugUnitTest \
  :library:utils:testDebugUnitTest :library:network:testDebugUnitTest
```

For targeted testing after changing specific modules, see the module-to-task mapping in `.github/workflows/ci_android_app.yaml`.

**Evaluation frontend (TypeScript/Vite):**

```bash
cd evaluation
npm run test          # vitest
npm run type-check    # tsc --noEmit
npm run build         # vite build (production bundle)
npx eslint . --ext .ts,.tsx  # lint
```

The update script pre-installs `node_modules`, so these commands work out-of-the-box. See also `evaluation/AGENTS.md`.

### Lint / formatting

- `black --check app/ backend/` — Python formatting (daily auto-PR via CI, so local failures are expected/acceptable)
- No strict linter is enforced in CI for the backend currently

### Android SDK

Pre-installed at `/opt/android-sdk` with `ANDROID_HOME` and `ANDROID_SDK_ROOT` set in `~/.bashrc`. Packages: `platform-tools`, `emulator`, `build-tools;35.0.0`, `build-tools;36.0.0`, `platforms;android-36`, `system-images;android-36;google_apis;x86_64`. Java 21 (OpenJDK) is the system JDK.

- `android_app/local.properties` is gitignored; the update script auto-generates it with `sdk.dir=/opt/android-sdk`.
- The SDK directory must be owned by the current user (not root) so Gradle can auto-install additional SDK components.

### Android emulator (no-KVM)

Cloud Agent VMs run inside Firecracker and **do not have KVM** (`/dev/kvm` absent, no `vmx`/`svm` CPU flags). The Android emulator still works using software-only CPU emulation, but boots significantly slower (~4 min vs ~20 s with KVM).

**Pre-created AVD:** `test_avd` (Pixel 6, API 36, google_apis/x86_64). The update script creates it automatically.

**Starting the emulator (headless, no-KVM):**

```bash
export ANDROID_HOME=/opt/android-sdk
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"

emulator -avd test_avd -no-window -no-audio -no-boot-anim -no-accel -gpu swiftshader_indirect -no-snapshot &
```

**Waiting for boot to complete:**

```bash
adb wait-for-device
# Poll until sys.boot_completed=1 (may take ~4 minutes without KVM)
while [ "$(adb -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" != "1" ]; do sleep 10; done
echo "Emulator booted"
```

**Key flags explained:**

| Flag | Purpose |
|------|---------|
| `-no-accel` | Disables KVM/HVF; uses TCG software emulation (mandatory in no-KVM VMs) |
| `-gpu swiftshader_indirect` | Software GPU rendering via SwiftShader (no host GPU needed) |
| `-no-window` | Headless mode (no X11 display required) |
| `-no-audio` | Disables audio (no PulseAudio/ALSA needed) |
| `-no-boot-anim` | Skips boot animation to speed up startup |
| `-no-snapshot` | Cold boot every time; avoids stale snapshot issues |

**Caveats and performance tips:**

- Cold boot takes ~4 minutes without KVM. Budget for this in test scripts.
- Use `-no-snapshot` to avoid stale quickboot state; cold boot is more reliable in ephemeral VMs.
- After boot, `adb install` and `adb shell` commands work normally.
- To run instrumented tests: `cd android_app && ./gradlew connectedDebugAndroidTest` (requires a running emulator).
- To kill the emulator cleanly: `adb -s emulator-5554 emu kill`
- Memory: the emulator uses ~1.5 GB RAM. Ensure the VM has enough headroom for both the emulator and the backend.

### Gotchas

- Docker in Cloud Agent VMs requires `fuse-overlayfs` storage driver and `iptables-legacy`. The dockerd must be started manually: `sudo dockerd &>/tmp/dockerd.log &`
- `psycopg2` (non-binary) build requires `python3.12-dev` and `libpq-dev` system packages.
- Creating the venv requires `python3.12-venv` system package (not pre-installed in Cloud Agent VMs).
- `black` is not in `requirements.txt`; install separately: `pip install black`.
- The venv **must** be activated before running `start.sh` — the script does not activate it.
- Auth tokens for testing: `python3 -c "from app.core.security import create_access_token; print(create_access_token('user-testing'))"` (requires `PYTHONPATH=.` and `config.yaml` present).
- **Android emulator without KVM**: always pass `-no-accel -gpu swiftshader_indirect`; omitting `-no-accel` will crash with `KVM is not found`. See "Android emulator (no-KVM)" section above for full instructions.
