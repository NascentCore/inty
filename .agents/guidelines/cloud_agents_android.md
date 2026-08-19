# Cloud Agent：Android 开发与 emulator

> 附录。主文档：[cloud_agents.md](cloud_agents.md)。Android SDK / AVD **不在** committed install 脚本里，通常来自 dashboard snapshot。

## SDK

- 路径：`/opt/android-sdk`（`ANDROID_HOME` / `ANDROID_SDK_ROOT` 在 `~/.bashrc`）
- Java 21；`android_app/local.properties` 设 `sdk.dir=/opt/android-sdk`（gitignored）
- SDK 目录须归当前用户所有（Gradle 才能自动装组件）

## 单元测试（镜像 CI）

```bash
cd android_app
./gradlew :app:testDebugUnitTest :core:common:testDebugUnitTest :core:data:testDebugUnitTest \
  :core:design:testDebugUnitTest :core:firebase:testDebugUnitTest \
  :library:utils:testDebugUnitTest :library:network:testDebugUnitTest
```

模块与 task 映射见 [`.github/workflows/ci_android_app.yaml`](../../.github/workflows/ci_android_app.yaml)。

## Emulator（无 KVM）

Cloud VM 在 Firecracker 里跑，**没有 KVM**（无 `/dev/kvm`）。可用软件模拟，但冷启动约 4 分钟（有 KVM 时约 20 秒）。

预置 AVD：`test_avd`（Pixel 6, API 36, google_apis/x86_64）

```bash
export ANDROID_HOME=/opt/android-sdk
export PATH="$ANDROID_HOME/emulator:$ANDROID_HOME/platform-tools:$PATH"

emulator -avd test_avd -no-window -no-audio -no-boot-anim \
  -no-accel -gpu swiftshader_indirect -no-snapshot &

adb wait-for-device
while [ "$(adb -s emulator-5554 shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" != "1" ]; do sleep 10; done
```

关键 flag：`-no-accel`（必须，否则报 KVM not found）、`-gpu swiftshader_indirect`（软件渲染）、`-no-snapshot`（避免 stale quickboot）。

Instrumented test：`cd android_app && ./gradlew connectedDebugAndroidTest`（需 emulator 已启动）。结束：`adb -s emulator-5554 emu kill`。 emulator 约占 1.5 GB RAM。
