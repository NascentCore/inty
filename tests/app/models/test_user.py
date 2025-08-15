from app.models.user import User


def test_user_phone_validation():
    # This should show a warning log
    user = User(phone="1234567890")
    assert user.phone == "1234567890"
