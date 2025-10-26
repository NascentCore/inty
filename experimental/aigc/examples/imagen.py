import sys
import os
# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A simple sample of using imagen to generate images with Vertex AI
from gemini_client import GeminiClient
from models import CharacterProfile, CharacterBackground, CharacterEncounter

client = GeminiClient()

# Create a complete character profile with all required fields
character = CharacterProfile(
    name="John Doe",
    age=25,
    gender="male",
    physical_appearance={
        "height": "5'10\"",
        "build": "athletic",
        "hair_color": "brown",
        "eye_color": "blue",
        "distinguishing_features": ["beard", "mustache"],
        "clothing_style": "casual",
        "accessories": ["silver watch"]
    },
    personality_summary="A confident and friendly young man with a warm personality",
    background=CharacterBackground(
        origin="New York City",
        occupation="Software Engineer",
        personality_traits=["confident", "friendly", "ambitious"],
        motivations=["career growth", "helping others"],
        fears=["failure", "loneliness"],
        dreams=["starting his own company", "traveling the world"],
        relationships={"family": "Close with parents and siblings", "friends": "Has a tight-knit group of friends"},
        skills=["programming", "problem-solving", "communication"],
        quirks=["talks with hands", "always carries a notebook"],
        backstory="John grew up in NYC and discovered his passion for technology early. He's worked hard to build his career and enjoys helping others learn programming."
    ),
    encounter=CharacterEncounter(
        scene_description="John is sitting at a coffee shop, working on his laptop with a friendly smile",
        location="Local Coffee Shop",
        mood="Relaxed and approachable",
        initial_dialogue="Hey there! I'm John. Working on some code - always happy to chat about tech or anything else!",
        user_role="A fellow coffee shop patron",
        encounter_type="casual"
    ),
    images=[]  # Will be populated by the image generation
)

client.generate_character_images(character=character, image_style="realistic", num_images=1)