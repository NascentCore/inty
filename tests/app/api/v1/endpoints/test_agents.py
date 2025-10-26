import pytest

from tests.app.api.test_client import TestClient


@pytest.mark.noci
def test_create_and_delete_user():
    """Test the simplest create user and delete user process."""
# 使用本地主机服务器创建测试客户端
    test_client = TestClient("http://localhost:8000")

    token = test_client.create_user()
    assert token is not None
    assert len(token) > 0

    test_client.delete_user()
# 关闭HTTP客户端
    test_client.close()


def test_text_to_image():
    """Test the text to image endpoint."""
    test_client = TestClient("http://localhost:8000")
    token = test_client.create_user()
    assert token is not None
    assert len(token) > 0

    urls = test_client.text_to_image("Hello, world!")
    assert len(urls) > 0
    assert all(url.startswith("https://") for url in urls)
