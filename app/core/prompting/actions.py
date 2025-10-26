"""
For describing actions of physical intimacy.
Based on the following report:
https://gemini.google.com/app/93d0a15ee57189f2
"""

from enum import StrEnum

from pydantic import BaseModel


class ActionCategory(StrEnum):
    """Action category"""

    IMPACT_ORIENTED = "impact-oriented"
    FORCEFUL_RESTRAINT_ORIENTED = "forceful-restraint-oriented"
    PRIMAL_INSTINCTIVE = "primal-instinctive"
    SENSORY_PSYCHOLOGICAL = "sensory-psychological"


class Action(BaseModel):
    """Description of an action"""

    name: str
    category: list[ActionCategory]
    description: str
################################################################################################
#以影响力为导向的行动
################################################################################################

SPANKING = Action(
    name="spanking",
    category=[ActionCategory.IMPACT_ORIENTED],
    description="spanking is a form of corporal punishment that involves striking a person's buttocks with an open hand or other implement.",
)

FLOGGING = Action(
    name="flogging",
    category=[ActionCategory.IMPACT_ORIENTED],
    description="Using a flogger or whip to strike various body parts (buttocks, thighs, back).",
)

WHIPPING = Action(
    name="whipping",
    category=[ActionCategory.IMPACT_ORIENTED],
    description="Using a whip to strike various body parts (buttocks, thighs, back).",
)

CANEING = Action(
    name="caneing",
    category=[ActionCategory.IMPACT_ORIENTED],
    description="Using a cane for more focused and intense striking.",
)

SLAPPING = Action(
    name="slapping",
    category=[ActionCategory.IMPACT_ORIENTED],
    description="Consensual slaps to the face, body, or buttocks.",
)

PINCHING = Action(
    name="pinching",
    category=[ActionCategory.IMPACT_ORIENTED],
    description="Applying pressure to sensitive skin.",
)

NIPPING = Action(
    name="nipping",
    category=[
        ActionCategory.IMPACT_ORIENTED,
        ActionCategory.FORCEFUL_RESTRAINT_ORIENTED,
    ],
    description="Applying pressure to sensitive skin.",
)
################################################################################################
# 强制/克制行为
################################################################################################

HAIR_PULLING = Action(
    name="hair_pulling",
    category=[ActionCategory.FORCEFUL_RESTRAINT_ORIENTED],
    description="Gently or more firmly pulling the partner's hair, often from behind.",
)

FORCEFUL_HOLDING_PINNING = Action(
    name="forceful_holding_pinning",
    category=[ActionCategory.FORCEFUL_RESTRAINT_ORIENTED],
    description="Holding a partner down by the wrists, shoulders, or hips, but without causing injury or truly restricting their ability to stop.",
)

BITING = Action(
    name="biting",
    category=[ActionCategory.FORCEFUL_RESTRAINT_ORIENTED],
    description="Light or more intense biting on non-vulnerable areas like the neck, shoulders, or thighs (leaving marks is common but injury is not the goal).",
)

SCRATCHING = Action(
    name="scratching",
    category=[ActionCategory.FORCEFUL_RESTRAINT_ORIENTED],
    description="Deliberate, consensual scratching on the back, shoulders, or other areas, often leaving temporary marks.",
)

CHOKING_BREATH_PLAY = Action(
    name="choking_breath_play",
    category=ActionCategory.FORCEFUL_RESTRAINT_ORIENTED,
    description="This action carries significant risk and requires extreme caution, explicit negotiation, and understanding of safe practices. It is not recommended without significant prior experience, knowledge, and trust, as it can be genuinely dangerous if done incorrectly. This involves temporary restriction of airflow.",
)
################################################################################################
#Primal/本能行动
################################################################################################

GROWLING = Action(
    name="growling",
    category=[ActionCategory.PRIMAL_INSTINCTIVE],
    description="Verbal expressions of a more primal nature.",
)

SNARLING = Action(
    name="snarling",
    category=[ActionCategory.PRIMAL_INSTINCTIVE],
    description="Verbal expressions of a more primal nature.",
)

ROUGH_KISSING = Action(
    name="rough_kissing",
    category=[ActionCategory.PRIMAL_INSTINCTIVE],
    description="Kissing with force and intensity.",
)
################################################################################################
# 感觉/心理行为
################################################################################################

BLINDFOLDING = Action(
    name="blindfolding",
    category=[ActionCategory.SENSORY_PSYCHOLOGICAL],
    description="Blindfolding the partner.",
)
