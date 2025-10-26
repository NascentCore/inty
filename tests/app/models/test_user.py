from app.models.user import User


def test_user_phone_validation():
# 这应该显示警告日志
    user = User(phone="1234567890")
    assert user.phone == "1234567890"
