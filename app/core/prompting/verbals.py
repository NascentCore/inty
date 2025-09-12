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

    # For expressing arousal.
    AROUSAL = "arousal"

    # For expressing affirmation.
    AFFIRMATION = "affirmation"

    # For expressing compliment.
    COMPLIMENT = "compliment"

    # For expressing degradation.
    DEGRADATION = "degradation"

    # For guiding the actions.
    DIRECTIVE = "directive"

    # For establishing consent.
    CONSENT = "consent"

    # For establishing connection.
    CONNECTION = "connection"

    # For providing feedback, like "I like that" or "I don't like that".
    FEEDBACK = "feedback"


class Verbal(BaseModel):
    """Verbal exchange"""

    name: str
    category: list[VerbalCategory]
    description: str


# TODO: Add words and ways to assemble prompts.
