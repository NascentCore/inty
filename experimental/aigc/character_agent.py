import time
import logging
from gemini_client import GeminiClient
from models import CharacterProfile, CharacterGenerationRequest, CharacterGenerationResponse

class CharacterAgent:
    """Main AI agent for generating comprehensive character profiles"""
    
    def __init__(self):
        """Initialize the character agent"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Character Agent...")
        
        try:
            self.gemini_client = GeminiClient()
            self.logger.info("Character Agent initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Character Agent: {e}")
            raise
        
    def generate_character(self, request: CharacterGenerationRequest) -> CharacterGenerationResponse:
        """Generate a complete character profile with images and encounter scenario"""
        
        self.logger.info("Starting character generation process")
        self.logger.info(f"Request details: {request.brief_description}")
        self.logger.debug(f"Genre: {request.genre}, Tone: {request.tone}")
        self.logger.debug(f"Image style: {request.image_style}, Num images: {request.num_images}")
        
        start_time = time.time()
        
        try:
            # Step 1: Generate the base character profile
            self.logger.info("Step 1: Generating base character profile...")
            character = self.gemini_client.generate_character_profile(
                brief_description=request.brief_description,
                genre=request.genre,
                tone=request.tone
            )
            
            step1_time = time.time() - start_time
            self.logger.info(f"Step 1 completed in {step1_time:.2f} seconds")
            self.logger.info(f"Base character created: {character.name}")
            
            # Step 2: Enhance character details for consistency
            self.logger.info("Step 2: Enhancing character details...")
            enhancement_start = time.time()
            
            character = self.gemini_client.enhance_character_details(character)
            
            enhancement_time = time.time() - enhancement_start
            self.logger.info(f"Step 2 completed in {enhancement_time:.2f} seconds")
            self.logger.info(f"Character enhanced: {character.name}")
            
            # Step 3: Generate character images
            self.logger.info("Step 3: Generating character images...")
            image_start = time.time()
            
            images = self.gemini_client.generate_character_images(
                character=character,
                image_style=request.image_style,
                num_images=request.num_images
            )
            character.images = images
            
            image_time = time.time() - image_start
            self.logger.info(f"Step 3 completed in {image_time:.2f} seconds")
            self.logger.info(f"Generated {len(images)} images")
            
            # Step 4: Validate and finalize character
            self.logger.info("Step 4: Validating character...")
            validation_start = time.time()
            
            self._validate_character(character)
            
            validation_time = time.time() - validation_start
            self.logger.info(f"Step 4 completed in {validation_time:.2f} seconds")
            self.logger.info("Character validation successful")
            
            generation_time = time.time() - start_time
            self.logger.info(f"Character generation completed successfully in {generation_time:.2f} seconds")
            
            return CharacterGenerationResponse(
                success=True,
                character=character,
                generation_time=generation_time
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            self.logger.error(f"Character generation failed after {generation_time:.2f} seconds: {str(e)}")
            self.logger.exception("Full exception details:")
            
            return CharacterGenerationResponse(
                success=False,
                error=str(e),
                generation_time=generation_time
            )
    
    def _validate_character(self, character: CharacterProfile) -> None:
        """Validate that the character profile is complete and consistent"""
        
        self.logger.info("Starting character validation...")
        
        # Check required fields
        required_fields = [
            ("name", character.name),
            ("personality_summary", character.personality_summary),
            ("background.backstory", character.background.backstory),
            ("encounter.scene_description", character.encounter.scene_description)
        ]
        
        self.logger.debug("Validating required fields...")
        for field_name, value in required_fields:
            if not value or (isinstance(value, str) and value.strip() == ""):
                self.logger.error(f"Missing or empty required field: {field_name}")
                raise ValueError(f"Character profile is missing required information: {field_name}")
            else:
                self.logger.debug(f"✅ Required field present: {field_name}")
        
        # Check for consistency in physical appearance
        self.logger.debug("Validating physical appearance...")
        appearance = character.physical_appearance
        if not appearance.get('hair_color') or not appearance.get('eye_color'):
            self.logger.error("Character physical appearance is incomplete")
            self.logger.debug(f"Available appearance fields: {list(appearance.keys())}")
            raise ValueError("Character physical appearance is incomplete")
        else:
            self.logger.debug(f"✅ Physical appearance complete: hair={appearance.get('hair_color')}, eyes={appearance.get('eye_color')}")
        
        # Validate encounter scenario
        self.logger.debug("Validating encounter scenario...")
        if not character.encounter.initial_dialogue:
            self.logger.error("Character encounter is missing initial dialogue")
            raise ValueError("Character encounter is missing initial dialogue")
        else:
            self.logger.debug(f"✅ Encounter dialogue present: {character.encounter.initial_dialogue[:50]}...")
        
        # Validate background information
        self.logger.debug("Validating background information...")
        bg = character.background
        bg_checks = [
            ("origin", bg.origin),
            ("occupation", bg.occupation),
            ("personality_traits", bg.personality_traits),
            ("motivations", bg.motivations),
            ("skills", bg.skills)
        ]
        
        for field_name, value in bg_checks:
            if not value or (isinstance(value, str) and value.strip() == "") or (isinstance(value, list) and len(value) == 0):
                self.logger.warning(f"Background field may be incomplete: {field_name}")
            else:
                self.logger.debug(f"✅ Background field present: {field_name}")
        
        # Validate images
        self.logger.debug("Validating generated images...")
        if len(character.images) == 0:
            self.logger.warning("No images were generated for the character")
        else:
            self.logger.debug(f"✅ Generated {len(character.images)} images")
            for i, image in enumerate(character.images):
                self.logger.debug(f"  Image {i+1}: {image.description}")
        
        self.logger.info("Character validation completed successfully")
    
    def get_character_summary(self, character: CharacterProfile) -> dict:
        """Get a summary of the generated character for quick reference"""
        
        self.logger.debug(f"Generating summary for character: {character.name}")
        
        summary = {
            "name": character.name,
            "age": character.age,
            "gender": character.gender,
            "personality": character.personality_summary,
            "occupation": character.background.occupation,
            "encounter_location": character.encounter.location,
            "encounter_type": character.encounter.encounter_type,
            "image_count": len(character.images),
            "key_traits": character.background.personality_traits[:3],
            "main_motivation": character.background.motivations[0] if character.background.motivations else "Unknown"
        }
        
        self.logger.debug(f"Summary generated: {summary['name']} ({summary['age']} years old)")
        return summary
    
    def export_character(self, character: CharacterProfile, format: str = "json") -> str:
        """Export character profile in specified format"""
        
        self.logger.info(f"Exporting character {character.name} in {format} format")
        
        if format.lower() == "json":
            try:
                export_data = character.model_dump_json(indent=2)
                self.logger.debug(f"JSON export size: {len(export_data)} characters")
                return export_data
            except Exception as e:
                self.logger.error(f"Failed to export character as JSON: {e}")
                raise
        elif format.lower() == "text":
            try:
                export_data = self._format_character_as_text(character)
                self.logger.debug(f"Text export size: {len(export_data)} characters")
                return export_data
            except Exception as e:
                self.logger.error(f"Failed to export character as text: {e}")
                raise
        else:
            self.logger.error(f"Unsupported export format: {format}")
            raise ValueError(f"Unsupported export format: {format}")
    
    def _format_character_as_text(self, character: CharacterProfile) -> str:
        """Format character profile as readable text"""
        
        self.logger.debug(f"Formatting character {character.name} as text")
        
        text = f"""
# {character.name} - Character Profile

## Basic Information
- **Age:** {character.age}
- **Gender:** {character.gender}
- **Occupation:** {character.background.occupation}
- **Origin:** {character.background.origin}

## Physical Appearance
- **Height:** {character.physical_appearance.get('height', 'Not specified')}
- **Build:** {character.physical_appearance.get('build', 'Not specified')}
- **Hair:** {character.physical_appearance.get('hair_color', 'Not specified')}
- **Eyes:** {character.physical_appearance.get('eye_color', 'Not specified')}
- **Distinguishing Features:** {', '.join(character.physical_appearance.get('distinguishing_features', []))}
- **Clothing Style:** {character.physical_appearance.get('clothing_style', 'Not specified')}

## Personality
{character.personality_summary}

### Traits
{', '.join(character.background.personality_traits)}

### Motivations
{', '.join(character.background.motivations)}

### Fears
{', '.join(character.background.fears)}

### Dreams
{', '.join(character.background.dreams)}

### Skills
{', '.join(character.background.skills)}

### Quirks
{', '.join(character.background.quirks)}

## Background Story
{character.background.backstory}

## Encounter Scenario
**Location:** {character.encounter.location}
**Type:** {character.encounter.encounter_type}
**Mood:** {character.encounter.mood}

### Scene Description
{character.encounter.scene_description}

### Initial Dialogue
"{character.encounter.initial_dialogue}"

### User's Role
{character.encounter.user_role}

## Generated Images
"""
        
        for i, image in enumerate(character.images, 1):
            text += f"""
### Image {i}
- **Description:** {image.description}
- **Scene:** {image.scene_context}
- **Style:** {image.image_style}
- **URL:** {image.url}
"""
        
        self.logger.debug(f"Text formatting completed for {character.name}")
        return text.strip() 