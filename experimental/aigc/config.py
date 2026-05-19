import os
from dotenv import load_dotenv
from logging_config import setup_logging

# Load environment variables
load_dotenv()


class Config:
    """Configuration class for the AI Character Generator"""

    # Initialize logging
    logger = setup_logging(
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        log_to_file=os.getenv("LOG_TO_FILE", "False").lower() == "true",
        log_file=os.getenv("LOG_FILE", "logs/character_generator.log"),
    )

    # Gemini API Configuration
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # Application Configuration
    DEBUG = os.getenv("DEBUG", "True").lower() == "true"
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    # Image Generation Settings
    MAX_IMAGES_PER_CHARACTER = int(os.getenv("MAX_IMAGES_PER_CHARACTER", "4"))
    IMAGE_QUALITY = os.getenv("IMAGE_QUALITY", "high")

    # Character Generation Settings
    CHARACTER_GENERATION_MODEL = "gemini-2.5-flash"
    IMAGE_GENERATION_MODEL = "imagen-4.0-generate-preview-06-06"

    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "False").lower() == "true"

    @classmethod
    def validate(cls):
        """Validate that required configuration is present"""
        cls.logger.info("Validating configuration...")

        if not cls.GEMINI_API_KEY:
            cls.logger.error("GEMINI_API_KEY environment variable is required")
            raise ValueError("GEMINI_API_KEY environment variable is required")

        cls.logger.info("Configuration validation successful")
        cls.logger.debug(f"Debug mode: {cls.DEBUG}")
        cls.logger.debug(f"Host: {cls.HOST}")
        cls.logger.debug(f"Port: {cls.PORT}")
        cls.logger.debug(
            f"Max images per character: {cls.MAX_IMAGES_PER_CHARACTER}"
        )
        cls.logger.debug(f"Character model: {cls.CHARACTER_GENERATION_MODEL}")
        cls.logger.debug(f"Image model: {cls.IMAGE_GENERATION_MODEL}")

        return True
