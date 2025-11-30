from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


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


class StageStatus(str, Enum):
    """Status flag for each multistage generation step"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CharacterIdentityCard(BaseModel):
    """Lightweight identity used in the multistage generator"""

    name: str
    alias: str
    archetype: str
    short_bio: str
    vibe: str
    session_goal: str
    key_traits: List[str] = Field(default_factory=list)


class CharacterIntroPack(BaseModel):
    """Public-facing intro & onboarding guidance"""

    elevator_pitch: str
    detailed_introduction: str
    relationship_hooks: List[str] = Field(default_factory=list)
    boundaries: List[str] = Field(default_factory=list)
    conversation_openers: List[str] = Field(default_factory=list)


class RoleplayPrompt(BaseModel):
    """Reusable prompts for immersive role play sessions"""

    title: str
    prompt: str
    npc_goal: str
    player_hook: str
    sample_dialogue: str
    tags: List[str] = Field(default_factory=list)


class ImagePrompt(BaseModel):
    """Blueprint for generating consistent images"""

    title: str
    prompt: str
    style: str
    camera: str
    lighting: str
    color_palette: str


class AudioProfile(BaseModel):
    """Voice guidance for TTS or dubbing"""

    archetype: str
    accent: str
    energy: str
    pace: str
    timbre: str
    sample_lines: List[str] = Field(default_factory=list)


class GenerationStage(BaseModel):
    """Telemetry for each step in the multistage pipeline"""

    key: str
    title: str
    description: str
    status: StageStatus = StageStatus.PENDING
    duration_seconds: float = 0.0
    artifacts: Dict[str, Any] = Field(default_factory=dict)


class MultiStageCharacterPayload(BaseModel):
    """Aggregate payload returned by the multistage generator"""

    identity: CharacterIdentityCard
    introduction: CharacterIntroPack
    roleplay_prompts: List[RoleplayPrompt]
    image_prompts: List[ImagePrompt]
    audio_profile: AudioProfile


class MultiStageGenerationResponse(BaseModel):
    """Response envelope for the multistage generation endpoint"""

    success: bool
    request: CharacterGenerationRequest
    payload: Optional[MultiStageCharacterPayload] = None
    stages: List[GenerationStage] = Field(default_factory=list)
    error: Optional[str] = None
    generation_time: float = 0.0
