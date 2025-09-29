"""Decorators for environment-based endpoint control"""

import logging
from functools import wraps
from typing import List, Optional, Set

from fastapi import HTTPException

from app.core.config import global_config_loaded_from_config_yaml

logger = logging.getLogger(__name__)


def environment_controlled(
    allowed_environments: Optional[List[str]] = None,
    blocked_environments: Optional[List[str]] = None,
    hide_in_production: bool = False
):
    """
    Decorator to control endpoint availability based on environment.
    
    Args:
        allowed_environments: List of environments where this endpoint is allowed
        blocked_environments: List of environments where this endpoint is blocked
        hide_in_production: If True, hide this endpoint in production environment
        
    Examples:
        @environment_controlled(hide_in_production=True)
        def admin_endpoint():
            pass
            
        @environment_controlled(allowed_environments=["dev", "staging"])
        def dev_only_endpoint():
            pass
            
        @environment_controlled(blocked_environments=["prod"])
        def non_prod_endpoint():
            pass
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_env = global_config_loaded_from_config_yaml.app.environment
            
            # Check if endpoint should be hidden in production
            if hide_in_production and current_env == "prod":
                logger.warning(f"Blocked access to production-hidden endpoint: {func.__name__}")
                raise HTTPException(
                    status_code=404,
                    detail="Endpoint not available in production environment"
                )
            
            # Check allowed environments
            if allowed_environments and current_env not in allowed_environments:
                logger.warning(f"Blocked access to environment-restricted endpoint: {func.__name__}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Endpoint not available in {current_env} environment"
                )
            
            # Check blocked environments
            if blocked_environments and current_env in blocked_environments:
                logger.warning(f"Blocked access to blocked environment endpoint: {func.__name__}")
                raise HTTPException(
                    status_code=404,
                    detail=f"Endpoint not available in {current_env} environment"
                )
            
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator


def production_hidden(func):
    """
    Convenience decorator to hide endpoint in production environment.
    
    Equivalent to @environment_controlled(hide_in_production=True)
    """
    return environment_controlled(hide_in_production=True)(func)


def dev_only(func):
    """
    Convenience decorator to allow endpoint only in development environment.
    
    Equivalent to @environment_controlled(allowed_environments=["dev"])
    """
    return environment_controlled(allowed_environments=["dev"])(func)


def non_production_only(func):
    """
    Convenience decorator to allow endpoint in all environments except production.
    
    Equivalent to @environment_controlled(blocked_environments=["prod"])
    """
    return environment_controlled(blocked_environments=["prod"])(func)
