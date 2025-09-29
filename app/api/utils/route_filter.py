"""Route filtering utilities for environment-based API control"""

import logging
from typing import Any, Dict, List, Set

from fastapi import APIRouter
from fastapi.routing import APIRoute

from app.core.config import global_config_loaded_from_config_yaml

logger = logging.getLogger(__name__)


class EnvironmentRouteFilter:
    """
    Utility class to filter routes based on environment configuration.
    """
    
    def __init__(self):
        self.environment = global_config_loaded_from_config_yaml.app.environment
        
        # Define which route prefixes should be hidden in production
        self.production_hidden_prefixes = {
            "/evaluation",
            "/admin",
        }
        
        # Define specific routes that should be hidden in production
        self.production_hidden_routes = {
            "/report/",  # GET /api/v1/report/ - list reports (admin only)
        }
        
        logger.info(f"EnvironmentRouteFilter initialized for environment: {self.environment}")
    
    def should_include_route(self, route: APIRoute) -> bool:
        """
        Determine if a route should be included based on environment.
        
        Args:
            route: FastAPI route object
            
        Returns:
            True if route should be included, False otherwise
        """
        path = route.path
        
        # In production, hide restricted routes
        if self.environment == "prod":
            # Check for prefix matches
            for hidden_prefix in self.production_hidden_prefixes:
                if path.startswith(hidden_prefix):
                    logger.debug(f"Filtering out route in production: {path}")
                    return False
            
            # Check for exact matches
            if path in self.production_hidden_routes:
                logger.debug(f"Filtering out specific route in production: {path}")
                return False
        
        return True
    
    def filter_router_routes(self, router: APIRouter) -> List[APIRoute]:
        """
        Filter routes from a router based on environment.
        
        Args:
            router: FastAPI router object
            
        Returns:
            List of routes that should be included
        """
        filtered_routes = []
        
        for route in router.routes:
            if isinstance(route, APIRoute):
                if self.should_include_route(route):
                    filtered_routes.append(route)
                else:
                    logger.info(f"Filtered out route: {route.path} (environment: {self.environment})")
            else:
                # Include non-APIRoute objects (like sub-routers)
                filtered_routes.append(route)
        
        return filtered_routes
    
    def create_filtered_router(self, router: APIRouter) -> APIRouter:
        """
        Create a new router with filtered routes.
        
        Args:
            router: Original router
            
        Returns:
            New router with filtered routes
        """
        filtered_routes = self.filter_router_routes(router)
        
        # Create new router with same configuration
        new_router = APIRouter(
            prefix=router.prefix,
            tags=router.tags,
            dependencies=router.dependencies,
            responses=router.responses,
            callbacks=router.callbacks,
            routes=filtered_routes,
            redirect_slashes=router.redirect_slashes,
            default_response_class=router.default_response_class,
        )
        
        return new_router


# Global instance
route_filter = EnvironmentRouteFilter()


def get_environment_controlled_router(router: APIRouter) -> APIRouter:
    """
    Get a router with environment-controlled routes.
    
    Args:
        router: Original router
        
    Returns:
        Router with filtered routes based on environment
    """
    return route_filter.create_filtered_router(router)
