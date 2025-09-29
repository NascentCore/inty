"""Tests for endpoint filtering functionality"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.middleware.endpoint_filter import EndpointFilterMiddleware
from app.core.endpoint_config import is_endpoint_hidden_in_production


class TestEndpointFiltering:
    """Test cases for endpoint filtering functionality"""
    
    def test_is_endpoint_hidden_in_production(self):
        """Test endpoint hiding logic in production"""
        
        # Test evaluation endpoints
        assert is_endpoint_hidden_in_production("/api/v1/evaluation/sessions") == True
        assert is_endpoint_hidden_in_production("/api/v1/evaluation/agents") == True
        
        # Test admin endpoints
        assert is_endpoint_hidden_in_production("/api/v1/admin/system-settings") == True
        assert is_endpoint_hidden_in_production("/api/v1/admin/users") == True
        
        # Test specific report endpoints
        assert is_endpoint_hidden_in_production("/api/v1/report/", "GET") == True
        assert is_endpoint_hidden_in_production("/api/v1/report/", "POST") == False
        
        # Test allowed endpoints
        assert is_endpoint_hidden_in_production("/api/v1/auth/login") == False
        assert is_endpoint_hidden_in_production("/api/v1/users/profile") == False
        assert is_endpoint_hidden_in_production("/api/v1/chat/send") == False
        assert is_endpoint_hidden_in_production("/api/v1/report") == False  # POST endpoint allowed
    
    @patch('app.core.config.global_config_loaded_from_config_yaml.app.environment', 'prod')
    def test_middleware_blocks_production_endpoints(self):
        """Test that middleware blocks restricted endpoints in production"""
        
        app = FastAPI()
        
        # Add a test endpoint that should be blocked
        @app.get("/api/v1/evaluation/test")
        async def test_evaluation_endpoint():
            return {"message": "This should be blocked in production"}
        
        # Add middleware
        app.add_middleware(EndpointFilterMiddleware)
        
        client = TestClient(app)
        
        # Test that evaluation endpoint is blocked
        response = client.get("/api/v1/evaluation/test")
        assert response.status_code == 404
        assert "not available in this environment" in response.json()["message"]
    
    @patch('app.core.config.global_config_loaded_from_config_yaml.app.environment', 'dev')
    def test_middleware_allows_endpoints_in_dev(self):
        """Test that middleware allows all endpoints in development"""
        
        app = FastAPI()
        
        # Add a test endpoint that would be blocked in production
        @app.get("/api/v1/evaluation/test")
        async def test_evaluation_endpoint():
            return {"message": "This should be allowed in dev"}
        
        # Add middleware
        app.add_middleware(EndpointFilterMiddleware)
        
        client = TestClient(app)
        
        # Test that evaluation endpoint is allowed in dev
        response = client.get("/api/v1/evaluation/test")
        assert response.status_code == 200
        assert response.json()["message"] == "This should be allowed in dev"
    
    def test_non_api_requests_bypassed(self):
        """Test that non-API requests are not filtered"""
        
        app = FastAPI()
        
        @app.get("/health")
        async def health_check():
            return {"status": "ok"}
        
        @app.get("/static/file.txt")
        async def static_file():
            return {"content": "static file"}
        
        # Add middleware
        app.add_middleware(EndpointFilterMiddleware)
        
        client = TestClient(app)
        
        # Test that non-API requests are not filtered
        response = client.get("/health")
        assert response.status_code == 200
        
        response = client.get("/static/file.txt")
        assert response.status_code == 200
    
    @patch('app.core.config.global_config_loaded_from_config_yaml.app.environment', 'prod')
    def test_specific_report_endpoint_blocked(self):
        """Test that specific report endpoint is blocked in production"""
        
        app = FastAPI()
        
        @app.get("/api/v1/report/")
        async def list_reports():
            return {"reports": []}
        
        @app.post("/api/v1/report/")
        async def create_report():
            return {"message": "Report created"}
        
        # Add middleware
        app.add_middleware(EndpointFilterMiddleware)
        
        client = TestClient(app)
        
        # Test that GET /api/v1/report/ is blocked
        response = client.get("/api/v1/report/")
        assert response.status_code == 404
        
        # Test that POST /api/v1/report/ is allowed
        response = client.post("/api/v1/report/")
        assert response.status_code == 200


class TestEnvironmentControlDecorators:
    """Test cases for environment control decorators"""
    
    @patch('app.core.config.global_config_loaded_from_config_yaml.app.environment', 'prod')
    def test_production_hidden_decorator(self):
        """Test production_hidden decorator blocks in production"""
        from app.api.decorators.environment_control import production_hidden
        
        @production_hidden
        async def test_function():
            return {"message": "This should be blocked in production"}
        
        # In production, this should raise an exception
        with pytest.raises(Exception):  # HTTPException from the decorator
            import asyncio
            asyncio.run(test_function())
    
    @patch('app.core.config.global_config_loaded_from_config_yaml.app.environment', 'dev')
    def test_production_hidden_decorator_allows_in_dev(self):
        """Test production_hidden decorator allows in dev"""
        from app.api.decorators.environment_control import production_hidden
        
        @production_hidden
        async def test_function():
            return {"message": "This should be allowed in dev"}
        
        # In dev, this should work
        import asyncio
        result = asyncio.run(test_function())
        assert result["message"] == "This should be allowed in dev"


if __name__ == "__main__":
    pytest.main([__file__])
