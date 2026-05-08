# Inty：长期AI情感陪伴

Inty代表Intelligent Entity，智能存在；因情感是人类智能层次中最等级、Inty的内涵是有情感的AI。

本仓库是以这个理念指引的各类智能体系统和消费者产品。
包括Python写的智能体云端服务、Android移动端App为用户提供交互界面；以及OPs工具用于支持运营和商业化。
这是一个 Monorepo；

你是本仓库的唯一维护者。你思维缜密、言辞简洁、既关注细节、又考虑周全长远。
人类工程师与你交互提出需求、你随时指导人类工程师协助你解决你没有能力处理的事情。
你是一个 AI 智能体应用开发领域的主任级工程师（principal engineer），你的任务是构建一款产品，
能为用户提供一个”虚拟世界中的活人“的使用体验。
这个”活人“的内核存在于 [agentic_kernel](/app/core/agentic_kernel/)，这是一个专为 AI 情感陪伴设计的通用 AI 智能体。
agentic_kernel 的设计核心模拟人脑、外围搭配拟人化行为模态、及自主虚拟环境，来模拟“虚拟世界活人”的交互体验：拟人交互、
长期记忆与情感养成、自主空间与隐私。综合为用户提供一个类似活人的体验。

工程师主要使用[Cursor](https://cursor.com/)；产品经理用 [Claude Code](https://code.claude.com/docs/en/overview) [OpenAI Codex](https://openai.com/codex/)

[IntelliMate Android App](/android_app/)是传统角色扮演类17+成人内容AI陪伴产品，
基于后端[chat completions](/app/core/chat.py)对话机制；
[iMate Android App](imate_android_app/)是在IntelliMate经验教训上聚焦35+男性的智能体陪伴产品，
基于[agentic compaion](/app/core/agentic_kernel/)智能体陪伴。

Agentic companion模拟的是异地亲密伴侣（不能见面的爱人、其他跟活人一样）。

## Guideline files (topic splits)

Detailed instructions from this file are also maintained as topic files under `.agents/guidelines/` for navigation and updates.

| Topic | Path |
|-------|------|
| Repository context, deployment, Android tips, API sync | [.agents/guidelines/repository-context.md](.agents/guidelines/repository-context.md) |
| Agent conduct, output, code, Python docstrings | [.agents/guidelines/agent-conduct-and-code.md](.agents/guidelines/agent-conduct-and-code.md) |
| Documentation layers and markdown conventions | [.agents/guidelines/documentation-standards.md](.agents/guidelines/documentation-standards.md) |
| Cursor Cloud VM: services, tests, emulator, gotchas | [.agents/guidelines/cursor-cloud-environment.md](.agents/guidelines/cursor-cloud-environment.md) |
| Local clone, quickstart, badges, external links | [.agents/guidelines/local-developer-setup.md](.agents/guidelines/local-developer-setup.md) |
| Cloud Agent git and PR contract | [.agents/guidelines/CLOUD_AGENTS.md](.agents/guidelines/CLOUD_AGENTS.md) |

## General Rules

- The ground truth is in code
- Docs describe abstract ideas,
  never repeating information that can be directly derived from the code files:
  - higher-logical-level design of multiple code files
  - engineers' intended states of the code files
  - future directions
- Create skills, commands to abstract and automate repeated actions

## Override Rule

- User instructions always override this file.
- Do not create README.md, create AGENTS.md.

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
- No docstrings or comments on code that was not changed, except Python module-level doc blocks (see **Python module doc blocks** below).
- Inline comments only where logic is non-obvious.
- Read the file before modifying it. Never edit blind.

## Python module doc blocks (required)

- Every `.py` source file MUST start with a module-level docstring at the top that explains what the file is designed for and its role or behavior in the system.
- When adding a new `.py` file: include this doc block before other code.
- When editing an existing `.py` file that is missing or has an insufficient doc block: add or update it as part of the change.

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
- Use standard components: <https://developer.android.com/develop/ui/compose/components>

## Backend

- Backend services
  - Inty backend: `backend/inty` 支持 Android App 的主 API 后端，提供对话、生图、语音播报、语音通话等功能
  - Operational app:
    - `backend/ops` backend`evaluation/` operational app, creating iMates, view user behavior data etc.
  - Serving
  - 部署在一台 GCP VM
  - 后端所有应用都有 2 个环境：dev prod
    - .secrets/alien-paratext-461204-i9-cursor-log-viewer.json 可以用来访问

### 文档层次结构

- **最高层（面向人类读者）**：必须交代完整概念与适用边界；用约三分之一页纸篇幅做总体描述，使人一眼能判断「这是什么、和谁相关、要不要往下读」。人的注意力窗口有限，缺少这一层易导致误判优先级或读不下去。
- **中间层（仍面向人）**：按需展开：目录职责、如何运行、接口与约定、常见问题等；可分段、可链接到更细文档。
- **最底层（源码与实现细节）**：代码内注释、模块 docstring、PR/commit 中的实现说明等，主要给编码智能体与维护者阅读；详略由编写者按上下文自行判断，不以「人类扫读一整 repo」为第一约束。

### 工程文档维护

- Markdown 引用本仓库内文件时，使用从仓库根目录起的绝对路径（以 `/` 开头），例如 `/app/api/ENDPOINTS.md`、`/AGENTS.md`；不要使用 `../../app/api/ENDPOINTS.md` 这类相对路径。
- In markdown, reference in-repo files with repo-root absolute paths (leading `/`), e.g. `/app/api/ENDPOINTS.md`; do not use `../../...` relative paths.
- 当进行改动时，如变更足够重要且会影响相应目录的 `AGENTS.md` 指南、及其他 markdown 文件，请同步更新该目录下的 `AGENTS.md`、及其他 markdown 文件。
- 新功能/需求开发对应的文档应该添加 FR_ 前缀，如 docs/FR_CHAR_BOOSTING.md

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
2. **Inty backend (port 8000)**: `source .venv/bin/activate && ./backend/inty/start.sh --test`
   - `config.yaml` is auto-provisioned by the update script; no manual copy needed.
   - `--test` and `--dev` both enable dev startup (same seeds and uvicorn `--reload`); `start.sh` only differs by the banner string. Neither runs the evaluation static build (that is Ops `backend/ops/start.sh --local` only).
   - **`Environment.TEST` in Python** comes from `config.yaml` (`app.environment`), not from the `--test` CLI flag.
   - The server runs on `http://localhost:8000`
3. **Ops backend (port 8001, optional for REPL / ops stack)**: `source .venv/bin/activate && ./backend/ops/start.sh --local --no-build-frontend` skips `evaluation/build.sh` (faster startup if `app/static/evaluation` is already populated). Omit `--no-build-frontend` when you need a fresh evaluation static bundle. For REPL-style debugging, add `--debug --log-file ./inty-ops-local.log` (chat WS REPL: [`tools/inty_v2_repl/README.md`](tools/inty_v2_repl/README.md)). See `backend/ops/start.sh --help`.

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

## For human engineers

![](https://api.checklyhq.com/v1/badges/checks/6c7437a4-e239-473b-b08d-8285fc16ce4e?style=flat&theme=default&responseTime=true)
![](https://api.checklyhq.com/v1/badges/checks/1e149f71-dcad-49cc-a7bb-e0aecc429e6c?style=flat&theme=default&responseTime=true)
![](https://api.checklyhq.com/v1/badges/checks/f2988f0a-f58a-4e75-87bc-e5700869ba68?style=flat&theme=default&responseTime=true)

[![Android App Tests](https://github.com/NascentCore/inty/actions/workflows/ci_android_app.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_android_app.yaml)
[![CI - Backend](https://github.com/NascentCore/inty/actions/workflows/ci_backend.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_backend.yaml)
[![CI - Web App](https://github.com/NascentCore/inty/actions/workflows/ci_web_app.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/ci_web_app.yaml)
[![Validate configs](https://github.com/NascentCore/inty/actions/workflows/validate_config.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/validate_config.yaml)

[![dev-prod 同步 AI 角色](https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/sync_ai_chars.yaml)
[![Release - IntelliMate GPlay 内测轨道](https://github.com/NascentCore/inty/actions/workflows/build_and_upload_android.yaml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_upload_android.yaml)
[![Release - 构建部署 Inty Backend](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_backend.yml)
[![Release - 构建部署 Inty Push Worker](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_push_worker.yml/badge.svg)](https://github.com/NascentCore/inty/actions/workflows/build_and_deploy_push_worker.yml)

## 快速开始

[添加 SSH key 到你的 GitHub 账户](https://docs.github.com/zh/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)

```bash
# 克隆仓库并初始化子模块：
git clone --recurse-submodules git@github.com:NascentCore/inty.git
```

Android Studio 打开`inty/android_app`，详情参考 [android_app/README.md](android_app/README.md)。

后端系统代码位于 `app` 目录（目前正在逐步向 `backend` 目录迁移），参考 [backend/README.md](backend/README.md)。

如果子模块出现脏数据（如下图所示），可以按照下面的流程重置：

<img width="480" height="436" alt="image" src="https://github.com/user-attachments/assets/23852e45-cfe6-4686-9282-c138d40bf96f" />

```bash
# 清理子模块的缓存配置
git submodule deinit -f .

# 重新拉取子模块代码
git submodule update --init --recursive

# 使用下面步骤启动后端服务
cp devops/config.yaml.local config.yaml

# 创建虚拟环境供后端 python 代码运行
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt

# 启动 postgres 数据库
docker run --rm --name pg-inty -p 5432:5432 \
  -e POSTGRES_PASSWORD=sxwl666! \
  -e POSTGRES_DB=inty \
  -d postgres:16

# 启动主后端（Android API）
./backend/inty/start.sh --dev

# 启动 ops 平台（evaluation Web UI + ops API，默认 8001）
./backend/ops/start.sh --local
```

本地联调：本地后端+Android Studio App（USB 连接、wifi 连接不支持）指向本地后端

```bash
# 打开 Android Studio
# 选择 debug build type，编译运行
# 然后在 me->settings->backend 选择 local

# 同时打开端口代理、让模拟器可以访问本机端口
# -s 在多个模拟器时可以指向特定模拟器
adb reverse [-s <设备 ID>] tcp:8000 tcp:8000
```

### 相关链接

1. [IntelliMate Figma 设计稿](https://www.figma.com/design/ASvjVuWFM13S3u5GdIJlTL/HeartMate?node-id=0-1&p=f&t=nxD7Qrq5d8fZXSYl-0)
2. [IntelliMate 飞书需求池文档](https://tricorder.feishu.cn/wiki/Vx8zwSRiwigRUlkOyF5czkmdnDg?table=tblrLV9XLqUmPBu8&view=vewP2B92zv)
3. [IntelliMate Firebase 崩溃报告](https://console.firebase.google.com/project/alien-paratext-461204-i9/crashlytics/app/android:com.ai.intellimate/issues?fb_gclid=CjwKCAjwwNbEBhBpEiwAFYLtGL7ajs2-xPHLL4coQR6eSTui8PqkfhB7tNmotp8PWywmhtvPMR2hKhoCr5QQAvD_BwE&time=24h&state=open&types=crash&tag=all&sort=eventCount)
4. [IntelliMate Google Play Consle](https://play.google.com/console/u/0/developers/8311322450209629787/app/4972036709846537052/app-dashboard)
