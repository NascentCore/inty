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
    name="Kind",
    description="Gentle, friendly, and considerate.",
    category=[TraitCategory.POSITIVE],
)
GENEROUS = Trait(
    name="Generous",
    description="Willing to give and share.",
    category=[TraitCategory.POSITIVE],
)
COMPASSIONATE = Trait(
    name="Compassionate",
    description="Feeling or showing sympathy and concern for others.",
    category=[TraitCategory.POSITIVE],
)
EMPATHETIC = Trait(
    name="Empathetic",
    description="Able to understand and share the feelings of another.",
    category=[TraitCategory.POSITIVE],
)
OPTIMISTIC = Trait(
    name="Optimistic",
    description="Hopeful and confident about the future.",
    category=[TraitCategory.POSITIVE],
)
CHEERFUL = Trait(
    name="Cheerful",
    description="Noticeably happy and optimistic.",
    category=[TraitCategory.POSITIVE],
)
HUMBLE = Trait(
    name="Humble",
    description="Having or showing a modest or low estimate of one's own importance.",
    category=[TraitCategory.POSITIVE],
)
RESILIENT = Trait(
    name="Resilient",
    description="Able to withstand or recover quickly from difficult conditions.",
    category=[TraitCategory.POSITIVE],
)
PATIENT = Trait(
    name="Patient",
    description="Able to accept or tolerate delays, problems, or suffering without becoming annoyed or anxious.",
    category=[TraitCategory.POSITIVE],
)
LOYAL = Trait(
    name="Loyal",
    description="Giving or showing firm and constant support or allegiance to a person or institution.",
    category=[TraitCategory.POSITIVE],
)
RELIABLE = Trait(
    name="Reliable",
    description="Consistently good in quality or performance; able to be trusted.",
    category=[TraitCategory.POSITIVE],
)
DEPENDABLE = Trait(
    name="Dependable",
    description="Trustworthy and reliable.",
    category=[TraitCategory.POSITIVE],
)
HONEST = Trait(
    name="Honest",
    description="Free of deceit and untruthfulness; sincere.",
    category=[TraitCategory.POSITIVE],
)
INTEGRITY = Trait(
    name="Integrity",
    description="The quality of being honest and having strong moral principles; moral uprightness.",
    category=[TraitCategory.POSITIVE],
)
BRAVE = Trait(
    name="Brave",
    description="Ready to face and endure danger or pain; showing courage.",
    category=[TraitCategory.POSITIVE],
)
COURAGEOUS = Trait(
    name="Courageous",
    description="Not deterred by danger or pain; brave.",
    category=[TraitCategory.POSITIVE],
)
ADVENTUROUS = Trait(
    name="Adventurous",
    description="Willing to take risks or to try out new methods, ideas, or experiences.",
    category=[TraitCategory.POSITIVE],
)
CREATIVE = Trait(
    name="Creative",
    description="Relating to or involving the use of the imagination or original ideas to create something.",
    category=[TraitCategory.POSITIVE],
)
INNOVATIVE = Trait(
    name="Innovative",
    description="Featuring new methods; advanced and original.",
    category=[TraitCategory.POSITIVE],
)
ADAPTABLE = Trait(
    name="Adaptable",
    description="Able to adjust to new conditions.",
    category=[TraitCategory.POSITIVE],
)
FLEXIBLE = Trait(
    name="Flexible",
    description="Able to be easily modified to respond to altered circumstances.",
    category=[TraitCategory.POSITIVE],
)
ENTHUSIASTIC = Trait(
    name="Enthusiastic",
    description="Having or showing intense and eager enjoyment, interest, or approval.",
    category=[TraitCategory.POSITIVE],
)
DILIGENT = Trait(
    name="Diligent",
    description="Having or showing care and conscientiousness in one's work or duties.",
    category=[TraitCategory.POSITIVE],
)
INDUSTRIOUS = Trait(
    name="Industrious",
    description="Diligent and hard-working.",
    category=[TraitCategory.POSITIVE],
)
CONSCIENTIOUS = Trait(
    name="Conscientious",
    description="Wishing to do one's work or duty well and thoroughly.",
    category=[TraitCategory.POSITIVE],
)
METICULOUS = Trait(
    name="Meticulous",
    description="Showing great attention to detail; very careful and precise.",
    category=[TraitCategory.POSITIVE],
)
DISCIPLINED = Trait(
    name="Disciplined",
    description="Showing a controlled form of behavior or way of working.",
    category=[TraitCategory.POSITIVE],
)
ORGANIZED = Trait(
    name="Organized",
    description="Arranged or structured in a systematic way.",
    category=[TraitCategory.POSITIVE],
)
RESPONSIBLE = Trait(
    name="Responsible",
    description="Having an obligation to do something, or having control over or care for someone, as part of one's job or role.",
    category=[TraitCategory.POSITIVE],
)
PROACTIVE = Trait(
    name="Proactive",
    description="Creating or controlling a situation by causing something to happen rather than responding to it after it has happened.",
    category=[TraitCategory.POSITIVE],
)
INITIATIVE = Trait(
    name="Initiative",
    description="The ability to assess and initiate things independently.",
    category=[TraitCategory.POSITIVE],
)
CHARISMATIC = Trait(
    name="Charismatic",
    description="Exercising a compelling charm that inspires devotion in others.",
    category=[TraitCategory.POSITIVE],
)
INSPIRING = Trait(
    name="Inspiring",
    description="Having the effect of inspiring someone.",
    category=[TraitCategory.POSITIVE],
)
MOTIVATING = Trait(
    name="Motivating",
    description="Providing a motive for doing something.",
    category=[TraitCategory.POSITIVE],
)
CONFIDENT = Trait(
    name="Confident",
    description="Feeling or showing confidence in oneself or one's abilities or qualities.",
    category=[TraitCategory.POSITIVE],
)
ASSERTIVE = Trait(
    name="Assertive",
    description="Having or showing a confident and forceful personality.",
    category=[TraitCategory.POSITIVE],
)
DECISIVE = Trait(
    name="Decisive",
    description="Making decisions quickly and effectively.",
    category=[TraitCategory.POSITIVE],
)
STRATEGIC = Trait(
    name="Strategic",
    description="Relating to the identification of long-term or overall aims and interests and the means of achieving them.",
    category=[TraitCategory.POSITIVE],
)
ANALYTICAL = Trait(
    name="Analytical",
    description="Relating to or using analysis or logical reasoning.",
    category=[TraitCategory.POSITIVE],
)
PERCEPTIVE = Trait(
    name="Perceptive",
    description="Having or showing sensitive insight.",
    category=[TraitCategory.POSITIVE],
)
INTUITIVE = Trait(
    name="Intuitive",
    description="Using or based on what one feels to be true even without conscious reasoning.",
    category=[TraitCategory.POSITIVE],
)
WITTY = Trait(
    name="Witty",
    description="Showing or characterized by quick and inventive verbal humor.",
    category=[TraitCategory.POSITIVE],
)
HUMOROUS = Trait(
    name="Humorous",
    description="Causing laughter and amusement; funny.",
    category=[TraitCategory.POSITIVE],
)
PLAYFUL = Trait(
    name="Playful",
    description="Fond of games and amusement; lighthearted.",
    category=[TraitCategory.POSITIVE],
)
ENERGETIC = Trait(
    name="Energetic",
    description="Showing or involving great activity or vitality.",
    category=[TraitCategory.POSITIVE],
)
VIBRANT = Trait(
    name="Vibrant",
    description="Full of energy and enthusiasm.",
    category=[TraitCategory.POSITIVE],
)
SOCIABLE = Trait(
    name="Sociable",
    description="Willing to talk and engage in activities with other people; friendly.",
    category=[TraitCategory.POSITIVE],
)
OUTGOING = Trait(
    name="Outgoing",
    description="Friendly and socially confident.",
    category=[TraitCategory.POSITIVE],
)
GREGARIOUS = Trait(
    name="Gregarious",
    description="Fond of company; sociable.",
    category=[TraitCategory.POSITIVE],
)
CALM = Trait(
    name="Calm",
    description="Not showing or feeling nervousness, anger, or other strong emotions.",
    category=[TraitCategory.POSITIVE],
)
POISED = Trait(
    name="Poised",
    description="Having a composed and self-assured manner.",
    category=[TraitCategory.POSITIVE],
)
GRACEFUL = Trait(
    name="Graceful",
    description="Characterized by elegance or beauty of form, manner, movement, or speech.",
    category=[TraitCategory.POSITIVE],
)
DIPLOMATIC = Trait(
    name="Diplomatic",
    description="Having or showing an ability to deal with people in a sensitive and effective way.",
    category=[TraitCategory.POSITIVE],
)
CHARMING = Trait(
    name="Charming",
    description="Pleasing or delighting.",
    category=[TraitCategory.POSITIVE],
)
SOPHISTICATED = Trait(
    name="Sophisticated",
    description="Having, revealing, or proceeding from a great deal of worldly experience and knowledge of fashion and culture.",
    category=[TraitCategory.POSITIVE],
)
CULTURED = Trait(
    name="Cultured",
    description="Characterized by refined manners, tastes, and knowledge.",
    category=[TraitCategory.POSITIVE],
)
OPEN_MINDED = Trait(
    name="Open-minded",
    description="Willing to consider new ideas; unprejudiced.",
    category=[TraitCategory.POSITIVE],
)
CURIOUS = Trait(
    name="Curious",
    description="Eager to know or learn something.",
    category=[TraitCategory.POSITIVE],
)
INQUISITIVE = Trait(
    name="Inquisitive",
    description="Given to inquiry, research, or asking questions; eager for knowledge; intellectually curious.",
    category=[TraitCategory.POSITIVE],
)
THOUGHTFUL = Trait(
    name="Thoughtful",
    description="Showing consideration for the needs of other people.",
    category=[TraitCategory.POSITIVE],
)
REFLECTIVE = Trait(
    name="Reflective",
    description="Relating to or characterized by deep thought; thoughtful.",
    category=[TraitCategory.POSITIVE],
)

# Negative Traits
ARROGANT = Trait(
    name="Arrogant",
    description="Having or revealing an exaggerated sense of one's own importance or abilities.",
    category=[TraitCategory.NEGATIVE],
)
EGOTISTICAL = Trait(
    name="Egotistical",
    description="Excessively conceited or absorbed in oneself; self-centered.",
    category=[TraitCategory.NEGATIVE],
)
SELFISH = Trait(
    name="Selfish",
    description="Lacking consideration for others; concerned chiefly with one's own personal profit or pleasure.",
    category=[TraitCategory.NEGATIVE],
)
GREEDY = Trait(
    name="Greedy",
    description="Having an excessive desire for wealth or possessions or more than is needed or deserved.",
    category=[TraitCategory.NEGATIVE],
)
MANIPULATIVE = Trait(
    name="Manipulative",
    description="Characterized by unscrupulous cunning, deception, or exploitation of others.",
    category=[TraitCategory.NEGATIVE],
)
DECEITFUL = Trait(
    name="Deceitful",
    description="Guilty of or involving deceit; misleading others.",
    category=[TraitCategory.NEGATIVE],
)
DISHONEST = Trait(
    name="Dishonest",
    description="Behaving or prone to behave in an untrustworthy or fraudulent way.",
    category=[TraitCategory.NEGATIVE],
)
UNTRUSTWORTHY = Trait(
    name="Untrustworthy",
    description="Not able to be relied on as honest or truthful.",
    category=[TraitCategory.NEGATIVE],
)
IRRESPONSIBLE = Trait(
    name="Irresponsible",
    description="Not showing a proper sense of responsibility.",
    category=[TraitCategory.NEGATIVE],
)
CARELESS = Trait(
    name="Careless",
    description="Not giving sufficient attention to avoiding harm or error.",
    category=[TraitCategory.NEGATIVE],
)
RECKLESS = Trait(
    name="Reckless",
    description="Heedless of danger or the consequences of one's actions; rash.",
    category=[TraitCategory.NEGATIVE],
)
IMPULSIVE = Trait(
    name="Impulsive",
    description="Acting or done without forethought.",
    category=[TraitCategory.NEGATIVE],
)
AGGRESSIVE = Trait(
    name="Aggressive",
    description="Ready or likely to attack or confront; characterized by or resulting from aggression.",
    category=[TraitCategory.NEGATIVE],
)
HOSTILE = Trait(
    name="Hostile",
    description="Unfriendly and antagonistic.",
    category=[TraitCategory.NEGATIVE],
)
RUDE = Trait(
    name="Rude",
    description="Offensively impolite or ill-mannered.",
    category=[TraitCategory.NEGATIVE],
)
INCONSIDERATE = Trait(
    name="Inconsiderate",
    description="Thoughtlessly causing hurt or inconvenience to others.",
    category=[TraitCategory.NEGATIVE],
)
INSENSITIVE = Trait(
    name="Insensitive",
    description="Showing or feeling no concern for others' feelings.",
    category=[TraitCategory.NEGATIVE],
)
CRUEL = Trait(
    name="Cruel",
    description="Willfully causing pain or suffering to others, or feeling no concern about it.",
    category=[TraitCategory.NEGATIVE],
)
MALICIOUS = Trait(
    name="Malicious",
    description="Characterized by malice; intending or intended to do harm.",
    category=[TraitCategory.NEGATIVE],
)
SPITEFUL = Trait(
    name="Spiteful",
    description="Showing or caused by malice; malevolent.",
    category=[TraitCategory.NEGATIVE],
)
ENVIOUS = Trait(
    name="Envious",
    description="Feeling or showing envy.",
    category=[TraitCategory.NEGATIVE],
)
JEALOUS = Trait(
    name="Jealous",
    description="Feeling or showing an envious resentment of someone or their achievements, possessions, or advantages.",
    category=[TraitCategory.NEGATIVE],
)
STUBBORN = Trait(
    name="Stubborn",
    description="Having or showing dogged determination not to change one's attitude or position on something, especially in spite of good arguments or reasons to do so.",
    category=[TraitCategory.NEGATIVE],
)
OBSTINATE = Trait(
    name="Obstinate",
    description="Stubbornly refusing to change one's opinion or chosen course of action, despite attempts to persuade one to do so.",
    category=[TraitCategory.NEGATIVE],
)
RIGID = Trait(
    name="Rigid",
    description="Unable to change or be changed according to the circumstances.",
    category=[TraitCategory.NEGATIVE],
)
INFLEXIBLE = Trait(
    name="Inflexible",
    description="Unwilling to change or compromise.",
    category=[TraitCategory.NEGATIVE],
)
NARROW_MINDED = Trait(
    name="Narrow-minded",
    description="Not willing to listen to or tolerate other people's views; prejudiced.",
    category=[TraitCategory.NEGATIVE],
)
BIGOTED = Trait(
    name="Bigoted",
    description="Having or revealing an obstinate belief in the superiority of one's own opinions and a prejudiced intolerance of the opinions of others.",
    category=[TraitCategory.NEGATIVE],
)
PESSIMISTIC = Trait(
    name="Pessimistic",
    description="Tending to see the worst aspect of things or believe that the worst will happen.",
    category=[TraitCategory.NEGATIVE],
)
CYNICAL = Trait(
    name="Cynical",
    description="Believing that people are motivated by self-interest; distrustful of human sincerity or integrity.",
    category=[TraitCategory.NEGATIVE],
)
SARCASTIC = Trait(
    name="Sarcastic", description="Using sarcasm.", category=[TraitCategory.NEGATIVE]
)
LAZY = Trait(
    name="Lazy",
    description="Unwilling to work or use energy.",
    category=[TraitCategory.NEGATIVE],
)
APATHETIC = Trait(
    name="Apathetic",
    description="Showing or feeling no interest, enthusiasm, or concern.",
    category=[TraitCategory.NEGATIVE],
)
INDIFFERENT = Trait(
    name="Indifferent",
    description="Having no particular interest or sympathy; unconcerned.",
    category=[TraitCategory.NEGATIVE],
)
DISORGANIZED = Trait(
    name="Disorganized",
    description="Lacking organization or tidiness.",
    category=[TraitCategory.NEGATIVE],
)
UNDISCIPLINED = Trait(
    name="Undisciplined",
    description="Lacking in discipline; uncontrolled in behavior or manner.",
    category=[TraitCategory.NEGATIVE],
)
IMMATURE = Trait(
    name="Immature",
    description="Having or showing a lack of emotional maturity; childish.",
    category=[TraitCategory.NEGATIVE],
)
WHINY = Trait(
    name="Whiny",
    description="Inclined to complain in a high-pitched, childish voice.",
    category=[TraitCategory.NEGATIVE],
)
FICKLE = Trait(
    name="Fickle",
    description="Changing frequently, especially as regards one's loyalties, interests, or affection.",
    category=[TraitCategory.NEGATIVE],
)
IMPULSIVE_NEG = Trait(
    name="Impulsive",
    description="Acting or done without forethought.",
    category=[TraitCategory.NEGATIVE],
)  # Renamed to avoid duplicate
MOODY = Trait(
    name="Moody",
    description="Given to sudden and unaccountable changes of mood or temper.",
    category=[TraitCategory.NEGATIVE],
)
TEMPERAMENTAL = Trait(
    name="Temperamental",
    description="Liable to unreasonable changes of mood.",
    category=[TraitCategory.NEGATIVE],
)
VOLATILE = Trait(
    name="Volatile",
    description="Liable to change rapidly and unpredictably, especially for the worse.",
    category=[TraitCategory.NEGATIVE],
)
ANXIOUS = Trait(
    name="Anxious",
    description="Experiencing worry, unease, or nervousness.",
    category=[TraitCategory.NEGATIVE],
)
INSECURE = Trait(
    name="Insecure",
    description="Not confident or assured; uncertain and anxious.",
    category=[TraitCategory.NEGATIVE],
)
COWARDLY = Trait(
    name="Cowardly", description="Lacking courage.", category=[TraitCategory.NEGATIVE]
)
TIMID = Trait(
    name="Timid",
    description="Showing a lack of courage or confidence; easily frightened.",
    category=[TraitCategory.NEGATIVE],
)
SHY = Trait(
    name="Shy",
    description="Nervous or reserved in company.",
    category=[TraitCategory.NEGATIVE],
)
INTROVERTED_NEG = Trait(
    name="Introverted",
    description="Characterized by concern primarily with one's own thoughts and feelings rather than with external things.",
    category=[TraitCategory.NEGATIVE],
)  # Renamed to avoid duplicate
WITHDRAWN = Trait(
    name="Withdrawn",
    description="Not wanting to communicate with other people.",
    category=[TraitCategory.NEGATIVE],
)
RESERVED_NEG = Trait(
    name="Reserved",
    description="Slow to reveal emotion or opinions.",
    category=[TraitCategory.NEGATIVE],
)  # Renamed to avoid duplicate
POMPOUS = Trait(
    name="Pompous",
    description="Affectedly and irritatingly grand, solemn, or self-important.",
    category=[TraitCategory.NEGATIVE],
)
BOASTFUL = Trait(
    name="Boastful",
    description="Showing excessive pride and self-satisfaction in one's achievements, possessions, or abilities.",
    category=[TraitCategory.NEGATIVE],
)
VAIN = Trait(
    name="Vain",
    description="Having or showing an excessively high opinion of one's appearance, abilities, or worth.",
    category=[TraitCategory.NEGATIVE],
)

# Neutral/Situational Traits
INTROVERTED = Trait(
    name="Introverted",
    description="Tends to be reserved and gains energy from solitude.",
    category=[TraitCategory.NEUTRAL],
)
EXTROVERTED = Trait(
    name="Extroverted",
    description="Tends to be outgoing and gains energy from social interaction.",
    category=[TraitCategory.NEUTRAL],
)
RESERVED = Trait(
    name="Reserved",
    description="Slow to reveal emotion or opinions.",
    category=[TraitCategory.NEUTRAL],
)
QUIET = Trait(
    name="Quiet",
    description="Making little or no noise.",
    category=[TraitCategory.NEUTRAL],
)
SERIOUS = Trait(
    name="Serious",
    description="Acting or speaking sincerely and in earnest, rather than in a playful or humorous way.",
    category=[TraitCategory.NEUTRAL],
)
INTENSE = Trait(
    name="Intense",
    description="Exhibiting a highly concentrated form of feeling, quality, or action.",
    category=[TraitCategory.NEUTRAL],
)
PRIVATE = Trait(
    name="Private",
    description="Not wishing to share one's thoughts and feelings with others.",
    category=[TraitCategory.NEUTRAL],
)
COMPLEX = Trait(
    name="Complex",
    description="Consisting of many different and connected parts; not easy to analyze or understand.",
    category=[TraitCategory.NEUTRAL],
)
ECCENTRIC = Trait(
    name="Eccentric",
    description="Unconventional and slightly strange.",
    category=[TraitCategory.NEUTRAL],
)
QUIRKY = Trait(
    name="Quirky",
    description="Characterized by peculiar or unexpected traits or aspects.",
    category=[TraitCategory.NEUTRAL],
)
