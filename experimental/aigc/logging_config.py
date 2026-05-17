"""
Logging configuration for the AI Character Generator
"""

import logging
import logging.handlers
from pathlib import Path


def setup_logging(
    log_level: str = "INFO",
    log_to_file: bool = False,
    log_file: str = "character_generator.log",
):
    """
    Setup comprehensive logging configuration

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_to_file: Whether to log to file
        log_file: Log file path
    """

    # Create logs directory if it doesn't exist
    if log_to_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

    # Create formatter with detailed information
    detailed_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    )

    # Create simpler formatter for console
    console_formatter = logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler for detailed logs
    if log_to_file:
        # Rotating file handler to prevent huge log files
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(file_handler)

        # Also create a separate error log
        error_handler = logging.handlers.RotatingFileHandler(
            log_file.replace(".log", "_errors.log"),
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=3,
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(detailed_formatter)
        root_logger.addHandler(error_handler)

    # Set specific logger levels
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str):
    """Get a logger with the specified name"""
    return logging.getLogger(name)


def log_api_request(request_data: dict, logger: logging.Logger):
    """Log API request details"""
    logger.info("API Request received")
    logger.debug(f"Request data: {request_data}")


def log_api_response(
    response_data: dict, logger: logging.Logger, response_time: float
):
    """Log API response details"""
    logger.info(f"API Response sent (time: {response_time:.3f}s)")
    logger.debug(f"Response data: {response_data}")


def log_character_generation_start(description: str, logger: logging.Logger):
    """Log the start of character generation"""
    logger.info(f"Starting character generation: {description}")


def log_character_generation_complete(
    character_name: str, generation_time: float, logger: logging.Logger
):
    """Log the completion of character generation"""
    logger.info(
        f"Character generation completed: {character_name} (time: {generation_time:.2f}s)"
    )


def log_character_generation_error(error: str, logger: logging.Logger):
    """Log character generation errors"""
    logger.error(f"Character generation failed: {error}")


def log_gemini_api_call(endpoint: str, logger: logging.Logger):
    """Log Gemini API calls"""
    logger.info(f"Making Gemini API call to: {endpoint}")


def log_gemini_api_response(
    endpoint: str, response_time: float, logger: logging.Logger
):
    """Log Gemini API responses"""
    logger.info(
        f"Gemini API response received from {endpoint} (time: {response_time:.2f}s)"
    )


def log_gemini_api_error(endpoint: str, error: str, logger: logging.Logger):
    """Log Gemini API errors"""
    logger.error(f"Gemini API error for {endpoint}: {error}")


def log_validation_step(
    step: str, success: bool, logger: logging.Logger, details: str = None
):
    """Log validation steps"""
    if success:
        logger.debug(f"Validation step passed: {step}")
        if details:
            logger.debug(f"  Details: {details}")
    else:
        logger.error(f"Validation step failed: {step}")
        if details:
            logger.error(f"  Details: {details}")


def log_file_operation(
    operation: str,
    file_path: str,
    success: bool,
    logger: logging.Logger,
    error: str = None,
):
    """Log file operations"""
    if success:
        logger.info(f"File operation successful: {operation} - {file_path}")
    else:
        logger.error(f"File operation failed: {operation} - {file_path}")
        if error:
            logger.error(f"  Error: {error}")


# Logging profiles for different environments
def setup_development_logging():
    """Setup logging for development environment"""
    return setup_logging(
        log_level="DEBUG",
        log_to_file=True,
        log_file="logs/character_generator_dev.log",
    )


def setup_production_logging():
    """Setup logging for production environment"""
    return setup_logging(
        log_level="INFO",
        log_to_file=True,
        log_file="logs/character_generator_prod.log",
    )


def setup_test_logging():
    """Setup logging for testing environment"""
    return setup_logging(log_level="WARNING", log_to_file=False)


def setup_verbose_logging():
    """Setup verbose logging for debugging"""
    return setup_logging(
        log_level="DEBUG",
        log_to_file=True,
        log_file="logs/character_generator_verbose.log",
    )
