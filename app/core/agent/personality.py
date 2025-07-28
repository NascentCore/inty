from pydantic import BaseModel

from app.core.agent import trait
from app.core.agent.trait import Trait


class Personality(BaseModel):
    """A collection of traits"""

    traits: list[Trait]

    def to_prompt(self) -> str:
        """Convert the personality to a prompt"""
        return "personality: " + ", ".join(trait.name for trait in self.traits)


EVERYONE_LIKES_YOU = Personality(
    traits=[
        trait.KIND,
        trait.GENEROUS,
        trait.COMPASSIONATE,
        trait.EMPATHETIC,
        trait.OPTIMISTIC,
        trait.CHEERFUL,
    ]
)
