"""
Utility functions for the AI Character Generator
"""

import json
import re
import logging
from typing import Dict, Any

def clean_json_response(response_text: str, logger: logging.Logger = None) -> str:
    """
    Clean a response text to extract valid JSON from markdown blocks or other formatting
    
    Args:
        response_text: The raw response text from the API
        logger: Optional logger for debugging
        
    Returns:
        Cleaned JSON string
    """
    if logger:
        logger.debug(f"Cleaning response text of length: {len(response_text)}")
# 清晰的除空格
    cleaned = response_text.strip()
# 删除markdown代码块
# 处理 ```json ...```` 模式
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]  # Remove ```json
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]  # Remove ```
    
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]  # Remove trailing ```
# 删除所有剩余的 Markdown 格式
    cleaned = re.sub(r'^```\w*\n?', '', cleaned)  # Remove opening code blocks
    cleaned = re.sub(r'\n?```$', '', cleaned)     # Remove closing code blocks
# 再次强调空格
    cleaned = cleaned.strip()
    
    if logger:
        logger.debug(f"Cleaned response length: {len(cleaned)}")
        logger.debug(f"Cleaned response preview: {cleaned[:200]}...")
    
    return cleaned

def safe_json_loads(json_string: str, logger: logging.Logger = None) -> Dict[str, Any]:
    """
    Safely parse JSON string with error handling and logging
    
    Args:
        json_string: JSON string to parse
        logger: Optional logger for debugging
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        json.JSONDecodeError: If JSON parsing fails
    """
    try:
#首先尝试按原样解析
        return json.loads(json_string)
    except json.JSONDecodeError as e:
        if logger:
            logger.warning(f"Initial JSON parsing failed: {e}")
            logger.debug(f"Attempting to clean JSON string...")
# 尝试清理响应
        cleaned_json = clean_json_response(json_string, logger)
        
        try:
            return json.loads(cleaned_json)
        except json.JSONDecodeError as e2:
            if logger:
                logger.error(f"JSON parsing failed even after cleaning: {e2}")
                logger.error(f"Original string: {json_string}")
                logger.error(f"Cleaned string: {cleaned_json}")
            raise e2

def validate_character_data(data: Dict[str, Any], logger: logging.Logger = None) -> bool:
    """
    Validate that character data has all required fields
    
    Args:
        data: Character data dictionary
        logger: Optional logger for debugging
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = [
        "name", "age", "gender", "physical_appearance", 
        "personality_summary", "background", "encounter"
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in data:
            missing_fields.append(field)
    
    if missing_fields:
        if logger:
            logger.error(f"Missing required fields: {missing_fields}")
        return False
#检查询问结构
    if "background" in data:
        required_background_fields = [
            "origin", "occupation", "personality_traits", 
            "motivations", "fears", "dreams", "relationships", 
            "skills", "quirks", "backstory"
        ]
        
        missing_bg_fields = []
        for field in required_background_fields:
            if field not in data["background"]:
                missing_bg_fields.append(f"background.{field}")
        
        if missing_bg_fields:
            if logger:
                logger.error(f"Missing background fields: {missing_bg_fields}")
            return False
    
    if "encounter" in data:
        required_encounter_fields = [
            "scene_description", "location", "mood", 
            "initial_dialogue", "user_role", "encounter_type"
        ]
        
        missing_enc_fields = []
        for field in required_encounter_fields:
            if field not in data["encounter"]:
                missing_enc_fields.append(f"encounter.{field}")
        
        if missing_enc_fields:
            if logger:
                logger.error(f"Missing encounter fields: {missing_enc_fields}")
            return False
    
    if logger:
        logger.debug("Character data validation passed")
    
    return True

def format_duration(seconds: float) -> str:
    """
    Format duration in a human-readable way
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.2f}s"
    else:
        minutes = int(seconds // 60)
        remaining_seconds = seconds % 60
        return f"{minutes}m {remaining_seconds:.1f}s"

def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
# 删除或替换无效字符
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
#删除前导/尾随空格和点
    sanitized = sanitized.strip('. ')
# 限制长度
    if len(sanitized) > 200:
        sanitized = sanitized[:200]
    return sanitized 