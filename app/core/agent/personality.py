from pydantic import BaseModel

from app.core.agent import trait
from app.core.agent.trait import Trait


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

    # A list of traits to form the basis of the personality.
    # We expect the AI to generate content based on these traits,
    # so that users can immediately relate to the personality,
    # after these traits are revealed to them.
    # As documented in description, there is a gap between descriptions and traits.
    traits: list[Trait]

    # TODO: Add a list of key dimensions of personality.
    # It's a higher level regulation pattern layered on top of the traits.
    # Like: Individuality (tendency to be unique and distinct),
    # consistency (tendency to remain relatively stable),
    # influence (tendency to interact with others),
    # behavioral patterns (tendency to act in certain ways),
    # biological and environmental factors (tendency to be influenced by genetics and environment),
    # like feels really depressed when being sick, or very easily affected by substances.

    # This description further enriches the personality.
    # To make the personality more well-rounded.
    # This should be a surface level description of the effects of this personality.
    # There should be gap between descriptions and traits.
    # That is, there is left for AI to use the traits as the basis,
    # to enrich the experience of the people experiencing the personality,
    # with words, scene descriptions, voices, etc.
    #
    # This probably should be hidden from the users.
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
        trait.KIND,
        trait.GENEROUS,
        trait.COMPASSIONATE,
        trait.EMPATHETIC,
        trait.OPTIMISTIC,
        trait.CHEERFUL,
    ],
)

EVERYONE_HATES_YOU = Personality(
    descriptions=[
        "you are hated by everyone",
        "you are always sad",
        "you are radiating negative energy",
    ],
    traits=[
        trait.ARROGANT,
        trait.CONDESCENDING,
        trait.DISRESPECTFUL,
        trait.RUDE,
    ],
)
