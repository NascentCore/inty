# FR: IntySettings 从 MMKV 逐项迁移到 DataStore（1 by 1）

<!-- CREATED_BY_AGENT -->

## 1. 目标与范围

### 1.1 目标

将当前 `IntySetting`（MMKV）中的设置项，按 **一次迁移一个 setting entry** 的方式，平滑迁移到 DataStore，避免大爆炸重构。

### 1.2 成功标准

1. 每一轮迭代只迁移 1 个 entry（单个 key 或单个前缀族）。
2. 迁移后的 entry 在功能行为上与 MMKV 阶段一致（默认值、切账号行为、读写时机一致）。
3. 可回滚（遇到线上问题可快速切回 MMKV 读路径）。
4. 最终下线 `IntySetting` 对 MMKV 的依赖（最后阶段）。

### 1.3 非目标（本计划不做）

- 不在同一迭代内批量迁移多个 entry。
- 不一次性替换所有 `IntySetting` 调用点。
- 不在本计划内改动 Room 聊天存储方案。

---

## 2. 当前现状（代码事实）

当前 `IntySetting` 有两类 MMKV：

- `allUserSetting`（应用级，例：`cur_uid`、`show_guest`、`app_data_*`）
- `curUserSetting`（用户级，例：token、各种偏好、会话状态、收藏状态等）

已存在 DataStore 基础设施：

- `DataStoreManager.kt`
- `JsonDattaStoreExt.kt`
- 现有 DataStore 实战：`UserProfileManager`、`PersonaPreferenceStore`、`BoostLeaderboardRankStore`

**核心挑战：**

1. `IntySetting` 目前大量是同步 getter，而 DataStore 是异步/Flow。
2. 存在动态 key（如 `conversation_hidden_{agentId}`、`explore_favorite_{agentId}`、`app_data_*`）。
3. 存在登录态关键数据（`cur_uid` / `token`），风险最高，必须后置迁移。

---

## 3. 总体策略（必须遵守）

## 3.1 逐项迁移策略

每轮只迁 1 个 entry，采用固定状态机：

1. `MMKV_ONLY`（初始）
2. `DS_DUAL_WRITE_DS_FIRST_READ`（DataStore 优先读，缺失时 fallback MMKV 并回填 DataStore）
3. `DS_ONLY`（稳定后仅 DataStore）
4. `MMKV_CLEANED`（删除该 entry 的 MMKV 读写逻辑）

> 注意：**禁止跨越状态**。每个 entry 都必须经历双读写观察阶段。

## 3.2 兼容策略

- 读取顺序：`DataStore -> MMKV fallback -> 回填 DataStore`
- 写入顺序（过渡期）：`DataStore + MMKV dual-write`
- 稳定后：停掉 MMKV write，再停 MMKV read

## 3.3 风险控制

- 为每个 entry 提供独立开关（建议 Remote Config）：
  - `setting_migration_<entry>_enabled`
  - `setting_migration_<entry>_ds_only`
- 打点监控：
  - fallback 次数
  - DS/MMKV 值不一致次数
  - 关键功能异常率（登录失败、会话列表异常、收藏丢失等）

---

## 4. 建议的数据模型与分层

## 4.1 DataStore 分桶

保持与现有 MMKV 语义一致，避免一次性改变模型：

1. `inty_settings_app`（应用级）
2. `inty_settings_user_<uid>`（用户级）

## 4.2 API 分层（建议）

1. `IntySetting`：暂时保留为 Facade（减小调用点改动）
2. `IntySettingsDataStore`：DataStore 读写实现（新）
3. `IntySettingsMigrationBridge`：负责 fallback、回填、双写和状态开关（新）

这样可以保证“外部调用面稳定 + 内部可逐项替换”。

---

## 5. 每个 entry 的标准迁移流程（One Entry Per Iteration）

每次迭代严格执行以下步骤：

1. **定义 entry 规格**
   - key 名称
   - 类型
   - 默认值
   - 作用域（app/user）
   - 用户切换时是否隔离
2. **先写测试（TDD）**
   - 默认值测试
   - MMKV fallback 测试
   - 回填测试
   - 切账号测试（如果是 user 级）
3. **实现 DataStore key 与读写 API**
4. **接入 Bridge（DS first + MMKV fallback + dual-write）**
5. **仅放开该 entry 的迁移开关**
6. **灰度验证 + 监控（至少 1 个版本周期）**
7. **切换为 DS only**
8. **移除该 entry 的 MMKV 逻辑与遗留 key 清理代码**

---

## 6. 迁移顺序建议（按风险从低到高）

> 规则：每一行是一次独立迁移迭代；每次只做一行。

| 迭代 | Entry | 风险 | 备注 |
|---|---|---|---|
| 01 | `chat_font_size_sp` | 低 | 单值、默认值明确 |
| 02 | `chat_model_id` | 低 | 单值 String |
| 03 | `chat_list_full_screen` | 低 | 单值 Boolean |
| 04 | `auto_play_animation` | 低 | 单值 Boolean |
| 05 | `text_streaming` | 低 | 单值 Boolean |
| 06 | `show_scene_action_button` | 低 | 单值 Boolean |
| 07 | `show_keep_talking` | 低 | 与 Remote Config 有关联，先迁值本身 |
| 08 | `auto_play_audio` | 低 | 与订阅态组合显示，验证 UI 同步 |
| 09 | `user_set_keep_talking` | 中 | 与远端默认值策略联动 |
| 10 | `user_set_auto_play_voice` | 中 | 同上 |
| 11 | `user_set_auto_play_animation` | 中 | 同上 |
| 12 | `user_set_text_streaming` | 中 | 标记型 key |
| 13 | `user_set_scene_action_button` | 中 | 标记型 key |
| 14 | `tips_disabled` | 中 | 影响提示弹窗 |
| 15 | `intellimate_tip_last_show_time` | 中 | 时间戳逻辑，需验证频率控制 |
| 16 | `feedback_dialog_last_show_time` | 中 | 时间戳逻辑 |
| 17 | `show_guest` | 中 | 新手引导展示状态 |
| 18 | `resub_reminder_last_time` | 中 | 订阅提醒节流 |
| 19 | `resub_reminder_show_count` | 中 | 与上一项一起联动验证 |
| 20 | `messages_tab_has_push` | 中 | 首页红点状态 |
| 21 | `conversation_has_push_{agentId}` | 中高 | 动态 key 前缀 |
| 22 | `explore_favorite_{agentId}` | 中高 | 动态 key 前缀，涉及列表展示 |
| 23 | `conversation_pinned_{agentId}` | 中高 | 动态 key，消息排序逻辑依赖 |
| 24 | `conversation_hidden_{agentId}` | 中高 | 动态 key，隐藏逻辑依赖 |
| 25 | `conversation_hidden_time_{agentId}` | 中高 | 与新消息判定联动 |
| 26 | `current_sort_seed` | 中高 | 推荐排序稳定性相关 |
| 27 | `keyboardHeight` | 中 | app 级 UI 偏好 |
| 28 | `vibe_mode_enabled` | 中 | 订阅态联动 |
| 29 | `has_app_update_tips` | 中 | 设置页状态 |
| 30 | `app_data_*` | 高 | 泛化存储，先拆业务再迁移 |
| 31 | `user_profile_*`（泛化） | 高 | 已部分迁出，建议按子业务拆分迁移 |
| 32 | `chat_background_{agentId}` | 高 | 当前依赖轮询读取，建议改为 Flow 后迁移 |
| 33 | `cur_uid` | 高 | 账户切换关键路径 |
| 34 | `token` | 最高 | 认证关键路径，最后迁移 |

---

## 7. 高风险项专项策略

## 7.1 `token` / `cur_uid`

- 必须最后迁移。
- 先引入内存快照（启动时预热）再替换同步读取路径，避免网络拦截器读取时机问题。
- 加入专项监控：
  - 401 峰值
  - 登录后首次请求失败率
  - relaunch 次数

## 7.2 `user_profile_*` 与 `app_data_*`

- 不建议直接“原样搬运”泛化 key-value。
- 先按业务拆分专用 Store（如草稿、缓存、图库、视频缓存路径），再逐项下线旧 key。

## 7.3 动态前缀 key（conversation/explore/chat background）

- 先抽象“前缀索引 + value”读写接口，再逐 key 迁移。
- 保证批量读取能力（例如 `getExploreFavoriteAgentIds()`）有等价实现。

---

## 8. 测试与验收

每个 entry 的 DoD（Definition of Done）：

1. 单元测试通过（默认值、fallback、回填、切账号）。
2. 关键回归场景手测通过（至少：冷启动、登录、登出、切账号、进入对应页面）。
3. 打点可观测（fallback/mismatch/error）。
4. 该 entry 支持独立回滚（开关关闭后恢复 MMKV 读）。
5. 文档更新（迁移状态表 + 测试记录）。

---

## 9. 里程碑建议

- **M1（低风险单值）**：迭代 01~12
- **M2（状态与时间戳）**：迭代 13~20
- **M3（动态 key）**：迭代 21~29
- **M4（高风险核心）**：迭代 30~34

每个里程碑结束后再进入下一里程碑，避免风险叠加。

---

## 10. 本计划对应的首个执行切片（推荐）

第一轮迁移建议从 `chat_font_size_sp` 开始，原因：

1. 低风险、调用点集中（`SettingStateManager`）。
2. 可快速验证 DataStore fallback + 回填机制是否可靠。
3. 不影响登录态、网络鉴权、消息流主链路。

首轮通过后，按第 6 节顺序继续“一次一个 entry”推进。

