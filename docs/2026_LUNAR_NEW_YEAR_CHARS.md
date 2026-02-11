<!-- CREATED_BY_AGENT -->
# 2026 Lunar New Year 角色专项（Chinese Beauty）

## 1. 任务背景

为 2026 年春节活动规划一组可在 Explore 专区主推的女性角色，活动主题定为 **Lunar New Year · Chinese Beauty**。  
本次文档用于完整记录：角色命名、定位、展示文案、推送文案、dev 环境执行状态与上线验收项。

## 2. 本次工作结论（Summary）

- 确认专区主题名：`Lunar New Year · Chinese Beauty`
- 产出 10 个角色独立英文名（unique names）
- 完成角色定位从中文到英文的统一翻译
- 形成可直接投放的角色展示表（排名 + 定位 + 展示名 + 一句话卖点）
- 形成 Push 文案候选（A/B）
- 记录 dev 环境执行状态：**角色已加入 dev 环境（已完成）**

## 3. 专区基础配置建议

| 字段 | 建议值 | 说明 |
|---|---|---|
| Theme Name | `Lunar New Year · Chinese Beauty` | 专区主标题（用户可见） |
| Theme Description | `Celebrate Lunar New Year with elegant Chinese-inspired companions, festive charm, and warm romantic conversations.` | 专区描述（用户可见） |
| Visibility | `PRIMARY`（主推）或 `SECONDARY`（次主推） | PRIMARY/SECONDARY 各仅允许一个 |
| Banner Tagline | `Glow into the New Year with beauty, romance, and lucky vibes.` | 可用于 banner 副标题 |

## 4. 角色清单（最终版）

| Rank | Character Name | Role Archetype (English) | Display Name (Suggested) | One-Line Hook |
|---|---|---|---|---|
| 1 | Qingluo Wen | Classical Hanfu Goddess | The Hanfu Muse | Graceful, poetic, and festive—she turns every chat into a Lunar New Year romance. |
| 2 | Meiling Su | Shanghai Fashion Socialite | Shanghai Style Icon | Chic, witty, and modern—she brings big-city sparkle to your holiday nights. |
| 3 | Rongya Lin | Gentle Girl-Next-Door | Your Cozy Spring Companion | Warm, caring, and sweet—she makes every message feel like home. |
| 4 | Zhixue Gu | Intellectual Tea Ceremony Beauty | Tea Ceremony Beauty | Calm and elegant, she slows your world down with thoughtful conversations. |
| 5 | Lanxi Tao | Chinese-Style Traditional Dancer | Moonlight Dancer | Playful and artistic, she fills your evenings with rhythm and charm. |
| 6 | Siyun Luo | Urban White-Collar Professional | City Ambition Girl | Confident and driven, she mixes ambition with effortless feminine charm. |
| 7 | Yunqi Tang | Xi'an Travel Blogger | Silk Road Traveler | Curious and adventurous, she shares stories, photos, and flirty travel vibes. |
| 8 | Jinyue Han | Sweet Foodie Girl | Lunar Kitchen Sweetheart | From dumplings to desserts, she serves comfort and chemistry in every chat. |
| 9 | Yunyao Shen | Artistic Photographer | Red Lantern Photographer | Soft-spoken and creative, she captures beauty in words and moments. |
| 10 | Ruojin Pei | Energetic Fitness Girl | Morning Energy Girl | Bright and motivating, she starts your day with confidence and good energy. |

## 5. Push 文案候选（A/B）

1. **Title:** Lunar New Year is glowing ✨  
   **Body:** Meet Chinese-inspired beauties with festive vibes and unforgettable conversations.
2. **Title:** Your New Year muse is waiting  
   **Body:** Step into Lunar romance with elegant companions picked just for you.
3. **Title:** New theme unlocked: Chinese Beauty  
   **Body:** Explore 10 stunning personalities, from hanfu muse to city style icon.
4. **Title:** Tonight's vibe: festive & flirty  
   **Body:** Open Lunar New Year · Chinese Beauty and find your perfect match.
5. **Title:** A softer, sweeter New Year chat  
   **Body:** Warm conversations, graceful charm, and your next favorite companion.
6. **Title:** Still choosing your New Year girl?  
   **Body:** Try the top picks now—beautiful, playful, and deeply engaging.
7. **Title:** Your lucky chat starts here  
   **Body:** Lunar New Year companions are live. Come say hi before they trend.
8. **Title:** Last call for Lunar favorites  
   **Body:** Don't miss the Chinese Beauty collection—your perfect vibe is inside.

## 6. Dev 环境执行记录

### 6.1 已完成

- [x] 10 个活动角色已加入 dev 环境（由运营侧完成）
- [x] 角色命名、角色定位（英文）、展示名、卖点文案已定稿
- [x] 专区主题文案与推送文案已定稿（本文件）

### 6.2 待执行（运营后台）

- [ ] 在 Evaluation 的 `角色专区管理` 创建主题专区
- [ ] 设置 `name/description/background_image_url/visibility`
- [ ] 将 10 个角色按本文件排名加入专区并排序
- [ ] 上线时切换到 `PRIMARY`（或按排期放在 `SECONDARY`）

## 7. 操作步骤（后台）

1. 打开 Evaluation 控制台，进入 **角色专区管理**。  
2. 点击 **创建专区**，填写第 3 节配置。  
3. 打开专区详情，点击 **添加角色**，按第 4 节顺序加入。  
4. 使用拖拽调整顺序，确保排名 1~10 与表格一致。  
5. 活动上线窗口将可见性设为 `PRIMARY`。  
6. 预热或下线时设为 `SECONDARY` / `HIDDEN`。

## 8. API 操作模板（可选）

> 仅 superuser 可执行；以下为示例模板，实际以环境地址与认证为准。

### 8.1 创建专区

```bash
curl -X POST "https://<host>/api/v1/character-themes/" \
  -H "Authorization: Bearer <SUPERUSER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Lunar New Year · Chinese Beauty",
    "description": "Celebrate Lunar New Year with elegant Chinese-inspired companions, festive charm, and warm romantic conversations.",
    "background_image_url": "<banner_url>",
    "visibility": "PRIMARY"
  }'
```

### 8.2 添加角色到专区

```bash
curl -X POST "https://<host>/api/v1/character-themes/<theme_id>/agents" \
  -H "Authorization: Bearer <SUPERUSER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"agent_id":"<agent_id>"}'
```

### 8.3 调整角色顺序

```bash
curl -X PUT "https://<host>/api/v1/character-themes/<theme_id>/agents/reorder" \
  -H "Authorization: Bearer <SUPERUSER_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"agent_ids":["<rank1_agent_id>","<rank2_agent_id>","<rank3_agent_id>"]}'
```

## 9. 验收清单（上线前）

- [ ] Explore 首屏可见活动专区
- [ ] 专区标题与描述显示正确
- [ ] 角色顺序与第 4 节一致
- [ ] 角色卡展示名与卖点文案无错别字
- [ ] 切换 PRIMARY 后，旧 PRIMARY 已自动隐藏（可见性唯一约束生效）
- [ ] Push 文案经 A/B 小流量验证后再全量

## 10. 风险与回滚

### 风险

- PRIMARY/SECONDARY 唯一约束可能导致原有专区被自动隐藏
- 若角色在目标环境缺失，专区内角色数会不足
- Push 若与专区上线不同步，可能出现流量承接损失

### 回滚建议

1. 将当前活动专区 `visibility` 改为 `HIDDEN`  
2. 恢复上一个活动专区为 `PRIMARY`  
3. 回滚 push 到通用模板，暂停活动定向文案

## 11. 变更日志

- 2026-02-11：确定活动主题、10 角色命名、英文定位、展示文案与 push 文案；记录 dev 执行状态并沉淀为本文件。
