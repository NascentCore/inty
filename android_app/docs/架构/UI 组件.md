# UI 组件

本文档记录 app 内可复用的 Compose UI 组件，便于统一视觉与交互、避免重复实现。

---

## IntelliMateCtaButton

**路径**：`app/src/main/kotlin/com/ai/intellimate/ui/components/IntelliMateCtaButton.kt`

与「Create My IntelliMate」一致的 CTA 按钮：粉→橙水平渐变、全宽圆角、白字，适用于需要强主操作按钮的场景。

### 适用范围

- 创建/编辑 IntelliMate 页底部（Create My IntelliMate / Update My IntelliMate）
- Explore 列表加载完毕后的「Explore More」按钮
- 其他需要同一视觉强度的主操作入口

### 视觉效果

- 全宽、圆角 25.dp、高 56.dp
- 水平渐变：粉红（`AppColors.IntelliMateCtaGradientStart`）→ 橙（`AppColors.IntelliMateCtaGradientEnd`）
- 白字 18.sp SemiBold
- `isLoading == true` 时显示白色 24.dp `CircularProgressIndicator`，并禁用点击
- 内置防连点（AntiClick）

### 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `text` | String | — | 按钮文案 |
| `onClick` | () -> Unit | — | 点击回调 |
| `modifier` | Modifier | Modifier | 布局修饰符 |
| `isLoading` | Boolean | false | 是否显示 loading 并禁用点击 |
| `enabled` | Boolean | true | 是否可点击（与 loading 共同生效） |

### 使用示例

```kotlin
// 创建页主按钮
IntelliMateCtaButton(
    text = if (isEditMode) "Update My IntelliMate" else "Create My IntelliMate",
    isLoading = isLoading,
    onClick = { /* 提交逻辑 */ },
)

// Explore More
IntelliMateCtaButton(
    text = stringResource(R.string.explore_loading_explore_more),
    onClick = onExploreMore,
)
```

### 相关配置

- 渐变色：`core/design/.../Color.kt` 中 `AppColors.IntelliMateCtaGradientStart` / `IntelliMateCtaGradientEnd`
- 尺寸：`UiConfigs.Size.CtaButtonHeight`（56.dp）、`UiConfigs.Shape.PrimaryButton`（25.dp）
