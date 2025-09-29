"""Configuration for endpoint environment control"""

from dataclasses import dataclass
from typing import Dict, List, Set


@dataclass
class EndpointEnvironmentConfig:
    """Configuration for endpoint environment control"""
    
    # Endpoints that should be hidden in production environment
    production_hidden_prefixes: Set[str] = None
    
    # Specific routes that should be hidden in production
    production_hidden_routes: Set[str] = None
    
    # Endpoints that should only be available in specific environments
    environment_specific_endpoints: Dict[str, List[str]] = None
    
    def __post_init__(self):
        if self.production_hidden_prefixes is None:
            self.production_hidden_prefixes = {
                "/api/v1/evaluation",
                "/api/v1/admin",
            }
        
        if self.production_hidden_routes is None:
            self.production_hidden_routes = {
                "GET /api/v1/report/",  # GET /api/v1/report/ - list reports (admin only)
            }
        
        if self.environment_specific_endpoints is None:
            self.environment_specific_endpoints = {
                "dev": [],  # Development-only endpoints
                "staging": [],  # Staging-only endpoints
                "prod": [],  # Production-only endpoints
            }


# Global endpoint configuration
endpoint_config = EndpointEnvironmentConfig()


def get_production_hidden_endpoints() -> Set[str]:
    """Get the set of endpoints that should be hidden in production"""
    return endpoint_config.production_hidden_prefixes


def get_production_hidden_routes() -> Set[str]:
    """Get the set of specific routes that should be hidden in production"""
    return endpoint_config.production_hidden_routes


def is_endpoint_hidden_in_production(path: str, method: str = None) -> bool:
    """
    Check if an endpoint should be hidden in production environment.
    
    Args:
        path: The request path
        method: The HTTP method (optional)
        
    Returns:
        True if the endpoint should be hidden in production
    """
    # Check for prefix matches
    for hidden_prefix in endpoint_config.production_hidden_prefixes:
        if path.startswith(hidden_prefix):
            return True
    
    # Check for method-specific exact matches
    if method:
        method_specific_route = f"{method} {path}"
        if method_specific_route in endpoint_config.production_hidden_routes:
            return True
    
    # Check for exact matches (without method)
    if path in endpoint_config.production_hidden_routes:
        return True
    
    return False


def get_environment_allowed_endpoints(environment: str) -> List[str]:
    """
    Get endpoints that are allowed in a specific environment.
    
    Args:
        environment: The environment name
        
    Returns:
        List of allowed endpoint patterns
    """
    return endpoint_config.environment_specific_endpoints.get(environment, [])
