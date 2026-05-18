# Cursor Cloud Agent 执行契约（强制）

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

## Service overview

The primary service for development is the **Python backend** (FastAPI/Uvicorn on port 8000), backed by **PostgreSQL 16** (Docker, port 5432). Standard commands are documented in `backend/README.md` and the CI workflow `.github/workflows/ci_backend.yaml`.

The **Android app** (`android_app/`) builds with Gradle 8.14+ and Java 21. CI workflow: `.github/workflows/ci_android_app.yaml`.

## Update script

The VM startup script (`SetupVmEnvironment`) installs all backend runtime **and** test dependencies from `requirements.txt` + `tests/requirements.txt` (covers pytest, pytest-asyncio, google-genai, Pillow, pydantic, pydantic-settings, loguru, langsmith, google-cloud-storage, etc.) and auto-provisions `config.yaml` from `devops/config.yaml.test` when the file is missing, so future agents always have a working test config on first boot.

It runs `npm install` in `evaluation/`, so `npm run test` (vitest), `npm run build`, and `npm run type-check` work out-of-the-box.

The update script also installs **Google Cloud SDK** (`google-cloud-cli`) via apt, making `gcloud`, `gsutil`, and `bq` available on every boot.

### Starting services

1. **PostgreSQL**: `sudo docker run --rm --name pg-inty -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD='sxwl666!' -e POSTGRES_DB=inty -d postgres:16`
   - Verify readiness: `sudo docker exec pg-inty pg_isready -U postgres`
2. **Inty backend (port 8000)**: `source .venv/bin/activate && ./backend/inty/start.sh --test`
   - `config.yaml` is auto-provisioned by the update script; no manual copy needed.
   - `--test` and `--dev` both enable dev startup (same seeds and uvicorn `--reload`); `start.sh` only differs by the banner string. Neither runs the evaluation static build (that is Ops `backend/ops/start.sh --local` only).
   - **`Environment.TEST` in Python** comes from `config.yaml` (`app.environment`), not from the `--test` CLI flag.
   - The server runs on `http://localhost:8000`
3. **Ops backend (port 8001, optional for REPL / ops stack)**: `source .venv/bin/activate && ./backend/ops/start.sh --local --no-build-frontend` skips `evaluation/build.sh` (faster startup if `app/static/evaluation` is already populated). Omit `--no-build-frontend` when you need a fresh evaluation static bundle. For REPL-style debugging, add `--debug --log-file ./inty-ops-local.log` (chat WS REPL: [`tools/inty_v2_repl/README.md`](tools/inty_v2_repl/README.md)). See `backend/ops/start.sh --help`.

## Running tests

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

## Lint / formatting

- `black --check app/ backend/` — Python formatting (daily auto-PR via CI, so local failures are expected/acceptable)
- No strict linter is enforced in CI for the backend currently

### Android SDK

Pre-installed at `/opt/android-sdk` with `ANDROID_HOME` and `ANDROID_SDK_ROOT` set in `~/.bashrc`. Packages: `platform-tools`, `emulator`, `build-tools;35.0.0`, `build-tools;36.0.0`, `platforms;android-36`, `system-images;android-36;google_apis;x86_64`. Java 21 (OpenJDK) is the system JDK.

- `android_app/local.properties` is gitignored; the update script auto-generates it with `sdk.dir=/opt/android-sdk`.
- The SDK directory must be owned by the current user (not root) so Gradle can auto-install additional SDK components.

## Android emulator (no-KVM)

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

## Gotchas

- Docker in Cloud Agent VMs requires `fuse-overlayfs` storage driver and `iptables-legacy`. The dockerd must be started manually: `sudo dockerd &>/tmp/dockerd.log &`
- `psycopg2` (non-binary) build requires `python3.12-dev` and `libpq-dev` system packages.
- Creating the venv requires `python3.12-venv` system package (not pre-installed in Cloud Agent VMs).
- `black` is not in `requirements.txt`; install separately: `pip install black`.
- The venv **must** be activated before running `start.sh` — the script does not activate it.
- Auth tokens for testing: `python3 -c "from app.core.security import create_access_token; print(create_access_token('user-testing'))"` (requires `PYTHONPATH=.` and `config.yaml` present).
- **Android emulator without KVM**: always pass `-no-accel -gpu swiftshader_indirect`; omitting `-no-accel` will crash with `KVM is not found`. See "Android emulator (no-KVM)" section above for full instructions.
