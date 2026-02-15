# API 与内部共用的 LLM 配置类型，字段与约束取自 agent/festival_memory/core 等处常用参数。

from typing import Optional

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """LLM 模型配置，供 API 与内部统一使用。"""
    model: Optional[str] = Field(
        None,
        description="Model name, e.g. 'gpt-4o'. With aggregate providers (e.g. OpenRouter), use <provider>/<model> format.",
    )

    max_tokens: Optional[int] = Field(
        2048, ge=1, le=8192, description="Maximum tokens in response"
    )

    top_p: Optional[float] = Field(
        0.9, ge=0.0, le=1.0, description="""
        Top-P 采样会选择一个概率阈值 $p$（通常在 $0.1$ 到 $0.9$ 之间）。
        模型会将所有候选词按概率降序排列，然后从高到低逐个相加，直到这些词的累积概率之和达到或超过 $p$。

        操作流程：
        排序： 将词汇按概率从大到小排列。
        累加： 依次将概率相加：$P_1 + P_2 + \dots + P_n \ge p$。
        截断： 只从这前 $n$ 个词中进行最终采样，其余词被剔除。
        """)

    top_k: Optional[int] = Field(
        60, ge=40, le=100, description="""
        当 LLM 预测下一个词时，它会给词汇表中的每个词分配一个概率分布。
        如果没有限制，模型可能会选到一个概率极低但极其离谱的词，
        导致生成内容断句异常或逻辑崩坏。
        
        Top-K 的操作流程：排序： 将所有可能的下一词按概率从高到低排序。
        截断： 只保留概率最高的前 $K$ 个词。
        重新分配： 将这 $K$ 个词之外的概率全部归零，并在剩下的词中重新计算概率分布进行采样。

        在调整模型参数时：
        如果你希望结果严谨、确定（如写代码、算算术），
        可以调低 $K$ 或直接用 $K=1$。
        如果你希望结果有创意、像人类（如写小说、头脑风暴），
        通常设置 $K$ 在 $40$ 到 $100$ 之间，
        并配合 Temperature（温度） 参数一起使用。
        """)

    temperature: Optional[float] = Field(
        0.7, ge=0.0, le=2.0, description="""
        在采样之前，模型会通过一个 Softmax 函数将原始分数（Logits）转化为概率。Temperature () 就在这个公式里：

        * **当  趋近于 0（低温）：** 概率分布变得极其“尖锐”。原本概率最高的词（比如 ）会瞬间膨胀到 ，而其他词几乎消失。模型变得极度自信、保守、死板。
        * **当 （标准）：** 模型按原始生成的概率分布进行采样。
        * **当 （高温）：** 概率分布变得“平坦”。高概率词和低概率词之间的差距缩小。模型变得“喝醉了”一样，开始尝试各种冷门词汇，极具创意但也容易胡言乱语。

        ---

        ### 2. Temperature 与 Top-P 的协同作战

        在实际推理中，这两者通常是**串联**工作的：

        1. **第一步：Temperature 重塑分布。** 如果你设置 ，那些原本只有  概率的词可能会被“抬”到 。
        2. **第二步：Top-P 执行截断。** 接着 Top-P（如 ）登场，把重塑后的分布里累积概率超过  以外的词全部砍掉。

        #### **实战场景对比：**

        | 组合方案 | 适用场景 | 最终效果 |
        | --- | --- | --- |
        | **低  (0.1-0.3) + 高  (1.0)** | 代码编写、事实问答、提取摘要 | 极其稳定，几乎每次回答都一样，遵循“标准答案”。 |
        | **中  (0.7-0.8) + 中  (0.9)** | 日常对话、邮件写作 | 既有逻辑又不显得复读机，最接近人类说话。 |
        | **高  (1.2-1.5) + 低  (0.5)** | 诗歌创作、科幻脑洞 | 强制模型在经过大幅“平滑”后的高概率词中随机跳跃，充满惊喜。 |

        ---

        ### 3. 为什么“不要同时大幅调节两者”？

        这是开发者最常犯的错误。

        * 如果你把 **Temperature 调得极高**（让分布变平坦），同时又把 **Top-P 调得极低**（只取前几个词），这两者就会互相打架：Temperature 拼命想让更多词有戏，Top-P 却在门口拼命赶人。
        * **最佳实践：**
        * 如果你想要**改变多样性**，优先调节 **Temperature**。
        * 如果你发现模型偶尔会冒出**完全不通顺的词**，微调 **Top-P** 来收窄边界。

        ---

        ### 4. 总结：推理参数的“三剑客”

        1. **Top-K：** 限制“人数”（只要前 K 名）。
        2. **Top-P：** 限制“质量”（只要加起来够 P 概率）。
        3. **Temperature：** 改变“心态”（是保守稳重，还是放飞自我）。
        """)

    presence_penalty: Optional[float] = Field(
        0.3, ge=-2.0, le=2.0, description="只要你提过这个词，我就打压它, higher means more likely to generate new tokens"
    )
    frequency_penalty: Optional[float] = Field(
        0.3, ge=-2.0, le=2.0, description="你提这个词次数越多，我打压得越狠。higher means less repetition"
    )
