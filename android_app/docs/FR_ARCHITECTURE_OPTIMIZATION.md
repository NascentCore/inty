# 架构优化工作计划

## 概述

本文档只制定了两个需要独立开发的架构优化任务的工作计划，其他优化项目一般伴随功能开发逐步迭代：
1. 封装底层逻辑，实现简单快捷调用（缓存与埋点）
2. 使用主题系统管理UI样式

**任务总览**：
- **任务一：封装底层逻辑**（4-5 人天）
  - 1.1.1 创建统一缓存管理 API：1.5-2 人天
  - 1.1.2 文件缓存操作封装：2 人天
  - 1.2.1 创建埋点 DSL API：1 人天
- **任务二：使用主题系统管理UI样式**（2-3 人天）
  - 2.1 创建基础颜色表：0.5 人天
  - 2.2 创建基础字体表：1 人天
  - 2.3 创建UI形状系统：0.5-1 人天
- **总计**：6.5-8 人天

---

## 任务一：封装底层逻辑，实现简单快捷调用

### 1.1 缓存系统封装（基于 DataStore）

**目标**：基于 Jetpack DataStore 封装统一的缓存管理 API，提供 StateFlow 响应式访问和 DSL 风格的保存操作。

**当前状态**：
- ✅ DataStore 依赖已引入（1.1.7）
- ✅ 已有部分 DataStore 使用示例（`BoostLeaderboardRankStore`、`PersonaPreferenceStore`）
- ⚠️ 当前主要使用 MMKV（`IntySetting`）进行键值对存储
- ⚠️ 存在分散的缓存管理器（`VideoCacheManager`、`AudioCacheManager`、`AgentCacheManager`）

**工作量**：3-4 人天

#### 子任务 1.1.1：创建统一缓存管理 API（1.5-2 人天）

**文件位置**：`core/data/src/main/kotlin/ai/sxwl/android/data/cache/`

**实现内容**：
1. 创建 `CacheManager` 接口和实现类
   - 支持键值对缓存（String, Int, Long, Boolean, Float）
   - 支持对象缓存（通过序列化）
   - 提供 StateFlow 访问接口
   - 提供 DSL 风格的保存操作

2. 创建 DSL 扩展函数
   ```kotlin
   // 示例 API
   cacheManager.save {
       putString("key", "value")
       putInt("count", 10)
       putObject("user", userObject)
   }
   
   val value: StateFlow<String?> = cacheManager.getStringFlow("key")
   ```

3. 支持用户级别和应用级别的缓存隔离

**依赖**：无

#### 子任务 1.1.2：文件缓存操作封装（2 人天）

**文件位置**：`core/data/src/main/kotlin/ai/sxwl/android/data/cache/FileCacheManager.kt`

**实现内容**：
1. 创建 `FileCacheManager` 类
   - 支持文件缓存（图片、视频、音频等）
   - 提供缓存路径管理

2. 与 DataStore 集成，记录文件缓存元数据

**依赖**：子任务 1.1.1

---

### 1.2 埋点系统 DSL 封装

**目标**：通过 DSL 方式简化埋点调用，提升开发效率和代码可读性。

**当前状态**：
- ✅ 已有 `FirebaseManager` 提供埋点功能
- ✅ 已有 `safeEventParams` 方法提供参数验证
- ⚠️ 当前调用方式较为繁琐，需要手动构建参数 Map

**工作量**：1 人天

#### 子任务 1.2.1：创建埋点 DSL API（1 人天）

**文件位置**：`core/firebase/src/main/kotlin/ai/sxwl/android/firebase/AnalyticsDSL.kt`

**实现内容**：
1. 创建 DSL 构建器
   ```kotlin
   // 示例 API
   trackEvent("button_clicked") {
       param("button_id", "login")
       param("screen", "splash")
   }
   
   trackScreen("chat_page") {
       param("agent_id", agentId)
   }
   ```

2. 提供类型安全的参数设置
3. 自动参数验证和规范化

**依赖**：现有 `FirebaseManager`

---

## 任务二：使用主题系统管理UI样式

**目标**：建立完整的主题系统，统一管理颜色、字体和形状，避免魔法值。

**当前状态**：
- ✅ 已有 `Color.kt` 定义颜色（Material3 主题色 + 自定义颜色）
- ⚠️ `Type.kt` 基本为空，未定义字体样式
- ⚠️ `UiConfigs.kt` 包含大量 UI 常量，但不够系统化
- ⚠️ 项目中仍存在直接使用魔法值的情况

**工作量**：2-3 人天

### 子任务 2.1：创建基础颜色表（0.5 人天）

**文件位置**：`core/design/src/main/kotlin/ai/sxwl/android/design/theme/Color.kt`

**实现内容**：
1. 整理现有颜色定义
2. 创建语义化颜色常量
   - 功能颜色（Primary, Secondary, Error, Success 等）
   - 场景颜色（Button, Card, Background 等）
   - 状态颜色（Enabled, Disabled, Hover 等）
3. 建立颜色命名规范
4. 从 `UiConfigs.kt` 迁移颜色定义到主题系统

**依赖**：无

### 子任务 2.2：创建基础字体表（1 人天）

**文件位置**：`core/design/src/main/kotlin/ai/sxwl/android/design/theme/Type.kt`

**实现内容**：
1. 定义完整的 Typography 系统
   ```kotlin
   val HeartTypography = Typography(
       displayLarge = TextStyle(...),
       displayMedium = TextStyle(...),
       // ... 完整的 Material3 Typography 定义
   )
   ```

2. 从 `UiConfigs.kt` 迁移字体大小定义
3. 创建自定义文本样式（如按钮文字、辅助文字等）
4. 提供字体大小、行高、字重等配置

**依赖**：无

### 子任务 2.3：创建UI形状系统（0.5-1 人天）

**文件位置**：`core/design/src/main/kotlin/ai/sxwl/android/design/theme/Shape.kt`

**实现内容**：
1. 创建形状定义文件
2. 定义不同场景下的圆角半径
   - 按钮形状（PrimaryButton, SecondaryButton 等）
   - 卡片形状（Card, Dialog 等）
   - 输入框形状
   - 其他组件形状
3. 从 `UiConfigs.kt` 迁移形状定义
4. 提供 `Shape` 对象供 Compose 使用

**依赖**：无

---

## 任务优先级与依赖关系

### 优先级排序
1. **P0（高优先级）**：任务一（缓存与埋点封装）- 提升开发效率
2. **P1（中优先级）**：任务二（主题系统）- 提升代码质量

### 依赖关系图
```
任务一（缓存与埋点）
├── 1.1.1 统一缓存管理 API（独立）
├── 1.1.2 文件缓存操作（依赖 1.1.1）
├── 1.2.1 埋点 DSL API（独立）

任务二（主题系统）
├── 2.1 基础颜色表（独立）
├── 2.2 基础字体表（独立）
├── 2.3 UI形状系统（独立）
```

## 验收标准

### 任务一验收标准
- [ ] 缓存系统提供 StateFlow 访问接口
- [ ] 缓存系统提供 DSL 保存操作
- [ ] 文件缓存功能完整
- [ ] 埋点 DSL API 可用
- [ ] 现有功能不受影响
- [ ] 所有缓存操作通过统一 API 进行

### 任务二验收标准
- [ ] 颜色系统完整且语义化
- [ ] 字体系统完整
- [ ] 形状系统完整

---

## 参考资料

- [Jetpack DataStore 官方文档](https://developer.android.com/topic/libraries/architecture/datastore)
- [Material3 设计指南](https://m3.material.io/)
- 项目现有代码：
  - `core/data/src/main/kotlin/ai/sxwl/android/data/store/BoostLeaderboardRankStore.kt` - DataStore 使用示例
  - `core/firebase/src/main/kotlin/ai/sxwl/android/firebase/FirebaseManager.kt` - 埋点实现
  - `core/design/src/main/kotlin/ai/sxwl/android/design/theme/` - 主题系统
  - `app/src/main/kotlin/com/ai/intellimate/ui/UiConfigs.kt` - UI 常量定义

---