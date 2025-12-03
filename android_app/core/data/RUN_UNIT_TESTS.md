# 如何运行 RoomDataSourceTest 单元测试

## ⚠️ 重要提示

`RoomDataSourceTest` 是一个**单元测试**（位于 `src/test`），但由于 `RoomDataSource` 依赖 Android 环境（`LogUtils`、`IntySetting` 需要 Android Context），这些测试实际上需要 Android 测试环境。

## 运行方式

### 方式 1：使用 Gradle 命令（推荐）

#### 运行所有单元测试
```bash
./gradlew :core:data:testDebugUnitTest
```

#### 运行特定测试类
```bash
./gradlew :core:data:testDebugUnitTest --tests "ai.sxwl.android.data.chat.data.RoomDataSourceTest"
```

#### 运行特定测试方法
```bash
# 运行单个测试方法
./gradlew :core:data:testDebugUnitTest --tests "ai.sxwl.android.data.chat.data.RoomDataSourceTest.getMessagesFlow*"

# 运行多个测试方法（使用通配符）
./gradlew :core:data:testDebugUnitTest --tests "ai.sxwl.android.data.chat.data.RoomDataSourceTest.*updateMessages*"
```

### 方式 2：使用 Android Studio（最简单）

1. **打开测试文件**：在 Android Studio 中打开 `RoomDataSourceTest.kt`

2. **运行单个测试方法**：
   - 点击测试方法左侧的绿色运行按钮 ▶️
   - 或右键点击测试方法 → "Run 'testMethodName()'"

3. **运行整个测试类**：
   - 点击测试类左侧的绿色运行按钮 ▶️
   - 或右键点击测试类名 → "Run 'RoomDataSourceTest'"

4. **运行所有单元测试**：
   - 右键点击 `core/data/src/test` 目录
   - 选择 "Run 'Tests in 'test''"

### 方式 3：查看测试报告

运行测试后，查看 HTML 报告：
```bash
# macOS
open core/data/build/reports/tests/testDebugUnitTest/index.html

# Linux
xdg-open core/data/build/reports/tests/testDebugUnitTest/index.html
```

## 当前问题

由于 `RoomDataSource` 依赖 Android 环境：
- `LogUtils` 在类加载时就需要 Android Application Context（无法在单元测试中 mock）
- `IntySetting` 需要 MMKV（需要 Android Context）

这些依赖在单元测试中无法直接 mock，导致测试失败。测试代码中已移除对 `LogUtils` 的 mock 尝试。

## 解决方案

### 选项 1：将测试迁移到 Android 测试（推荐）

将 `RoomDataSourceTest.kt` 移动到 `src/androidTest` 目录，这样可以使用真实的 Android 环境：

```bash
# 移动文件
mv core/data/src/test/kotlin/ai/sxwl/android/data/chat/data/RoomDataSourceTest.kt \
   core/data/src/androidTest/kotlin/ai/sxwl/android/data/chat/data/RoomDataSourceTest.kt

# 然后使用 Android 测试命令运行
./gradlew :core:data:connectedDebugAndroidTest \
  -Pandroid.testInstrumentationRunnerArguments.class=ai.sxwl.android.data.chat.data.RoomDataSourceTest
```

### 选项 2：使用 Robolectric（需要添加依赖）

添加 Robolectric 依赖来模拟 Android 环境：

```kotlin
// 在 build.gradle.kts 中添加
testImplementation("org.robolectric:robolectric:4.11.1")

// 在测试类上添加注解
@RunWith(RobolectricTestRunner::class)
class RoomDataSourceTest { ... }
```

### 选项 3：重构代码以支持单元测试

将 `LogUtils` 和 `IntySetting` 的调用抽象为接口，在测试中注入 mock 实现。

## 快速测试命令

```bash
# 运行所有单元测试
./gradlew :core:data:testDebugUnitTest

# 运行特定测试类
./gradlew :core:data:testDebugUnitTest --tests "ai.sxwl.android.data.chat.data.RoomDataSourceTest"

# 只编译测试（不运行）
./gradlew :core:data:compileDebugUnitTestKotlin
```

## 测试覆盖率

要查看测试覆盖率，需要配置 JaCoCo：

```bash
# 运行测试并生成覆盖率报告
./gradlew :core:data:testDebugUnitTest jacocoTestReport

# 查看覆盖率报告
open core/data/build/reports/jacoco/jacocoTestReport/html/index.html
```

