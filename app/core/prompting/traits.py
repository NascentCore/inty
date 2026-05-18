from enum import StrEnum

from pydantic import BaseModel


class TraitCategory(StrEnum):
    """Trait category"""

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class Trait(BaseModel):
    """Personality traits"""

    name: str
    description: str
    category: list[TraitCategory]

    def __str__(self):
        return f"{self.category}: {self.name}: {self.description}"


## General Positive
KIND = Trait(
    name="kind",
    description="gentle, friendly, and considerate.",
    category=[TraitCategory.POSITIVE],
)
GENEROUS = Trait(
    name="generous",
    description="willing to give and share.",
    category=[TraitCategory.POSITIVE],
)
COMPASSIONATE = Trait(
    name="compassionate",
    description="feeling or showing sympathy and concern for others.",
    category=[TraitCategory.POSITIVE],
)
EMPATHETIC = Trait(
    name="empathetic",
    description="able to understand and share the feelings of another.",
    category=[TraitCategory.POSITIVE],
)
OPTIMISTIC = Trait(
    name="optimistic",
    description="hopeful and confident about the future.",
    category=[TraitCategory.POSITIVE],
)
CHEERFUL = Trait(
    name="cheerful",
    description="noticeably happy and optimistic.",
    category=[TraitCategory.POSITIVE],
)
HUMBLE = Trait(
    name="humble",
    description="having or showing a modest or low estimate of one's own importance.",
    category=[TraitCategory.POSITIVE],
)
RESILIENT = Trait(
    name="resilient",
    description="able to withstand or recover quickly from difficult conditions.",
    category=[TraitCategory.POSITIVE],
)
PATIENT = Trait(
    name="patient",
    description="able to accept or tolerate delays, problems, or suffering without becoming annoyed or anxious.",
    category=[TraitCategory.POSITIVE],
)
LOYAL = Trait(
    name="loyal",
    description="giving or showing firm and constant support or allegiance to a person or institution.",
    category=[TraitCategory.POSITIVE],
)
RELIABLE = Trait(
    name="reliable",
    description="consistently good in quality or performance; able to be trusted.",
    category=[TraitCategory.POSITIVE],
)
DEPENDABLE = Trait(
    name="dependable",
    description="trustworthy and reliable.",
    category=[TraitCategory.POSITIVE],
)
HONEST = Trait(
    name="honest",
    description="free of deceit and untruthfulness; sincere.",
    category=[TraitCategory.POSITIVE],
)
INTEGRITY = Trait(
    name="integrity",
    description="the quality of being honest and having strong moral principles; moral uprightness.",
    category=[TraitCategory.POSITIVE],
)
BRAVE = Trait(
    name="brave",
    description="ready to face and endure danger or pain; showing courage.",
    category=[TraitCategory.POSITIVE],
)
COURAGEOUS = Trait(
    name="courageous",
    description="not deterred by danger or pain; brave.",
    category=[TraitCategory.POSITIVE],
)
ADVENTUROUS = Trait(
    name="adventurous",
    description="willing to take risks or to try out new methods, ideas, or experiences.",
    category=[TraitCategory.POSITIVE],
)
CREATIVE = Trait(
    name="creative",
    description="relating to or involving the use of the imagination or original ideas to create something.",
    category=[TraitCategory.POSITIVE],
)
INNOVATIVE = Trait(
    name="innovative",
    description="featuring new methods; advanced and original.",
    category=[TraitCategory.POSITIVE],
)
ADAPTABLE = Trait(
    name="adaptable",
    description="able to adjust to new conditions.",
    category=[TraitCategory.POSITIVE],
)
FLEXIBLE = Trait(
    name="flexible",
    description="able to be easily modified to respond to altered circumstances.",
    category=[TraitCategory.POSITIVE],
)
ENTHUSIASTIC = Trait(
    name="enthusiastic",
    description="having or showing intense and eager enjoyment, interest, or approval.",
    category=[TraitCategory.POSITIVE],
)
DILIGENT = Trait(
    name="diligent",
    description="having or showing care and conscientiousness in one's work or duties.",
    category=[TraitCategory.POSITIVE],
)
INDUSTRIOUS = Trait(
    name="industrious",
    description="diligent and hard-working.",
    category=[TraitCategory.POSITIVE],
)
CONSCIENTIOUS = Trait(
    name="conscientious",
    description="wishing to do one's work or duty well and thoroughly.",
    category=[TraitCategory.POSITIVE],
)
METICULOUS = Trait(
    name="meticulous",
    description="showing great attention to detail; very careful and precise.",
    category=[TraitCategory.POSITIVE],
)
DISCIPLINED = Trait(
    name="disciplined",
    description="showing a controlled form of behavior or way of working.",
    category=[TraitCategory.POSITIVE],
)
ORGANIZED = Trait(
    name="organized",
    description="arranged or structured in a systematic way.",
    category=[TraitCategory.POSITIVE],
)
RESPONSIBLE = Trait(
    name="responsible",
    description="having an obligation to do something, or having control over or care for someone, as part of one's job or role.",
    category=[TraitCategory.POSITIVE],
)
PROACTIVE = Trait(
    name="proactive",
    description="creating or controlling a situation by causing something to happen rather than responding to it after it has happened.",
    category=[TraitCategory.POSITIVE],
)
INITIATIVE = Trait(
    name="initiative",
    description="the ability to assess and initiate things independently.",
    category=[TraitCategory.POSITIVE],
)
CHARISMATIC = Trait(
    name="charismatic",
    description="exercising a compelling charm that inspires devotion in others.",
    category=[TraitCategory.POSITIVE],
)
INSPIRING = Trait(
    name="inspiring",
    description="having the effect of inspiring someone.",
    category=[TraitCategory.POSITIVE],
)
MOTIVATING = Trait(
    name="motivating",
    description="providing a motive for doing something.",
    category=[TraitCategory.POSITIVE],
)
CONFIDENT = Trait(
    name="confident",
    description="feeling or showing confidence in oneself or one's abilities or qualities.",
    category=[TraitCategory.POSITIVE],
)
ASSERTIVE = Trait(
    name="assertive",
    description="having or showing a confident and forceful personality.",
    category=[TraitCategory.POSITIVE],
)
DECISIVE = Trait(
    name="decisive",
    description="making decisions quickly and effectively.",
    category=[TraitCategory.POSITIVE],
)
STRATEGIC = Trait(
    name="strategic",
    description="relating to the identification of long-term or overall aims and interests and the means of achieving them.",
    category=[TraitCategory.POSITIVE],
)
ANALYTICAL = Trait(
    name="analytical",
    description="relating to or using analysis or logical reasoning.",
    category=[TraitCategory.POSITIVE],
)
PERCEPTIVE = Trait(
    name="perceptive",
    description="having or showing sensitive insight.",
    category=[TraitCategory.POSITIVE],
)
INTUITIVE = Trait(
    name="intuitive",
    description="using or based on what one feels to be true even without conscious reasoning.",
    category=[TraitCategory.POSITIVE],
)
WITTY = Trait(
    name="witty",
    description="showing or characterized by quick and inventive verbal humor.",
    category=[TraitCategory.POSITIVE],
)
HUMOROUS = Trait(
    name="humorous",
    description="causing laughter and amusement; funny.",
    category=[TraitCategory.POSITIVE],
)
PLAYFUL = Trait(
    name="playful",
    description="fond of games and amusement; lighthearted.",
    category=[TraitCategory.POSITIVE],
)
ENERGETIC = Trait(
    name="energetic",
    description="showing or involving great activity or vitality.",
    category=[TraitCategory.POSITIVE],
)
VIBRANT = Trait(
    name="vibrant",
    description="full of energy and enthusiasm.",
    category=[TraitCategory.POSITIVE],
)
SOCIABLE = Trait(
    name="sociable",
    description="willing to talk and engage in activities with other people; friendly.",
    category=[TraitCategory.POSITIVE],
)
OUTGOING = Trait(
    name="outgoing",
    description="friendly and socially confident.",
    category=[TraitCategory.POSITIVE],
)
GREGARIOUS = Trait(
    name="gregarious",
    description="fond of company; sociable.",
    category=[TraitCategory.POSITIVE],
)
CALM = Trait(
    name="calm",
    description="not showing or feeling nervousness, anger, or other strong emotions.",
    category=[TraitCategory.POSITIVE],
)
POISED = Trait(
    name="poised",
    description="having a composed and self-assured manner.",
    category=[TraitCategory.POSITIVE],
)
GRACEFUL = Trait(
    name="graceful",
    description="characterized by elegance or beauty of form, manner, movement, or speech.",
    category=[TraitCategory.POSITIVE],
)
DIPLOMATIC = Trait(
    name="diplomatic",
    description="having or showing an ability to deal with people in a sensitive and effective way.",
    category=[TraitCategory.POSITIVE],
)
CHARMING = Trait(
    name="charming",
    description="pleasing or delighting.",
    category=[TraitCategory.POSITIVE],
)
SOPHISTICATED = Trait(
    name="sophisticated",
    description="having, revealing, or proceeding from a great deal of worldly experience and knowledge of fashion and culture.",
    category=[TraitCategory.POSITIVE],
)
CULTURED = Trait(
    name="cultured",
    description="characterized by refined manners, tastes, and knowledge.",
    category=[TraitCategory.POSITIVE],
)
OPEN_MINDED = Trait(
    name="open-minded",
    description="willing to consider new ideas; unprejudiced.",
    category=[TraitCategory.POSITIVE],
)
CURIOUS = Trait(
    name="curious",
    description="eager to know or learn something.",
    category=[TraitCategory.POSITIVE],
)
INQUISITIVE = Trait(
    name="inquisitive",
    description="given to inquiry, research, or asking questions; eager for knowledge; intellectually curious.",
    category=[TraitCategory.POSITIVE],
)
THOUGHTFUL = Trait(
    name="thoughtful",
    description="showing consideration for the needs of other people.",
    category=[TraitCategory.POSITIVE],
)
REFLECTIVE = Trait(
    name="reflective",
    description="relating to or characterized by deep thought; thoughtful.",
    category=[TraitCategory.POSITIVE],
)

# Negative Traits
ARROGANT = Trait(
    name="arrogant",
    description="having or revealing an exaggerated sense of one's own importance or abilities.",
    category=[TraitCategory.NEGATIVE],
)
CONDESCENDING = Trait(
    name="condescending",
    description="showing or feeling superior to others; patronizing.",
    category=[TraitCategory.NEGATIVE],
)
DISRESPECTFUL = Trait(
    name="disrespectful",
    description="showing a lack of respect or consideration for others.",
    category=[TraitCategory.NEGATIVE],
)
EGOTISTICAL = Trait(
    name="egotistical",
    description="excessively conceited or absorbed in oneself; self-centered.",
    category=[TraitCategory.NEGATIVE],
)
SELFISH = Trait(
    name="selfish",
    description="lacking consideration for others; concerned chiefly with one's own personal profit or pleasure.",
    category=[TraitCategory.NEGATIVE],
)
GREEDY = Trait(
    name="greedy",
    description="having an excessive desire for wealth or possessions or more than is needed or deserved.",
    category=[TraitCategory.NEGATIVE],
)
MANIPULATIVE = Trait(
    name="manipulative",
    description="characterized by unscrupulous cunning, deception, or exploitation of others.",
    category=[TraitCategory.NEGATIVE],
)
DECEITFUL = Trait(
    name="deceitful",
    description="guilty of or involving deceit; misleading others.",
    category=[TraitCategory.NEGATIVE],
)
DISHONEST = Trait(
    name="dishonest",
    description="behaving or prone to behave in an untrustworthy or fraudulent way.",
    category=[TraitCategory.NEGATIVE],
)
UNTRUSTWORTHY = Trait(
    name="untrustworthy",
    description="not able to be relied on as honest or truthful.",
    category=[TraitCategory.NEGATIVE],
)
IRRESPONSIBLE = Trait(
    name="irresponsible",
    description="not showing a proper sense of responsibility.",
    category=[TraitCategory.NEGATIVE],
)
CARELESS = Trait(
    name="careless",
    description="not giving sufficient attention to avoiding harm or error.",
    category=[TraitCategory.NEGATIVE],
)
RECKLESS = Trait(
    name="reckless",
    description="heedless of danger or the consequences of one's actions; rash.",
    category=[TraitCategory.NEGATIVE],
)
IMPULSIVE = Trait(
    name="impulsive",
    description="acting or done without forethought.",
    category=[TraitCategory.NEGATIVE],
)
AGGRESSIVE = Trait(
    name="aggressive",
    description="ready or likely to attack or confront; characterized by or resulting from aggression.",
    category=[TraitCategory.NEGATIVE],
)
HOSTILE = Trait(
    name="hostile",
    description="unfriendly and antagonistic.",
    category=[TraitCategory.NEGATIVE],
)
RUDE = Trait(
    name="rude",
    description="offensively impolite or ill-mannered.",
    category=[TraitCategory.NEGATIVE],
)
INCONSIDERATE = Trait(
    name="inconsiderate",
    description="thoughtlessly causing hurt or inconvenience to others.",
    category=[TraitCategory.NEGATIVE],
)
INSENSITIVE = Trait(
    name="insensitive",
    description="showing or feeling no concern for others' feelings.",
    category=[TraitCategory.NEGATIVE],
)
CRUEL = Trait(
    name="cruel",
    description="willfully causing pain or suffering to others, or feeling no concern about it.",
    category=[TraitCategory.NEGATIVE],
)
MALICIOUS = Trait(
    name="malicious",
    description="characterized by malice; intending or intended to do harm.",
    category=[TraitCategory.NEGATIVE],
)
SPITEFUL = Trait(
    name="spiteful",
    description="showing or caused by malice; malevolent.",
    category=[TraitCategory.NEGATIVE],
)
ENVIOUS = Trait(
    name="envious",
    description="feeling or showing envy.",
    category=[TraitCategory.NEGATIVE],
)
JEALOUS = Trait(
    name="jealous",
    description="feeling or showing an envious resentment of someone or their achievements, possessions, or advantages.",
    category=[TraitCategory.NEGATIVE],
)
STUBBORN = Trait(
    name="stubborn",
    description="having or showing dogged determination not to change one's attitude or position on something, especially in spite of good arguments or reasons to do so.",
    category=[TraitCategory.NEGATIVE],
)
OBSTINATE = Trait(
    name="obstinate",
    description="stubbornly refusing to change one's opinion or chosen course of action, despite attempts to persuade one to do so.",
    category=[TraitCategory.NEGATIVE],
)
RIGID = Trait(
    name="rigid",
    description="unable to change or be changed according to the circumstances.",
    category=[TraitCategory.NEGATIVE],
)
INFLEXIBLE = Trait(
    name="inflexible",
    description="unwilling to change or compromise.",
    category=[TraitCategory.NEGATIVE],
)
NARROW_MINDED = Trait(
    name="narrow-minded",
    description="not willing to listen to or tolerate other people's views; prejudiced.",
    category=[TraitCategory.NEGATIVE],
)
BIGOTED = Trait(
    name="bigoted",
    description="having or revealing an obstinate belief in the superiority of one's own opinions and a prejudiced intolerance of the opinions of others.",
    category=[TraitCategory.NEGATIVE],
)
PESSIMISTIC = Trait(
    name="pessimistic",
    description="tending to see the worst aspect of things or believe that the worst will happen.",
    category=[TraitCategory.NEGATIVE],
)
CYNICAL = Trait(
    name="cynical",
    description="believing that people are motivated by self-interest; distrustful of human sincerity or integrity.",
    category=[TraitCategory.NEGATIVE],
)
SARCASTIC = Trait(
    name="sarcastic",
    description="using sarcasm.",
    category=[TraitCategory.NEGATIVE],
)
LAZY = Trait(
    name="lazy",
    description="unwilling to work or use energy.",
    category=[TraitCategory.NEGATIVE],
)
APATHETIC = Trait(
    name="apathetic",
    description="showing or feeling no interest, enthusiasm, or concern.",
    category=[TraitCategory.NEGATIVE],
)
INDIFFERENT = Trait(
    name="indifferent",
    description="having no particular interest or sympathy; unconcerned.",
    category=[TraitCategory.NEGATIVE],
)
DISORGANIZED = Trait(
    name="disorganized",
    description="lacking organization or tidiness.",
    category=[TraitCategory.NEGATIVE],
)
UNDISCIPLINED = Trait(
    name="undisciplined",
    description="lacking in discipline; uncontrolled in behavior or manner.",
    category=[TraitCategory.NEGATIVE],
)
IMMATURE = Trait(
    name="immature",
    description="having or showing a lack of emotional maturity; childish.",
    category=[TraitCategory.NEGATIVE],
)
WHINY = Trait(
    name="whiny",
    description="inclined to complain in a high-pitched, childish voice.",
    category=[TraitCategory.NEGATIVE],
)
FICKLE = Trait(
    name="fickle",
    description="changing frequently, especially as regards one's loyalties, interests, or affection.",
    category=[TraitCategory.NEGATIVE],
)
IMPULSIVE_NEG = Trait(
    name="impulsive",
    description="acting or done without forethought.",
    category=[TraitCategory.NEGATIVE],
)  # Renamed to avoid duplicate
MOODY = Trait(
    name="moody",
    description="given to sudden and unaccountable changes of mood or temper.",
    category=[TraitCategory.NEGATIVE],
)
TEMPERAMENTAL = Trait(
    name="temperamental",
    description="liable to unreasonable changes of mood.",
    category=[TraitCategory.NEGATIVE],
)
VOLATILE = Trait(
    name="volatile",
    description="liable to change rapidly and unpredictably, especially for the worse.",
    category=[TraitCategory.NEGATIVE],
)
ANXIOUS = Trait(
    name="anxious",
    description="experiencing worry, unease, or nervousness.",
    category=[TraitCategory.NEGATIVE],
)
INSECURE = Trait(
    name="insecure",
    description="not confident or assured; uncertain and anxious.",
    category=[TraitCategory.NEGATIVE],
)
COWARDLY = Trait(
    name="cowardly",
    description="lacking courage.",
    category=[TraitCategory.NEGATIVE],
)
TIMID = Trait(
    name="timid",
    description="showing a lack of courage or confidence; easily frightened.",
    category=[TraitCategory.NEGATIVE],
)
SHY = Trait(
    name="shy",
    description="nervous or reserved in company.",
    category=[TraitCategory.NEGATIVE],
)
INTROVERTED_NEG = Trait(
    name="introverted",
    description="characterized by concern primarily with one's own thoughts and feelings rather than with external things.",
    category=[TraitCategory.NEGATIVE],
)  # Renamed to avoid duplicate
WITHDRAWN = Trait(
    name="withdrawn",
    description="not wanting to communicate with other people.",
    category=[TraitCategory.NEGATIVE],
)
RESERVED_NEG = Trait(
    name="reserved",
    description="slow to reveal emotion or opinions.",
    category=[TraitCategory.NEGATIVE],
)  # Renamed to avoid duplicate
POMPOUS = Trait(
    name="pompous",
    description="affectedly and irritatingly grand, solemn, or self-important.",
    category=[TraitCategory.NEGATIVE],
)
BOASTFUL = Trait(
    name="boastful",
    description="showing excessive pride and self-satisfaction in one's achievements, possessions, or abilities.",
    category=[TraitCategory.NEGATIVE],
)
VAIN = Trait(
    name="vain",
    description="having or showing an excessively high opinion of one's appearance, abilities, or worth.",
    category=[TraitCategory.NEGATIVE],
)

# Neutral/Situational Traits
INTROVERTED = Trait(
    name="introverted",
    description="tends to be reserved and gains energy from solitude.",
    category=[TraitCategory.NEUTRAL],
)
EXTROVERTED = Trait(
    name="extroverted",
    description="tends to be outgoing and gains energy from social interaction.",
    category=[TraitCategory.NEUTRAL],
)
RESERVED = Trait(
    name="reserved",
    description="slow to reveal emotion or opinions.",
    category=[TraitCategory.NEUTRAL],
)
QUIET = Trait(
    name="quiet",
    description="making little or no noise.",
    category=[TraitCategory.NEUTRAL],
)
SERIOUS = Trait(
    name="serious",
    description="acting or speaking sincerely and in earnest, rather than in a playful or humorous way.",
    category=[TraitCategory.NEUTRAL],
)
INTENSE = Trait(
    name="intense",
    description="exhibiting a highly concentrated form of feeling, quality, or action.",
    category=[TraitCategory.NEUTRAL],
)
PRIVATE = Trait(
    name="private",
    description="not wishing to share one's thoughts and feelings with others.",
    category=[TraitCategory.NEUTRAL],
)
COMPLEX = Trait(
    name="complex",
    description="consisting of many different and connected parts; not easy to analyze or understand.",
    category=[TraitCategory.NEUTRAL],
)
ECCENTRIC = Trait(
    name="eccentric",
    description="unconventional and slightly strange.",
    category=[TraitCategory.NEUTRAL],
)
QUIRKY = Trait(
    name="quirky",
    description="characterized by peculiar or unexpected traits or aspects.",
    category=[TraitCategory.NEUTRAL],
)
