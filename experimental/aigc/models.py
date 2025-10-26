from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class CharacterImage(BaseModel):
    """Model for character images"""

    url: str
    description: str
    scene_context: str
    image_style: str


class CharacterEncounter(BaseModel):
    """Model for character encounter scenarios"""

    scene_description: str
    location: str
    mood: str
    initial_dialogue: str
    user_role: str
    encounter_type: str  # e.g., "casual", "adventure", "mystery", "romance"


class CharacterBackground(BaseModel):
    """Model for character background information"""

    origin: str
    occupation: str
    personality_traits: List[str]
    motivations: List[str]
    fears: List[str]
    dreams: List[str]
    relationships: Dict[str, str]
    skills: List[str]
    quirks: List[str]
    backstory: str


class CharacterProfile(BaseModel):
    """Complete character profile model"""

    name: str
    age: int
    gender: str
    physical_appearance: Dict[str, Any]
    personality_summary: str
    # Not the scene background, but the character background
    background: CharacterBackground
    encounter: CharacterEncounter
    images: List[CharacterImage]
    created_at: datetime = Field(default_factory=datetime.now)


class CharacterGenerationRequest(BaseModel):
    """Request model for character generation"""

    brief_description: str = Field(
        ..., description="Brief description of the character to expand upon"
    )
    genre: Optional[str] = Field(
        default="fantasy",
        description="Genre of the character (fantasy, sci-fi, modern, etc.)",
    )
    tone: Optional[str] = Field(
        default="neutral",
        description="Tone of the character (serious, humorous, mysterious, etc.)",
    )
    image_style: Optional[str] = Field(
        default="realistic", description="Style for generated images"
    )
    num_images: Optional[int] = Field(
        default=4, description="Number of images to generate"
    )


class CharacterGenerationResponse(BaseModel):
    """Response model for character generation"""

    success: bool
    character: Optional[CharacterProfile] = None
    error: Optional[str] = None
    generation_time: float
