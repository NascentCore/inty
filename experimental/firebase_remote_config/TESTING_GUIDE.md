# Firebase Remote Config AB 测试详细测试指南

本文档提供详细的步骤说明，帮助您完成 Firebase Remote Config AB 测试的完整测试流程。

## 目录

1. [前置准备](#前置准备)
2. [Firebase 项目设置](#firebase-项目设置)
3. [应用配置](#应用配置)
4. [Remote Config 参数配置](#remote-config-参数配置)
5. [AB 测试条件设置](#ab-测试条件设置)
6. [构建和运行应用](#构建和运行应用)
7. [测试不同变体](#测试不同变体)
8. [验证配置生效](#验证配置生效)
9. [测试场景清单](#测试场景清单)
10. [故障排查](#故障排查)

---

## 前置准备

### 1.1 环境要求

- ✅ Android Studio Hedgehog (2023.1.1) 或更高版本
- ✅ JDK 8 或更高版本
- ✅ Android SDK (API 24+)
- ✅ 一个 Google 账号（用于访问 Firebase Console）
- ✅ Android 设备或模拟器（API 24+）

### 1.2 检查项目文件

确认以下文件存在：

```
experimental/firebase_remote_config/
├── app/
│   ├── build.gradle.kts
│   ├── google-services.json.example
│   └── src/main/
│       ├── AndroidManifest.xml
│       └── java/com/example/firebaseremoteconfig/
│           ├── MainActivity.kt
│           ├── RemoteConfigManager.kt
│           └── ABTestVariant.kt
├── build.gradle.kts
├── settings.gradle.kts
└── README.md
```

---

## Firebase 项目设置

### 2.1 创建 Firebase 项目

1. **访问 Firebase Console**
   - 打开浏览器，访问：https://console.firebase.google.com/
   - 使用 Google 账号登录

2. **创建新项目**
   - 点击 **"添加项目"** 或 **"Create a project"**
   - 输入项目名称，例如：`remote-config-ab-test-demo`
   - 点击 **"继续"** 或 **"Continue"**

3. **配置 Google Analytics（可选）**
   - 可以选择启用或禁用 Google Analytics
   - 如果启用，选择或创建 Analytics 账号
   - 点击 **"创建项目"** 或 **"Create project"**

4. **等待项目创建完成**
   - 通常需要 1-2 分钟
   - 创建完成后点击 **"继续"** 或 **"Continue"**

### 2.2 添加 Android 应用

1. **在项目概览页面添加应用**
   - 点击 Android 图标（🐢）或 **"Add app"** → **"Android"**

2. **填写应用信息**
   ```
   Android 软件包名称: com.example.firebaseremoteconfig
   应用昵称（可选）: Remote Config AB Test Demo
   调试签名证书 SHA-1（可选）: 暂时留空
   ```

3. **注册应用**
   - 点击 **"注册应用"** 或 **"Register app"**

4. **下载配置文件**
   - 点击 **"下载 google-services.json"** 按钮
   - 保存文件到本地

5. **将配置文件添加到项目**
   ```bash
   # 方法 1: 使用命令行
   cp ~/Downloads/google-services.json experimental/firebase_remote_config/app/
   
   # 方法 2: 使用 Android Studio
   # 直接将文件拖拽到 app/ 目录下
   ```

6. **验证文件位置**
   ```
   experimental/firebase_remote_config/app/google-services.json ✅
   ```

7. **完成设置**
   - 在 Firebase Console 中点击 **"下一步"** → **"继续"** → **"继续"**
   - 暂时跳过后续步骤（已在代码中配置）

### 2.3 启用 Remote Config

1. **导航到 Remote Config**
   - 在 Firebase Console 左侧菜单中
   - 找到 **"Remote Config"** 或 **"远程配置"**
   - 点击进入

2. **首次使用提示**
   - 如果是首次使用，会看到欢迎页面
   - 点击 **"创建配置"** 或 **"Create configuration"**

---

## 应用配置

### 3.1 在 Android Studio 中打开项目

1. **打开 Android Studio**
   - 启动 Android Studio

2. **导入项目**
   - 点击 **File** → **Open**
   - 导航到 `experimental/firebase_remote_config` 目录
   - 点击 **OK**

3. **等待 Gradle 同步**
   - Android Studio 会自动同步 Gradle 文件
   - 等待同步完成（首次可能需要几分钟）

4. **检查同步状态**
   - 查看底部状态栏，应显示 "Gradle sync finished"
   - 如有错误，检查 `google-services.json` 是否正确放置

### 3.2 验证依赖配置

1. **检查 build.gradle.kts**
   - 打开 `app/build.gradle.kts`
   - 确认包含以下插件：
     ```kotlin
     plugins {
         id("com.android.application")
         id("org.jetbrains.kotlin.android")
         id("com.google.gms.google-services")  // ✅ 必须存在
     }
     ```

2. **检查依赖**
   - 确认包含 Firebase Remote Config：
     ```kotlin
     implementation(platform("com.google.firebase:firebase-bom:32.7.0"))
     implementation("com.google.firebase:firebase-config-ktx")
     ```

3. **重新同步（如需要）**
   - 如果修改了依赖，点击 **File** → **Sync Project with Gradle Files**

---

## Remote Config 参数配置

### 4.1 添加第一个参数：按钮颜色变体

1. **在 Firebase Console 中打开 Remote Config**
   - 导航到：**Remote Config** → **参数** 或 **Parameters**

2. **添加参数**
   - 点击 **"添加参数"** 或 **"Add parameter"**

3. **配置参数 1：button_color_variant**
   ```
   参数键: button_color_variant
   默认值: control
   说明（可选）: AB测试按钮颜色变体 - control/variant_a/variant_b
   ```

4. **保存参数**
   - 点击 **"保存"** 或 **"Save"**

### 4.2 添加第二个参数：欢迎消息

1. **再次点击 "添加参数"**

2. **配置参数 2：welcome_message**
   ```
   参数键: welcome_message
   默认值: 欢迎使用应用！
   说明（可选）: 应用欢迎消息文本
   ```

3. **保存参数**

### 4.3 添加第三个参数：新功能开关

1. **再次点击 "添加参数"**

2. **配置参数 3：enable_new_feature**
   ```
   参数键: enable_new_feature
   默认值: false
   数据类型: Boolean（布尔值）
   说明（可选）: 是否启用新功能
   ```

3. **设置数据类型**
   - 在参数值输入框右侧，点击数据类型下拉菜单
   - 选择 **Boolean**
   - 输入 `false` 作为默认值

4. **保存参数**

### 4.4 发布配置

1. **检查所有参数**
   - 确认三个参数都已添加：
     - ✅ `button_color_variant` = `control`
     - ✅ `welcome_message` = `欢迎使用应用！`
     - ✅ `enable_new_feature` = `false`

2. **发布配置**
   - 点击右上角的 **"发布"** 或 **"Publish"** 按钮
   - 确认发布（可能要求输入发布说明）

3. **等待发布完成**
   - 通常几秒钟内完成
   - 发布后，配置会立即生效

---

## AB 测试条件设置

### 5.1 了解条件系统

Firebase Remote Config 支持基于条件的参数值分配：
- **随机百分比**：随机分配用户到不同变体
- **用户属性**：基于用户属性（地区、语言等）
- **应用版本**：基于应用版本号
- **设备类型**：基于设备类型

### 5.2 设置变体 A（10% 用户）

1. **编辑 button_color_variant 参数**
   - 在参数列表中，找到 `button_color_variant`
   - 点击参数行的 **"条件"** 或 **"Condition"** 列

2. **创建新条件**
   - 点击 **"添加条件"** 或 **"Add condition"**
   - 选择 **"随机百分比"** 或 **"Random percentile"**

3. **配置条件 1**
   ```
   条件名称: 10% 用户变体 A
   条件类型: 随机百分比
   百分比范围: 0-10
   值: variant_a
   ```

4. **详细步骤**
   - **条件名称**：输入 `10% 用户变体 A`
   - **条件类型**：选择 **"Random percentile"**
   - **百分比设置**：
     - First percentile: `0`
     - Last percentile: `10`
   - **值**：输入 `variant_a`
   - 点击 **"完成"** 或 **"Done"**

### 5.3 设置变体 B（10% 用户）

1. **再次添加条件**
   - 在同一个参数下，再次点击 **"添加条件"**

2. **配置条件 2**
   ```
   条件名称: 10% 用户变体 B
   条件类型: 随机百分比
   百分比范围: 10-20
   值: variant_b
   ```

3. **详细步骤**
   - **条件名称**：输入 `10% 用户变体 B`
   - **条件类型**：选择 **"Random percentile"**
   - **百分比设置**：
     - First percentile: `10`
     - Last percentile: `20`
   - **值**：输入 `variant_b`
   - 点击 **"完成"**

### 5.4 确认默认值（80% 用户）

1. **检查默认值**
   - 确保默认值（Default value）为 `control`
   - 这对应剩余的 80% 用户（0-10% 变体A，10-20% 变体B，20-100% 对照组）

2. **最终配置应如下**
   ```
   button_color_variant:
   - 条件: 10% 用户变体 A → variant_a
   - 条件: 10% 用户变体 B → variant_b
   - 默认值: control
   ```

### 5.5 发布 AB 测试配置

1. **保存所有更改**
   - 点击 **"发布"** 或 **"Publish"**

2. **添加发布说明（可选）**
   ```
   发布说明: 设置按钮颜色 AB 测试，10% 用户变体A，10% 用户变体B，80% 对照组
   ```

3. **确认发布**

---

## 构建和运行应用

### 6.1 准备设备或模拟器

#### 选项 A：使用 Android 模拟器

1. **打开 AVD Manager**
   - Android Studio → **Tools** → **Device Manager**
   - 或点击工具栏的设备图标

2. **创建虚拟设备**
   - 点击 **"Create Device"**
   - 选择设备型号（推荐：Pixel 5）
   - 选择系统镜像（API 24+，推荐 API 33）
   - 完成创建

3. **启动模拟器**
   - 在设备列表中，点击播放按钮启动模拟器
   - 等待模拟器完全启动

#### 选项 B：使用物理设备

1. **启用开发者选项**
   - 设置 → 关于手机 → 连续点击"版本号"7次

2. **启用 USB 调试**
   - 设置 → 开发者选项 → 启用"USB 调试"

3. **连接设备**
   - 使用 USB 连接设备到电脑
   - 确认设备授权 USB 调试

4. **验证连接**
   ```bash
   adb devices
   # 应该显示设备列表
   ```

### 6.2 构建应用

1. **选择构建变体**
   - Android Studio 底部工具栏
   - 点击 **"Build Variants"** 标签
   - 选择 **debug** 变体

2. **清理项目（可选）**
   - **Build** → **Clean Project**

3. **构建项目**
   - **Build** → **Rebuild Project**
   - 等待构建完成

4. **检查构建输出**
   - 查看底部 **"Build"** 标签
   - 确认显示 "BUILD SUCCESSFUL"

### 6.3 运行应用

1. **选择运行配置**
   - 顶部工具栏，选择目标设备
   - 选择 **app** 模块

2. **运行应用**
   - 点击绿色的运行按钮（▶️）
   - 或按快捷键 `Shift + F10`

3. **等待安装**
   - Android Studio 会自动安装 APK
   - 首次安装可能需要 1-2 分钟

4. **应用启动**
   - 应用会自动启动
   - 首次启动会从 Firebase 获取配置

---

## 测试不同变体

### 7.1 首次运行测试

1. **观察应用界面**
   - 应用应显示主界面
   - 查看以下元素：
     - ✅ 欢迎消息区域
     - ✅ 按钮颜色变体显示
     - ✅ 测试按钮（显示当前变体的颜色）
     - ✅ 新功能开关
     - ✅ 配置状态信息

2. **记录当前变体**
   - 查看"当前按钮变体"显示的值
   - 可能是：`对照组`、`变体 A` 或 `变体 B`
   - 记录下当前变体

3. **验证按钮颜色**
   - 检查测试按钮的颜色：
     - **对照组**：紫色 (#6200EE)
     - **变体 A**：蓝色 (#2196F3)
     - **变体 B**：红色 (#F44336)

4. **检查配置状态**
   - 查看"配置状态"区域
   - 确认显示"配置已加载"
   - 记录最后获取时间

### 7.2 测试配置刷新

1. **手动刷新配置**
   - 点击"刷新配置"按钮
   - 观察加载状态（按钮应显示加载指示器）

2. **验证刷新结果**
   - 如果配置有更新，会显示"配置已更新"
   - 如果无更新，会显示"配置已是最新"
   - 检查最后获取时间是否更新

3. **观察变体变化**
   - 如果在 Firebase Console 中修改了配置
   - 刷新后应该看到新的变体值

### 7.3 测试不同变体（强制指定）

#### 方法 1：使用 Firebase Console 临时覆盖

1. **在 Firebase Console 中修改默认值**
   - Remote Config → 编辑 `button_color_variant`
   - 将默认值改为 `variant_a`
   - 发布配置

2. **在应用中刷新**
   - 点击"刷新配置"按钮
   - 观察按钮颜色变为蓝色

3. **测试其他变体**
   - 重复步骤，测试 `variant_b`（红色）和 `control`（紫色）

#### 方法 2：修改代码强制指定（仅用于测试）

1. **临时修改 RemoteConfigManager.kt**
   ```kotlin
   fun getButtonColorVariant(): String {
       // 临时强制返回 variant_a 用于测试
       return "variant_a"
       // return remoteConfig.getString(KEY_BUTTON_COLOR_VARIANT)
   }
   ```

2. **重新运行应用**
   - 应该看到变体 A（蓝色按钮）

3. **测试完成后恢复**
   - 撤销代码修改
   - 恢复原来的实现

### 7.4 测试其他参数

1. **测试欢迎消息**
   - 在 Firebase Console 中修改 `welcome_message`
   - 例如改为：`欢迎来到 AB 测试演示！`
   - 发布配置，在应用中刷新

2. **测试新功能开关**
   - 在 Firebase Console 中修改 `enable_new_feature`
   - 将值改为 `true`
   - 发布配置，在应用中刷新
   - 开关应变为启用状态

---

## 验证配置生效

### 8.1 验证配置获取

1. **检查日志输出**
   - 在 Android Studio 中打开 **Logcat**
   - 过滤标签：`RemoteConfigManager`
   - 应该看到配置获取的日志：
     ```
     D/RemoteConfigManager: Config fetched and activated: true
     ```

2. **检查配置状态**
   - 应用中查看"配置状态"区域
   - 确认显示正确的获取时间
   - 确认状态为"成功"

### 8.2 验证 AB 测试分配

1. **多次运行应用**
   - 卸载应用（模拟新用户）
   - 重新安装并运行
   - 记录分配的变体

2. **统计变体分布**
   - 运行 10-20 次（每次卸载重装）
   - 统计各变体的出现次数
   - 预期分布：
     - 对照组：约 80%
     - 变体 A：约 10%
     - 变体 B：约 10%

3. **验证随机性**
   - 多次测试应该看到不同的变体分配
   - 不应该每次都得到相同的变体

### 8.3 验证配置缓存

1. **断开网络**
   - 在设备设置中关闭 Wi-Fi/移动数据

2. **重新启动应用**
   - 完全关闭应用
   - 重新打开

3. **验证使用缓存**
   - 应用应该仍能正常显示
   - 使用之前缓存的配置值
   - 配置状态可能显示旧的时间戳

4. **恢复网络**
   - 重新连接网络
   - 点击"刷新配置"
   - 应该能获取最新配置

---

## 测试场景清单

### ✅ 基础功能测试

- [ ] 应用能够正常启动
- [ ] Firebase Remote Config 成功初始化
- [ ] 配置能够成功获取
- [ ] 默认值正确显示
- [ ] UI 正确显示所有元素

### ✅ AB 测试功能测试

- [ ] 能够正确分配不同变体
- [ ] 按钮颜色随变体正确变化
- [ ] 变体分配符合预期比例（约 80%/10%/10%）
- [ ] 同一用户多次运行保持相同变体（除非卸载重装）

### ✅ 配置刷新测试

- [ ] 手动刷新配置功能正常
- [ ] 刷新后能获取最新配置
- [ ] 刷新后 UI 正确更新
- [ ] 加载状态正确显示

### ✅ 参数测试

- [ ] `button_color_variant` 参数正确读取
- [ ] `welcome_message` 参数正确显示
- [ ] `enable_new_feature` 布尔值正确读取
- [ ] 参数修改后刷新能正确更新

### ✅ 网络和错误处理测试

- [ ] 网络断开时使用缓存配置
- [ ] 配置获取失败时使用默认值
- [ ] 错误信息正确显示
- [ ] 网络恢复后能正常获取配置

### ✅ Firebase Console 集成测试

- [ ] 在 Console 中修改参数能生效
- [ ] 发布配置后应用能获取更新
- [ ] 条件设置正确工作
- [ ] 多个条件正确评估

---

## 故障排查

### 问题 1：应用无法启动

**症状**：应用崩溃或无法安装

**检查清单**：
1. ✅ 确认 `google-services.json` 已正确放置在 `app/` 目录
2. ✅ 确认包名与 Firebase 项目中配置的一致：`com.example.firebaseremoteconfig`
3. ✅ 检查 AndroidManifest.xml 中的包名
4. ✅ 确认已添加 Google Services 插件
5. ✅ 清理并重新构建项目

**解决方法**：
```bash
# 清理项目
./gradlew clean

# 重新构建
./gradlew build
```

### 问题 2：无法获取 Remote Config

**症状**：配置状态显示错误，或一直显示默认值

**检查清单**：
1. ✅ 确认 Firebase 项目已启用 Remote Config
2. ✅ 确认参数已发布（不是草稿状态）
3. ✅ 检查网络连接
4. ✅ 查看 Logcat 中的错误日志
5. ✅ 确认应用有网络权限

**解决方法**：
- 检查 AndroidManifest.xml 中是否有 `<uses-permission android:name="android.permission.INTERNET" />`
- 在 Firebase Console 中确认配置已发布
- 检查 Logcat 中的详细错误信息

### 问题 3：变体分配不正确

**症状**：总是得到相同的变体，或变体分布不符合预期

**检查清单**：
1. ✅ 确认 Firebase Console 中条件设置正确
2. ✅ 确认百分比范围没有重叠
3. ✅ 确认默认值设置正确
4. ✅ 测试时是否每次都卸载重装（模拟新用户）

**解决方法**：
- 每次测试前卸载应用（模拟新用户）
- 检查条件配置，确保百分比范围正确：
  - 变体 A: 0-10
  - 变体 B: 10-20
  - 对照组: 20-100（默认值）

### 问题 4：配置刷新不生效

**症状**：修改配置后刷新，应用仍显示旧值

**检查清单**：
1. ✅ 确认 Firebase Console 中配置已发布
2. ✅ 检查 `minimumFetchIntervalInSeconds` 设置
3. ✅ 确认网络连接正常
4. ✅ 查看 Logcat 确认刷新是否成功

**解决方法**：
- 开发时可以设置 `minimumFetchIntervalInSeconds = 0`（每次都能获取）
- 生产环境建议设置为 3600（1小时）
- 确认配置发布后等待几秒钟再刷新

### 问题 5：布尔值参数读取错误

**症状**：`enable_new_feature` 总是返回 false

**检查清单**：
1. ✅ 确认参数类型设置为 Boolean
2. ✅ 确认默认值格式正确（true/false，小写）
3. ✅ 检查代码中获取布尔值的方法

**解决方法**：
- 在 Firebase Console 中确认参数类型为 Boolean
- 使用 `remoteConfig.getBoolean()` 方法获取布尔值
- 检查默认值设置是否正确

### 问题 6：应用图标不显示

**症状**：应用图标显示为默认 Android 图标

**检查清单**：
1. ✅ 确认 `ic_launcher.xml` 文件存在
2. ✅ 确认 AndroidManifest.xml 中图标引用正确
3. ✅ 清理并重新构建

**解决方法**：
- 这只是演示应用，图标问题不影响功能测试
- 如需修复，可以替换为实际的 PNG 图标文件

---

## 进阶测试

### 测试条件组合

1. **基于用户属性的条件**
   - 在 Firebase Console 中创建基于语言的条件
   - 例如：中文用户显示变体 A，英文用户显示变体 B

2. **基于应用版本的条件**
   - 创建基于版本号的条件
   - 测试不同版本的用户看到不同变体

### 性能测试

1. **配置获取时间**
   - 测量首次配置获取所需时间
   - 测量配置刷新所需时间

2. **缓存效果**
   - 验证缓存机制是否正常工作
   - 测试离线场景下的表现

### 集成测试

1. **与 Analytics 集成**
   - 记录配置获取事件
   - 跟踪不同变体的用户行为

2. **多设备测试**
   - 在不同设备上测试
   - 验证配置一致性

---

## 测试报告模板

完成测试后，可以记录以下信息：

```
测试日期: ___________
测试人员: ___________
设备信息: ___________
Android 版本: ___________

测试结果:
- 应用启动: ✅ / ❌
- 配置获取: ✅ / ❌
- 变体分配: ✅ / ❌
- 配置刷新: ✅ / ❌

变体分布统计（运行 20 次）:
- 对照组: __ 次 (__%)
- 变体 A: __ 次 (__%)
- 变体 B: __ 次 (__%)

发现的问题:
1. ___________
2. ___________

备注:
___________
```

---

## 参考资源

- [Firebase Remote Config 官方文档](https://firebase.google.com/docs/remote-config)
- [Firebase Remote Config Android API](https://firebase.google.com/docs/reference/android/com/google/firebase/remoteconfig/FirebaseRemoteConfig)
- [Firebase Console](https://console.firebase.google.com/)
- [Android Studio 文档](https://developer.android.com/studio)

---

## 下一步

完成基础测试后，可以：

1. **集成 Analytics**：跟踪不同变体的效果
2. **添加更多测试场景**：如不同的 UI 布局、文案等
3. **自动化测试**：编写单元测试和 UI 测试
4. **生产环境部署**：配置生产环境的 Remote Config 参数

---

**祝测试顺利！** 🎉

如有问题，请参考故障排查部分或查看 Firebase 官方文档。
