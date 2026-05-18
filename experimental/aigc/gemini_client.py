import base64
import os
from google import genai
from google.genai import types as gemini_types
import json
import time
from PIL import Image as PILImage
from io import BytesIO
from typing import List, Dict, Any
from config import Config
from models import CharacterProfile, CharacterBackground, CharacterEncounter
from utils import safe_json_loads, validate_character_data
from loguru import logger


class GeminiImage(gemini_types.Image):
    """
    A wrapper around the gemini_types.Image class that adds a few convenience methods.
    """

    def decode_base64(self):
        self.image_bytes = base64.b64decode(self.image_bytes)

    def show(self):
        """Show the image using PIL"""
        image = PILImage.open(BytesIO(self.image_bytes))
        image.show()


class GeminiClient:
    """Client for interacting with Gemini API for character generation"""

    def __init__(self):
        """Initialize the Gemini client"""
        logger.info("Initializing Gemini client...")

        try:
            # Check if we should use Vertex AI or Gemini API (Google AI Studio)
            # Vertex AI requires service account credentials, not API key
            use_vertex_ai = (
                os.getenv("GOOGLE_APPLICATION_CREDENTIALS") is not None
            )

            if use_vertex_ai:
                # Use Vertex AI with service account credentials
                logger.info("Using Vertex AI with service account credentials")
                project_id = os.getenv("GOOGLE_CLOUD_PROJECT", "inty-backend")
                location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
                self.client = genai.Client(
                    vertexai=True, project=project_id, location=location
                )
            else:
                # Use Gemini API (Google AI Studio) with API key
                if not Config.GEMINI_API_KEY:
                    raise ValueError(
                        "GEMINI_API_KEY is required for Gemini API (Google AI Studio)"
                    )

                logger.info("Using Gemini API (Google AI Studio) with API key")
                self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

            logger.info(f"Gemini client initialized successfully")
            logger.debug(
                f"Character model: {Config.CHARACTER_GENERATION_MODEL}"
            )
            logger.debug(f"Image model: {Config.IMAGE_GENERATION_MODEL}")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini client: {e}")
            raise

    def generate_character_profile(
        self,
        brief_description: str,
        genre: str = "fantasy",
        tone: str = "neutral",
    ) -> CharacterProfile:
        """Generate a complete character profile from a brief description"""

        logger.info(f"Generating character profile for: {brief_description}")
        logger.debug(f"Genre: {genre}, Tone: {tone}")

        prompt = f"""
        You are an expert character designer and storyteller. Create a detailed, engaging character profile based on this brief description: "{brief_description}"
        
        Genre: {genre}
        Tone: {tone}
        
        IMPORTANT: Respond with ONLY valid JSON. Do not include any markdown formatting, code blocks, or explanatory text.
        
        Generate a complete character profile in JSON format with the following structure:
        {{
            "name": "Character Name",
            "age": 25,
            "gender": "male/female/non-binary",
            "physical_appearance": {{
                "height": "5'8\"",
                "build": "athletic",
                "hair_color": "brown",
                "eye_color": "blue",
                "distinguishing_features": ["scar on left cheek", "piercing green eyes"],
                "clothing_style": "casual but stylish",
                "accessories": ["silver watch", "leather bracelet"]
            }},
            "personality_summary": "A brief 2-3 sentence summary of their personality",
            "background": {{
                "origin": "Where they're from",
                "occupation": "What they do",
                "personality_traits": ["trait1", "trait2", "trait3"],
                "motivations": ["motivation1", "motivation2"],
                "fears": ["fear1", "fear2"],
                "dreams": ["dream1", "dream2"],
                "relationships": {{"family": "description", "friends": "description"}},
                "skills": ["skill1", "skill2", "skill3"],
                "quirks": ["quirk1", "quirk2"],
                "backstory": "A detailed 3-4 paragraph backstory explaining their past, key events, and how they became who they are today"
            }},
            "encounter": {{
                "scene_description": "A vivid 2-3 paragraph description of where and how the user meets this character",
                "location": "Specific location name",
                "mood": "atmospheric description",
                "initial_dialogue": "The first thing the character says to the user",
                "user_role": "What role the user plays in this encounter",
                "encounter_type": "casual/adventure/mystery/romance"
            }}
        }}
        
        Make the character compelling, unique, and suitable for role-play. Ensure all details are consistent and create a rich, immersive experience.
        
        Remember: Return ONLY the JSON object, no additional formatting or text.
        """

        logger.debug(f"Generated prompt length: {len(prompt)} characters")

        try:
            logger.info("Sending character generation request to Gemini API...")
            start_time = time.time()

            response = self.client.models.generate_content(
                model=Config.CHARACTER_GENERATION_MODEL, contents=prompt
            )

            api_time = time.time() - start_time
            logger.info(
                f"Gemini API response received in {api_time:.2f} seconds"
            )
            logger.debug(
                f"Response text length: {len(response.text)} characters"
            )

            # Log the first 200 characters of response for debugging
            response_preview = (
                response.text[:200] + "..."
                if len(response.text) > 200
                else response.text
            )
            logger.debug(f"Response preview: {response_preview}")

            logger.info("Parsing JSON response...")
            character_data = safe_json_loads(response.text, self.logger)
            logger.info("JSON parsing successful")

            # Validate character data structure
            if not validate_character_data(character_data, self.logger):
                raise ValueError("Character data validation failed")

            # Log character data structure
            logger.debug(
                f"Character name: {character_data.get('name', 'Unknown')}"
            )
            logger.debug(
                f"Character age: {character_data.get('age', 'Unknown')}"
            )
            logger.debug(
                f"Character gender: {character_data.get('gender', 'Unknown')}"
            )

            # Create CharacterProfile object
            logger.info("Creating CharacterProfile object...")
            background = CharacterBackground(**character_data["background"])
            encounter = CharacterEncounter(**character_data["encounter"])

            character = CharacterProfile(
                name=character_data["name"],
                age=character_data["age"],
                gender=character_data["gender"],
                physical_appearance=character_data["physical_appearance"],
                personality_summary=character_data["personality_summary"],
                background=background,
                encounter=encounter,
                images=[],  # Will be populated separately
            )

            logger.info(
                f"Character profile created successfully: {character.name}"
            )
            return character

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(
                f"Response text: {response.text if 'response' in locals() else 'No response'}"
            )
            raise Exception(f"Failed to parse character profile JSON: {str(e)}")
        except KeyError as e:
            logger.error(f"Missing required field in character data: {e}")
            logger.error(
                f"Available fields: {list(character_data.keys()) if 'character_data' in locals() else 'No data'}"
            )
            raise Exception(
                f"Missing required field in character profile: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to generate character profile: {str(e)}")
            raise Exception(f"Failed to generate character profile: {str(e)}")

    def generate_character_images(
        self, character: CharacterProfile, num_images_per_scene: int = 1
    ) -> List[GeminiImage]:
        """Generate consistent character images based on the character profile"""

        logger.info(
            f"Generating {num_images_per_scene} images per scene for {character.images} scenes for character: {character.name}"
        )

        # Create a detailed physical description for image generation
        appearance = character.physical_appearance
        physical_desc = f"""
        {character.name} is a {character.age}-year-old {character.gender} character.
        Height: {appearance.get('height', 'average')}
        Build: {appearance.get('build', 'average')}
        Hair: {appearance.get('hair_color', 'natural')}
        Eyes: {appearance.get('eye_color', 'natural')}
        Distinguishing features: {', '.join(appearance.get('distinguishing_features', []))}
        Clothing style: {appearance.get('clothing_style', 'casual')}
        Accessories: {', '.join(appearance.get('accessories', []))}
        """

        logger.debug(
            f"Physical description length: {len(physical_desc)} characters"
        )

        images = []
        num_scenes = len(character.images)

        for i, scene in enumerate(character.images):
            # Each scene requires a new image generation run.
            logger.info(f"Generating image {i+1}/{num_scenes}: {scene}")
            image_style = scene.image_style

            image_prompt = f"""
            Create a {image_style} style image of {physical_desc}
            
            Scene: {scene}
            Style: {image_style}
            Mood: {character.encounter.mood}
            
            Make sure the character's appearance is consistent across all images.
            Focus on capturing their personality and the atmosphere of their world.
            """

            logger.debug(f"Image prompt length: {len(image_prompt)} characters")

            # Generate image using Gemini
            start_time = time.time()

            response = self.client.models.generate_images(
                model=Config.IMAGE_GENERATION_MODEL,
                prompt=image_prompt,
                config=gemini_types.GenerateImagesConfig(
                    # Generate only one image per scene.
                    number_of_images=num_images_per_scene,
                    aspect_ratio="3:4",
                    safety_filter_level="block_low_and_above",
                    person_generation="ALLOW_ADULT",
                ),
            )
            image_time = time.time() - start_time

            # Log response for debugging
            logger.info(f"Image generation response: {response}")

            # Extract image data from the response
            assert response.generated_images, "No images generated"
            assert (
                len(response.generated_images) == 1
            ), "Expected exactly one image"

            generated_image: gemini_types.Image = response.generated_images[
                0
            ].image
            assert generated_image, "No image data"
            gemini_image = GeminiImage(**generated_image.model_dump())
            gemini_image.decode_base64()
            images.append(gemini_image)

            logger.info(f"Image {i+1} processed in {image_time:.2f} seconds")

        logger.info(
            f"Successfully generated {len(images)} images for {character.name}"
        )
        return images

    def enhance_character_details(
        self, character: CharacterProfile
    ) -> CharacterProfile:
        """Enhance character details with additional depth and consistency"""

        logger.info(f"Enhancing character details for: {character.name}")

        prompt = f"""
        Enhance and refine this character profile to make it more engaging and consistent:
        
        Character: {character.name}
        Current background: {character.background.backstory}
        
        IMPORTANT: Respond with ONLY valid JSON. Do not include any markdown formatting, code blocks, or explanatory text.
        
        Please provide enhanced details in JSON format:
        {{
            "enhanced_backstory": "More detailed and engaging backstory",
            "additional_quirks": ["quirk1", "quirk2"],
            "speech_patterns": "How they talk and express themselves",
            "body_language": "How they carry themselves and move",
            "emotional_triggers": ["trigger1", "trigger2"],
            "growth_arc": "How they might develop through interaction"
        }}
        
        Remember: Return ONLY the JSON object, no additional formatting or text.
        """

        try:
            logger.info(
                "Sending character enhancement request to Gemini API..."
            )
            start_time = time.time()

            response = self.client.models.generate_content(
                model=Config.CHARACTER_GENERATION_MODEL, prompt=prompt
            )

            api_time = time.time() - start_time
            logger.info(
                f"Enhancement API response received in {api_time:.2f} seconds"
            )

            enhancements = safe_json_loads(response.text, self.logger)
            logger.info("Enhancement JSON parsed successfully")

            # Update character with enhanced details
            original_quirks_count = len(character.background.quirks)
            character.background.quirks.extend(
                enhancements.get("additional_quirks", [])
            )
            character.background.backstory = enhancements.get(
                "enhanced_backstory", character.background.backstory
            )

            # Add new fields to physical_appearance
            character.physical_appearance.update(
                {
                    "speech_patterns": enhancements.get("speech_patterns", ""),
                    "body_language": enhancements.get("body_language", ""),
                    "emotional_triggers": enhancements.get(
                        "emotional_triggers", []
                    ),
                    "growth_arc": enhancements.get("growth_arc", ""),
                }
            )

            new_quirks_count = len(character.background.quirks)
            logger.info(
                f"Character enhanced: added {new_quirks_count - original_quirks_count} new quirks"
            )
            logger.debug(
                f"Enhanced fields: speech_patterns, body_language, emotional_triggers, growth_arc"
            )

            return character

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse enhancement JSON: {e}")
            logger.error(
                f"Response text: {response.text if 'response' in locals() else 'No response'}"
            )
        except Exception as e:
            logger.error(f"Failed to enhance character details: {str(e)}")

        return character

    def generate_structured_json(self, prompt: str) -> Dict[str, Any]:
        """Helper for arbitrary structured outputs in downstream pipelines"""

        logger.info("Generating structured JSON payload via Gemini")
        logger.debug(f"Structured prompt length: {len(prompt)} characters")

        try:
            response = self.client.models.generate_content(
                model=Config.CHARACTER_GENERATION_MODEL, contents=prompt
            )
            logger.info("Structured response received successfully")
            return safe_json_loads(response.text, self.logger)
        except Exception as exc:
            logger.error(f"Failed to build structured JSON: {exc}")
            raise
