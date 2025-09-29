"""Endpoint filtering middleware for environment-based API hiding"""

import logging
from typing import List, Set

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import global_config_loaded_from_config_yaml
from app.core.endpoint_config import is_endpoint_hidden_in_production

logger = logging.getLogger(__name__)


class EndpointFilterMiddleware(BaseHTTPMiddleware):
    """
    Middleware to filter out non-production endpoints based on environment configuration.
    
    This middleware checks if the current environment allows certain endpoints
    and blocks access to restricted endpoints in production.
    """
    
    def __init__(self, app, restricted_endpoints: List[str] = None):
        super().__init__(app)
        self.restricted_endpoints = set(restricted_endpoints or [])
        self.environment = global_config_loaded_from_config_yaml.app.environment
        
        logger.info(f"EndpointFilterMiddleware initialized for environment: {self.environment}")
        logger.info(f"Using centralized endpoint configuration")
    
    async def dispatch(self, request: Request, call_next):
        """Process the request and filter endpoints based on environment"""
        
        # Skip filtering for non-API requests
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Check if this endpoint should be hidden in production
        if self._should_hide_endpoint(request.url.path, request.method):
            logger.warning(
                f"Blocked access to restricted endpoint: {request.url.path} "
                f"in environment: {self.environment}"
            )
            return JSONResponse(
                status_code=404,
                content={
                    "detail": "Not Found",
                    "message": "The requested endpoint is not available in this environment"
                }
            )
        
        return await call_next(request)
    
    def _should_hide_endpoint(self, path: str, method: str = None) -> bool:
        """
        Determine if an endpoint should be hidden based on environment and path.
        
        Args:
            path: The request path
            method: The HTTP method (optional)
            
        Returns:
            True if the endpoint should be hidden, False otherwise
        """
        # In production environment, hide restricted endpoints
        if self.environment == "prod":
            return is_endpoint_hidden_in_production(path, method)
        
        # In non-production environments, allow all endpoints
        return False


def create_endpoint_filter_middleware(app, restricted_endpoints: List[str] = None):
    """
    Factory function to create endpoint filter middleware.
    
    Args:
        app: FastAPI application instance
        restricted_endpoints: List of additional endpoints to restrict
        
    Returns:
        Configured EndpointFilterMiddleware instance
    """
    return EndpointFilterMiddleware(app, restricted_endpoints)
