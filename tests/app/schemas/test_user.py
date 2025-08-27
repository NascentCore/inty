import pytest
from pydantic import ValidationError

from app.schemas.user import UserUpdate


def test_user_update_email_validator_raises_error():
    """Test that UserUpdate email validator raises ValueError when email is provided"""
    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(email="test@example.com")
    
    assert "Email is not allowed to be updated, should be removed" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(phone="1234567890")
    
    assert "Phone is not allowed to be updated, should be removed" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(age_group="18-24")
    
    assert "Age group is not allowed to be updated, should be removed" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info:
        UserUpdate(system_language="en")
    
    assert "System language is not allowed to be updated, should be removed" in str(exc_info.value)