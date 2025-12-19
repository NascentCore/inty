# 运行单元测试

## 运行 EnergyCelebrationBannerTest

### 方式 1：使用 Gradle 命令（推荐）

#### 运行所有单元测试
```bash
cd android_app
./gradlew :app:testDebugUnitTest
```

#### 运行特定测试类
```bash
cd android_app
./gradlew :app:testDebugUnitTest --tests "com.ai.intellimate.chat.ui.EnergyCelebrationBannerTest"
```

#### 运行特定测试方法
```bash
cd android_app
./gradlew :app:testDebugUnitTest --tests "com.ai.intellimate.chat.ui.EnergyCelebrationBannerTest.resolveCelebrationLevel_firstPoint_returnsFirst"
```

#### 运行多个测试方法
```bash
cd android_app
./gradlew :app:testDebugUnitTest --tests "com.ai.intellimate.chat.ui.EnergyCelebrationBannerTest.resolveCelebrationLevel_*"
```

### 方式 2：使用 Android Studio（最简单）

1. **打开测试文件**：在 Android Studio 中打开 `EnergyCelebrationBannerTest.kt`

2. **运行单个测试方法**：
   - 点击测试方法左侧的绿色运行按钮 ▶️
   - 或右键点击测试方法 → "Run 'testMethodName()'"

3. **运行整个测试类**：
   - 点击测试类左侧的绿色运行按钮 ▶️
   - 或右键点击测试类名 → "Run 'EnergyCelebrationBannerTest'"

4. **运行所有测试**：
   - 右键点击 `app/src/test` 目录
   - 选择 "Run 'Tests in 'test''"

### 方式 3：查看测试报告

运行测试后，可以在以下位置查看测试报告：

```bash
# 打开测试报告（macOS）
open android_app/app/build/reports/tests/testDebugUnitTest/index.html

# 打开测试报告（Linux）
xdg-open android_app/app/build/reports/tests/testDebugUnitTest/index.html
```

## 常见问题

### 1. SDK location not found
```
SDK location not found. Define a valid SDK location with an ANDROID_HOME environment variable
```

**解决**：设置 Android SDK 路径
```bash
export ANDROID_HOME=$HOME/Library/Android/sdk  # macOS
# 或
export ANDROID_HOME=$HOME/Android/Sdk  # Linux
```

### 2. 测试编译失败
确保项目已正确同步：
```bash
cd android_app
./gradlew clean
./gradlew :app:testDebugUnitTest
```

### 3. 只编译不运行
```bash
cd android_app
./gradlew :app:compileDebugUnitTestKotlin
```

## 调试测试

在 Android Studio 中：
1. 在测试方法中设置断点
2. 右键点击测试方法 → "Debug 'testMethodName()'"
3. 使用调试器逐步执行

