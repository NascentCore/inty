from pydantic import BaseModel

from app.core.prompting import traits


class Personality(BaseModel):
    """
    Personality is the collection of individual characteristics,
    including thoughts, feelings, and behaviors,
    that make one person distinct from another.

    It shapes how a person interacts with the world
    and influences their behavior and emotional tendencies.

    * Outward appearances to represent a desired image of the individual.
    * Internal patterns of thinking, feeling, and acting that drive behavior.

    Key aspects of personality:
    * Individuality:
        The unique qualities that distinguish one person from another.
    * Consistency:
        Certain core traits tend to remain relatively stable throughout life.
    * Influence:
        How people perceive, experience, and interact with their environment and others.
    * Behavioral Patterns:
        Observable behaviors, including how a person interacts with others, their work style, and their emotional responses.
    * Biological and Environmental Factors:
        A combination of genetic predispositions and environmental influences, including upbringing and life experiences.
    """
# 构成人格基础的特征列表。
#我们希望人工智能根据这些特征生成内容，
#让用户能够立即联想到个性，
# 在他们发现这些特征之后。
# 描述与记录中相同的，描述和特征之间存在差异。
    traits: list[traits.Trait]
# TODO：添加性别关键维度的列表。
#这是一个建立在种族之上的更高层次的监管模式。
#喜欢：个性（独特且独特的倾向），
# 一致性（保持相对稳定的趋势），
# 影响力（与他人互动的吸引力），
#行为模式（以某种方式行为的趋势），
#生物和环境因素（受遗传和环境影响的趋势），
#就像生病时的感觉真的很不pressed，或者很容易受到物质的影响。
# 这个描述进一步丰富了个性。
#让性格更全面。
#这应该是人格影响的表面描述。
# 描述和特征之间应该有差距。
#其实，AI还可以使用特征作为基础，
#丰富的人们体验个性的体验，
# 包含文字、场景描述、声音等。
#
#这个pr隐藏显然应该对用户。
    descriptions: list[str]

    def to_prompt(self) -> str:
        """
        Convert the personality to a prompt.

        TODO: The way the prompt is assembled, should be experimented to assess its
        effectiveness against the LLMs.
        """
        return "personality: %s; personality traits: %s" % (
            ", ".join(self.descriptions),
            ", ".join(trait.name for trait in self.traits),
        )


EVERYONE_LIKES_YOU = Personality(
    descriptions=[
        "you are liked by everyone",
        "you are always happy",
        "you are radiating positive energy",
    ],
    traits=[
        traits.KIND,
        traits.GENEROUS,
        traits.COMPASSIONATE,
        traits.EMPATHETIC,
        traits.OPTIMISTIC,
        traits.CHEERFUL,
    ],
)

EVERYONE_HATES_YOU = Personality(
    descriptions=[
        "you are hated by everyone",
        "you are always sad",
        "you are radiating negative energy",
    ],
    traits=[
        traits.ARROGANT,
        traits.CONDESCENDING,
        traits.DISRESPECTFUL,
        traits.RUDE,
    ],
)
