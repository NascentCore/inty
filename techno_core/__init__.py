"""TechnoCore：Inty 在架构上的「虚拟居留层」命名与设计归宿。

本包位于仓库根目录，与运行时主体 ``app.core.agentic_kernel`` 解耦：此处存放
概念边界、球层词汇（见 ``techno_core.spheres``）及人机可读的设计说明
（``techno_core/AGENTS.md``）。自主节拍、后台工具链与世界事件的**实现**仍在
内核模块中；未来若将「独立于用户的虚拟环境」拆成清晰子系统，应优先把编排与
类型收敛到本包或其子模块，以避免 companion 目录无限膨胀。

Hyperion 小说中的 TechnoCore 等仅为隐喻与分层灵感，不构成产品叙事或 canon。
"""
