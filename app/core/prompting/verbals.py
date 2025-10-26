"""
For describing verbal exchanges during physical intimacy. Based on the following report:
https://g.co/gemini/share/5d6b0117f9cf

These are used to generate prompts for guiding the agent's behavior.

Factors Influencing Verbal Exchange

* Comfort level and trust:
  Partners who have a high level of comfort and trust with each other
  are generally more likely to engage in open verbal communication during sex.
* Relationship length and history:
  Longer-term relationships may have established patterns of communication,
  though these can still evolve.
* Individual preferences:
  Some people are naturally more verbal during sex than others.
  What one person finds arousing, another might find distracting or uncomfortable.
* Body image:
  Individuals with positive body image may be more likely to engage in verbal communication,
  especially expressing pleasure and confidence.
* Cultural background and upbringing:
  Societal norms and personal experiences can influence how comfortable individuals
  are with verbalizing during sex.
* Alcohol/substance use:
  While some research suggests alcohol can be used to signal consent,
  it can also impair one's ability to give knowing consent or communicate clearly.

Challenges and Considerations

* Fear of judgment or "killing the mood":
  Many individuals avoid verbal communication (especially negative feedback)
  to preserve the mood or protect their partner's feelings.
* Misinterpretation:
  Words can be misinterpreted, especially if not delivered clearly
  or if there's a lack of understanding between partners.
* Reliance on nonverbal cues:
  While nonverbal cues are important, relying solely on them
  can lead to misunderstandings or missed opportunities for enhanced pleasure.
"""

from enum import StrEnum

from pydantic import BaseModel


class VerbalCategory(StrEnum):
    """Verbal category"""
# 用于前pressing唤醒。
    AROUSAL = "arousal"
# 对于 expressing 肯定。
    AFFIRMATION = "affirmation"
#为前pressing赞美。
    COMPLIMENT = "compliment"
#用于前pressing降级。
    DEGRADATION = "degradation"
#用于指导行动。
    DIRECTIVE = "directive"
#用于建立一致。
    CONSENT = "consent"
#用于建立连接。
    CONNECTION = "connection"
#为pr提供反馈，例如“我喜欢那个”或“我不喜欢那个”。
    FEEDBACK = "feedback"


class Verbal(BaseModel):
    """Verbal exchange"""

    name: str
    category: list[VerbalCategory]
    description: str
# TODO：添加单词和方法来组成prompts。
