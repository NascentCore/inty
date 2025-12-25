# Inty.is 属性类型支持
_Exported on 12/23/2025 at 11:27:49 PST from Cursor (2.2.43)_

---

**User**

https://github.com/NascentCore/inty/issues/1294  是否已经处理

---

**Cursor**


检查 issue #1294 的状态。



Issue 仍为 open。检查相关代码，确认是否已处理。



查看最新的 migration 文件，确认是否已处理：



检查 agents 表的 unique constraint 是否已删除：



检查是否还有其他 migration 删除了 agents 表的 unique constraint：



检查 `20250805_041613_43b18ddc9846_system_settings_and_voice_cache_tables.py` 中是否删除了 unique constraint：



检查 alembic 的当前 head revision，确认最新 migration 状态：



查找最新的 migration 文件：



检查 agents 模型是否需要添加废弃注释：



## 处理状态总结

### Users 表 — 已完成
- 已去除 NOT NULL（`nullable=True`）
- 已去除 UNIQUE（已删除 unique constraint 和 unique index）
- 已删除索引
- 已标记为废弃（模型中有 `DEPRECATED` 注释和 `【已废弃】用户可读ID` comment）

相关 migration: `20251130_204229_ac1a943ddb73_users_readable_id_删除_unique_nullable_.py`

### Agents 表 — 基本完成
- 已去除 NOT NULL（`nullable=True`）
- 已去除 UNIQUE（已删除 unique index）
- 已删除索引
- 已标记为废弃（模型中有 `DEPRECATED` 注释，但 Column 定义中缺少废弃的 comment）

相关 migration: `20251113_065347_4a90b1f01430_remove_readable_id_constraints.py`

## 建议

Agents 表的 `readable_id` 字段已有 `DEPRECATED` 注释，但 Column 定义中缺少废弃的 comment。为保持一致性，建议在 `app/models/agent.py` 中添加 comment，与 users 表保持一致：

```python
readable_id = Column(String(8), comment="【已废弃】角色可读ID")
```

**结论**：Issue #1294 基本已处理，但 agents 表的 Column 定义中缺少废弃的 comment。需要我添加这个 comment 吗？

```python
readable_id = Column(String(8), comment="【已废弃】角色可读ID")
```

---

**User**

是的

---

**Cursor**


为 agents 表的 `readable_id` 字段添加废弃注释，与 users 表保持一致。



为 agents 表的 `readable_id` 字段添加废弃注释：


```python
from enum import StrEnum

import sqlalchemy as sa
from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.models import Base
from app.models.associations import agent_followers
from app.models.user import Gender


class AgentStatus(StrEnum):
    """AI角色状态"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class AgentVisibility(StrEnum):
    """AI 角色可见性"""

    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"


class Agent(Base):
    """AI 角色，Agent 的提法是早期的用词，改动比较麻烦，就沿用了。"""

    __tablename__ = "agents"

    id = Column(String, primary_key=True, index=True)
    # DEPRECATED: app 显示 ID 而非 readable_id
    readable_id = Column(String(8), comment="【已废弃】角色可读ID")
    name = Column(String(30), index=True, nullable=False)
    gender = Column(Enum(Gender, name="gender"), nullable=False)
    avatar = Column(String)
    background = Column(String)
    background_images = Column(JSON)  # 存储背景图列表
    background_animated = Column(String, nullable=True)  # 存储 webp 动图 URL
    voice_id = Column(String)
    settings = Column(JSON)
    intro = Column(String)
    opening = Column(String)
    visibility = Column(
        Enum(AgentVisibility, name="visibility"), default=AgentVisibility.PUBLIC
    )
    photos = Column(JSON)
    category = Column(String)
    status = Column(Enum(AgentStatus, name="agentstatus"), default=AgentStatus.PENDING)
    created_at = Column(DateTime(timezone=True), server_default=sa.text("now()"))
    updated_at = Column(DateTime(timezone=True), onupdate=sa.text("now()"))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(
        Integer,
        nullable=False,
        default=1,
        server_default=sa.text("1"),
    )
    points = Column(
        Integer,
        default=0,
        server_default=sa.text("0"),
        comment="角色积分，用于角色热度排名（boosting feature）",
    )
    prompt = Column(String)

    # 主提示词和模式提示词字段
    # 如果使用预设提示词，存储 prompt ID（如 "roleplay_main"）
    # 如果自定义，存储完整文本
    main_prompt = Column(
        Text, nullable=True
    )  # 主提示词 - 作为第一个system message，可以是预设 ID 或自定义文本
    mode_prompt = Column(
        Text, nullable=True
    )  # 模式提示词 - 放在角色卡提示词后面，可以是预设 ID 或自定义文本

    # 角色卡相关字段；都已经废弃
    character_card_spec = Column(String, nullable=True)  # 角色卡规范版本
    character_card_data = Column(JSON, nullable=True)  # 原始角色卡数据
    personality = Column(Text, nullable=True)  # 性格特征
    scenario = Column(Text, nullable=True)  # 场景设定
    message_example = Column(Text, nullable=True)  # 对话示例
    creator_notes = Column(Text, nullable=True)  # 创建者备注
    post_history_instructions = Column(Text, nullable=True)  # 历史后指令
    alternate_greetings = Column(JSON, nullable=True)  # 替代问候语
    character_book = Column(JSON, nullable=True)  # 角色书
    tags = Column(JSON, nullable=True)  # 标签
    character_version = Column(String, nullable=True)  # 版本号
    extensions = Column(JSON, nullable=True)  # 扩展数据
    meta_data = Column(JSON, nullable=True)  # 灵活的元数据

    # 语音相关字段
    opening_audio_url = Column(String, nullable=True)  # 预生成的开场白语音URL

    # 外键
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)

    # 关系
    creator = relationship("User", back_populates="agents")
    followers = relationship(
        "User", secondary=agent_followers, back_populates="following_agents"
    )
    messages = relationship("Message", back_populates="agent")
    chat_settings = relationship("ChatSettings", back_populates="agent")
    chats = relationship("Chat", back_populates="agent")
    resources = relationship("Resource", back_populates="agent")

    # 乐观锁配置：使用 version 字段防止并发更新冲突
    # 更新时会自动检查版本号，不匹配则抛出 StaleDataError，成功更新后自动递增 version
    __mapper_args__ = {
        "version_id_col": version,
    }

```


检查是否有 lint 错误：



已为 agents 表的 `readable_id` 字段添加废弃注释。

## 完成的工作

1. 在 `app/models/agent.py` 中为 `readable_id` 字段添加了 `comment="【已废弃】角色可读ID"`，与 users 表保持一致。

现在两个表的 `readable_id` 字段都已：
- 去除 NOT NULL 约束
- 去除 UNIQUE 约束
- 删除索引
- 标记为废弃（包含 DEPRECATED 注释和废弃 comment）

**Issue #1294 已处理完成**。可以关闭该 issue。需要我帮你关闭吗？

---

**User**

关闭

---

**Cursor**


关闭 issue #1294。



已关闭 issue #1294。

已完成：
- 为 agents 表的 `readable_id` 字段添加废弃注释
- 关闭 GitHub issue

两个表的 `readable_id` 字段已去除附加属性（NOT NULL、UNIQUE、索引），并标记为已废弃。

