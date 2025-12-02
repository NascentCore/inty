# 如何运行测试

## ⚠️ 重要提示

**Android 测试任务不支持 `--tests` 参数**。必须使用以下方式之一：

1. **使用 `-Pandroid.testInstrumentationRunnerArguments.class`** 运行特定测试类
2. **使用 `-Pandroid.testInstrumentationRunnerArguments.package`** 运行包下的所有测试
3. **在 Android Studio 中直接运行**（推荐，最简单）

## 测试文件位置

所有测试文件位于：
```
core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/local/
├── ChatTimestampTest.kt          # 时间戳相关测试
├── LoadMoreMessagesTest.kt       # prependMessages 测试
├── UpdateMessagesTest.kt         # updateMessages 保留 sortKey 测试
├── ConcurrencyTest.kt            # 并发场景测试
└── SyncStateTest.kt              # 同步状态管理测试
```

## 运行方式

### 方式 1：使用 Gradle 命令（推荐）

#### 运行所有测试
```bash
./gradlew :core:data:connectedDebugAndroidTest
```

#### 运行特定测试类
```bash
# 运行 UpdateMessagesTest
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=ai.sxwl.android.data.chat.local.UpdateMessagesTest

# 运行 ConcurrencyTest
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=ai.sxwl.android.data.chat.local.ConcurrencyTest

# 运行 SyncStateTest
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=ai.sxwl.android.data.chat.local.SyncStateTest

# 运行 LoadMoreMessagesTest
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=ai.sxwl.android.data.chat.local.LoadMoreMessagesTest

# 运行 ChatTimestampTest
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=ai.sxwl.android.data.chat.local.ChatTimestampTest
```

#### 运行特定测试方法
```bash
# 运行 UpdateMessagesTest 中的特定测试
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=ai.sxwl.android.data.chat.local.UpdateMessagesTest#updateMessagesPreservesSortKeyForExistingMessagesByLocalId

# 运行 ConcurrencyTest 中的并发测试
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=ai.sxwl.android.data.chat.local.ConcurrencyTest#concurrentAppendMessagesDoesNotCreateDuplicateSortKeys
```

#### 运行多个测试类（使用包名）
```bash
# 运行 chat.local 包下的所有测试
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.package=ai.sxwl.android.data.chat.local
```

### 方式 2：使用 Android Studio

1. **打开测试文件**：在 Android Studio 中打开任意测试文件（如 `UpdateMessagesTest.kt`）

2. **运行单个测试方法**：
   - 点击测试方法左侧的绿色运行按钮
   - 或右键点击测试方法 → "Run 'testMethodName()'"

3. **运行整个测试类**：
   - 点击测试类左侧的绿色运行按钮
   - 或右键点击测试类名 → "Run 'UpdateMessagesTest'"

4. **运行所有测试**：
   - 右键点击 `core/data/src/androidTest` 目录
   - 选择 "Run 'Tests in 'androidTest''"

### 方式 3：使用 ADB（需要连接设备/模拟器）

```bash
# 确保设备已连接
adb devices

# 运行所有测试
adb shell am instrument -w -r \
  -e class ai.sxwl.android.data.chat.local.UpdateMessagesTest \
  ai.sxwl.android.data.test/androidx.test.runner.AndroidJUnitRunner
```

## 前置条件

### 1. 连接设备或启动模拟器

**检查设备连接**：
```bash
adb devices
```

**启动模拟器**（如果使用）：
- 在 Android Studio 中：Tools → Device Manager → 启动模拟器
- 或使用命令行：`emulator -avd <avd_name>`

### 2. 确保应用已安装

测试会自动安装测试 APK，但需要确保主应用已安装：
```bash
./gradlew :app:installDebug
```

## 测试输出

### 查看测试结果

运行测试后，结果会显示在：
- **终端输出**：显示测试通过/失败信息
- **Android Studio**：Run 窗口显示详细结果
- **HTML 报告**：`core/data/build/reports/androidTests/connected/index.html`

### 查看测试报告

```bash
# 打开测试报告（macOS）
open core/data/build/reports/androidTests/connected/index.html

# 打开测试报告（Linux）
xdg-open core/data/build/reports/androidTests/connected/index.html
```

## 常见问题

### 1. 设备未连接
```
Error: No connected devices!
```
**解决**：连接设备或启动模拟器

### 2. 测试超时
```
TimeoutException: Timeout waiting for Flow emission
```
**解决**：增加 `withTimeout` 的时间，或检查测试逻辑

### 3. 数据库已关闭
```
IllegalStateException: Cannot perform this operation because the connection pool has been closed
```
**解决**：确保在 `tearDown` 中等待 Flow 完成后再关闭数据库

### 4. 测试失败：消息数量不匹配
```
AssertionError: expected:<4> but was:<0>
```
**解决**：检查 `waitForMessages` 是否正确等待 Flow 更新

## 快速测试命令

### 运行所有新测试（使用包名）
```bash
# 运行 chat.local 包下的所有测试（包括所有新测试）
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.package=ai.sxwl.android.data.chat.local
```

### 运行所有聊天相关测试
```bash
# 运行 chat 包下的所有测试
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.package=ai.sxwl.android.data.chat
```

### 只编译测试（不运行）
```bash
./gradlew :core:data:compileDebugAndroidTestKotlin
```

## 测试覆盖率

要查看测试覆盖率，需要配置 JaCoCo：

```bash
# 运行测试并生成覆盖率报告
./gradlew :core:data:connectedDebugAndroidTest jacocoTestReport

# 查看覆盖率报告
open core/data/build/reports/jacoco/jacocoTestReport/html/index.html
```

## 调试测试

### 在 Android Studio 中调试

1. 在测试方法中设置断点
2. 右键点击测试方法 → "Debug 'testMethodName()'"
3. 使用调试器逐步执行

### 查看日志

测试中的 `println` 和 `LogUtils` 输出会显示在：
- **Android Studio**：Logcat 窗口
- **命令行**：`adb logcat` 输出

### 查看数据库状态

可以在测试中添加代码查看数据库内容：
```kotlin
val dao = database.chatMessageDao()
val entities = dao.getAllMessages(agentId)
println("Database entities: ${entities.map { "${it.localId}: sortKey=${it.sortKey}" }}")
```

## 性能测试

对于并发测试，可以增加并发数量来测试性能：
```kotlin
// 在 ConcurrencyTest 中
val jobs = (1..100).map { ... } // 增加到 100 个并发
```

## 持续集成

在 CI/CD 中运行测试：
```yaml
# GitHub Actions 示例
- name: Run Android Tests
  run: |
    echo "y" | $ANDROID_HOME/tools/bin/sdkmanager "emulator"
    $ANDROID_HOME/emulator/emulator -avd test_avd -no-window &
    adb wait-for-device
    ./gradlew :core:data:connectedDebugAndroidTest
```

