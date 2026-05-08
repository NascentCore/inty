# 说明

系统层级约束，是以System Role注入到大模型调用的不同层级的提示词。
每个文件代表了该约束的语义。越底层的约束要出现在最前面的System Message，根据LLM对越先出现的指令响应越准确。
这些约束是大模型用来理解“用户与智能体”这一交互对中，对双方交互模式的整体性理解，并不能完全作为智能体本身的描述。
这也是为何，这些提示词被称为system-hierarchy（而非智能体描述之类的说法）。

1. **AXIOM.md**：[prompts/AXIOM.md](/app/core/agentic_kernel/companion/prompts/AXIOM.md)（非 Workspace 根目录稿）
2. 下列为 [templates](/app/core/agentic_kernel/companion/templates/) 下 Workspace 初始模板，会随着用户与智能体交互更新。
   越靠前的部分更新越慢：
   1. SOUL.md
   2. IDENTITY.md/USER.md
   3. MEMORY.md
