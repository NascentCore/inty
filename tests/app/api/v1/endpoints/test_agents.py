import pytest
from loguru import logger

from tests.app.api.test_client import TestClient


@pytest.mark.noci
def test_create_and_delete_user():
    """Test the simplest create user and delete user process."""
    # Create test client with localhost server
    test_client = TestClient("http://localhost:8000")
    
    # Create user and get token
    logger.info("Creating guest user...")
    token = test_client.create_user()
    assert token is not None
    assert len(token) > 0
    logger.info(f"User created successfully, guest_id: {test_client.guest_id}")
    
    # Delete user
    logger.info("Deleting user account...")
    test_client.delete_user()
    logger.info("User deleted successfully")
    
    # Close the HTTP client
    test_client.close()

