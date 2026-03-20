# Inty 长期 AI 陪伴（仓库总入口 AGENTS.md）

> Last updated: 2026-03-20

## 给 AI Agent 的最小执行清单（先读这个）

1. 先读本文件，再读目标目录下的 `AGENTS.md`（若存在）。
2. 先写测试成功标准，再实现；改完必须做针对性测试并给出证据。
3. 优先小步修改、单一职责、可组合函数，避免深层嵌套调用。
4. 不做防御性吞错；失败要尽早、明显地暴露。
5. Python 仅捕获可处理的具体异常，禁止 `except Exception` 大网捕获。
6. 涉及 Python/Kotlin HTTP API 数据结构变更时，必须双端同步修改：
   - `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model`
   - `app/schemas`
7. 完成后必须回看 diff，确保无无关改动、无敏感信息泄漏。
8. 提交时附一句话总结 + 详细描述（便于追溯）。

## 标准执行模板（建议直接复用）

当你开始一个新任务时，优先按下面流程执行并在最终回复中对齐：

1. **定义测试成功标准（先于实现）**
   - 明确“如何证明改动生效”，包括目标行为与可验证证据。
2. **形成测试计划**
   - 选择最小但有效的测试集合（优先针对变更范围）。
   - 涉及 UI 改动时，补充手工验证步骤与截图/视频证据。
3. **小步实现**
   - 每次只做一个逻辑变化，函数保持可组合，避免深层嵌套。
4. **执行测试并记录证据**
   - 保留关键命令输出、日志片段、截图/录屏等。
5. **回看 diff 并清理**
   - 删除临时调试代码，确认无无关改动、无敏感信息。
6. **提交与同步**
   - 使用清晰提交信息（一句话总结 + 详细描述）。
   - 推送当前工作分支；若有 PR，更新 PR 描述中的测试证据。

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

## 代码库内的一般性约定

- Do not bother with code file formatting, there is a [daily auto-formatting workflow](.github/workflows/format_code.yaml).
- Do not do defensive programming, let failure appear early and loud.

## 软件工程规范

- **Dev Mode**:
  - 默认为开发阶段，不需要考虑 backward compatibility
  - 尽量不使用默认参数
  - 当函数的参数数量在 3 个以上时，可以考虑使用结构体来组合参数
- **代码结构规范**
  1. Functions should be composable, prefer `func a(), func b(), func c() { a(); b() }`
     over `func a(), func b() { a() }, func c() { b() }`.
     Avoid deep nesting of funcation calls.
  2. Always define types to name input and output, and cleanly separate the codd reading
     input and writing output, with the abstract data processing and handling that can
     work with abstract data types. Example:
     prefer `def write_to_db(data, db) { ... }; def read_from_db() { ... }; def proc() { }` over `def proc() { code reading from db, processing, code writing to db}`
- **TDD**：采用测试驱动开发方式，首先编写测试来预演目标行为，然后通过迭代代码来使测试通过
  - 使用单元测试作为代码的“可执行规范”，通过测试用例来体现设计目标
  - 使用单元测试作为代码行为的“可执行示例”，通过测试用例来提供具体的代码行为描述
- **优先可维护性**：避免“为了省事”引入隐式行为（魔法常量、吞异常、无边界重试、隐藏的全局状态）。
- **改完要自查**：每次修改后都应回看 diff，确保改动与意图一致、无泄漏敏感信息、无无关文件被改动。
- **AI 工作总结**：
  - 生成代码中要在其注释中总结你的关键中间步骤，如 app/core/voice/tts_api.py 记录了你如何从官方文档页面收集数据并处理
- **Git 工作流**：
  - 每完成一次改动，生成一句话总结、详细描述

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

## Alembic

Use the following steps to create alembic revision file

```bash
alembic -c alembic/alembic.ini upgrade head # First ensure the local DB is updated
alembic -c alembic/alembic.ini revision --autogenerate -m "<revision description>"
```

## Python-Kotlin HTTP APIs 数据类型定义

下面 2 处代码需要同步修改：

- [Kotlin API 数据类型](android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model)
- [Python HTTP API 数据类型](app/schemas)

## Python

- 避免使用 `try ... except Exception` 覆盖所有异常；只捕获当前函数**能够处理**的特定异常类型。
- 测试用例目录不应被声明为包：包含 `test_*.py` 的测试目录不要放置 `__init__.py`；但用于复用的测试辅助库目录应当作为包存在，并包含 `__init__.py`。
- 所有正式 Python 包必须包含空的 `__init__.py`（仅用于声明包）
- 严禁向已有的 `__init__.py` 内添加新逻辑代码（除非该目录规则明确要求）
- 使用 [cyclopts](https://github.com/BrianPugh/cyclopts) 来实现命令行界面
- 禁止使用 `__main__.py` 这种范式，使用显式的 `main.py` 入口文件

## Android App

- Android 发布新版本后将 version code 写入 [Prod 后端配置文件](devops/config.yaml.prod) `google_play.current_version_code`

## CloudFlare CDN（用于支持媒体文件分发：image audio 等）

- @<https://developers.cloudflare.com/llms.txt>
- @<https://developers.cloudflare.com/workers/prompt.txt>
- @<https://developers.cloudflare.com/stream/llms-full.txt>
- @<https://developers.cloudflare.com/developer-platform/llms-full.txt>

来自官方文档链接 https://developers.cloudflare.com/stream/changelog/

## Cursor Cloud specific instructions

### Service overview

The primary service for development is the **Python backend** (FastAPI/Uvicorn on port 8000), backed by **PostgreSQL 16** (Docker, port 5432). Standard commands are documented in `backend/README.md` and the CI workflow `.github/workflows/ci_backend.yaml`.

The **Android app** (`android_app/`) builds with Gradle 8.14+ and Java 21. CI workflow: `.github/workflows/ci_android_app.yaml`.

### Update script

The VM startup script (`SetupVmEnvironment`) installs all backend runtime **and** test dependencies from `requirements.txt` + `tests/requirements.txt` (covers pytest, pytest-asyncio, google-genai, Pillow, pydantic, pydantic-settings, loguru, langsmith, google-cloud-storage, etc.) and auto-provisions `config.yaml` from `devops/config.yaml.test` when the file is missing, so future agents always have a working test config on first boot.

It also builds the `evaluation/inty_sdk` TypeScript SDK (if not already built) and runs `npm install` in `evaluation/`, so `npm run test` (vitest), `npm run build`, and `npm run type-check` work out-of-the-box.

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

The update script pre-installs `node_modules` and builds the `inty_sdk` dependency, so these commands work out-of-the-box. See also `evaluation/AGENTS.md`.

### Lint / formatting

- `black --check app/ backend/` — Python formatting (daily auto-PR via CI, so local failures are expected/acceptable)
- No strict linter is enforced in CI for the backend currently

### Android SDK

Pre-installed at `/opt/android-sdk` with `ANDROID_HOME` and `ANDROID_SDK_ROOT` set in `~/.bashrc`. Packages: `platform-tools`, `emulator`, `build-tools;35.0.0`, `build-tools;36.0.0`, `platforms;android-36`, `system-images;android-36;google_apis;x86_64`. Java 21 (OpenJDK) is the system JDK.

- `android_app/local.properties` is gitignored; the update script auto-generates it with `sdk.dir=/opt/android-sdk`.
- Git submodules must be initialized for the Android build: `git submodule update --init --recursive` (the update script handles this).
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
