"""
端到端测试：Report API

测试后端服务的举报功能，包括：
- 非管理员用户可提交举报/反馈（POST /api/v1/report/ 对任意已登录用户开放）
- 使用 reason_codes 创建举报（新 API）
- 使用 reason_ids 创建举报（向后兼容，旧 API）
- 使用 reason_codes 创建反馈（新 API）
- 使用 reason_ids 创建反馈（向后兼容，旧 API）

列表/详情/删除等管理接口仅对超级用户开放，相关测试通过 report_superuser fixture 临时提升权限。
"""

import pytest
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import global_config_loaded_from_config_yaml
from app.models.chat import Chat
from app.models.chat_history import ChatHistory
from app.models.report import Report, ReportStatus, ReportType
from app.models.user import User
from tests.app.api.v1.endpoints.conftest import integration_client


@pytest.fixture
def db_session():
    engine = create_engine(global_config_loaded_from_config_yaml.database.url)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _get_reporter_id(integration_client):
    """获取当前用户 ID 的辅助函数"""
    user_response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/users/me"
    )
    assert (
        user_response.status_code == 200
    ), f"Failed to get user info: {user_response.text}"
    user_data = user_response.json()
    assert (
        user_data.get("code") == 200
    ), f"Get user info returned error: {user_data}"
    return user_data["data"]["id"]


@pytest.fixture
def report_superuser(integration_client, db_session):
    """将当前集成测试用户临时提升为超级用户（/report 接口仅对超级用户开放）。"""
    user_response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/users/me"
    )
    assert user_response.status_code == 200, user_response.text
    user_id = user_response.json()["data"]["id"]
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    db_user.is_superuser = True
    db_session.commit()
    try:
        yield
    finally:
        db_user = db_session.query(User).filter(User.id == user_id).first()
        if db_user is not None:
            db_user.is_superuser = False
            db_session.commit()


def _ensure_user_is_not_superuser(integration_client, db_session) -> None:
    """确保当前集成测试用户不是超级用户（用于验证非管理员可调用的接口）。"""
    user_response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/users/me"
    )
    assert user_response.status_code == 200, user_response.text
    user_id = user_response.json()["data"]["id"]
    db_user = db_session.query(User).filter(User.id == user_id).first()
    assert db_user is not None
    if db_user.is_superuser:
        db_user.is_superuser = False
        db_session.commit()


def _find_report(db_session, agent_id, reporter_id):
    """查找举报记录的辅助函数"""
    return (
        db_session.query(Report)
        .filter(
            Report.target_id == agent_id,
            Report.target_type == "AGENT",
            Report.reporter_id == reporter_id,
        )
        .order_by(Report.created_at.desc())
        .first()
    )


def _find_feedback(db_session, reporter_id):
    """查找反馈记录的辅助函数"""
    return (
        db_session.query(Report)
        .filter(
            Report.reporter_id == reporter_id,
            Report.report_type == ReportType.FEEDBACK,
        )
        .order_by(Report.created_at.desc())
        .first()
    )


def _set_reporter_profile_for_detail_check(db_session, reporter_id):
    """更新举报人信息，便于断言详情接口返回完整用户信息。"""
    db_user = db_session.query(User).filter(User.id == reporter_id).first()
    assert db_user is not None
    db_user.nickname = "ReportDetailTester"
    db_user.email = "report-detail-tester@example.com"
    db_session.commit()


def _seed_chat_rounds(
    db_session,
    *,
    user_id: str,
    agent_id: str,
    chat_id: str,
    rounds: int,
    start_at: datetime,
) -> None:
    db_session.add(
        Chat(
            id=chat_id,
            user_id=user_id,
            agent_id=agent_id,
            is_active=True,
        )
    )
    session_id = uuid.uuid5(uuid.NAMESPACE_DNS, chat_id)
    current_time = start_at
    for index in range(rounds):
        db_session.add(
            ChatHistory(
                session_id=session_id,
                message={
                    "type": "human",
                    "data": {"content": f"user-{index}"},
                },
                created_at=current_time,
            )
        )
        current_time += timedelta(seconds=1)
        db_session.add(
            ChatHistory(
                session_id=session_id,
                message={
                    "type": "ai",
                    "data": {"content": f"ai-{index}"},
                },
                created_at=current_time,
            )
        )
        current_time += timedelta(seconds=1)
    db_session.commit()


def test_create_report_as_non_superuser(integration_client, db_session):
    """验证非管理员（已登录）用户可以成功提交举报。"""
    _ensure_user_is_not_superuser(integration_client, db_session)

    agent_id = integration_client.create_agent(
        name="Test Report Non-Admin Agent",
        visibility="PUBLIC",
    )
    report_payload = {
        "target_id": agent_id,
        "target_type": "AGENT",
        "reason_codes": ["SENSITIVE_CONTENT"],
        "description": "Report from non-admin user",
        "image_urls": [],
    }

    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=report_payload,
    )

    assert (
        response.status_code == 200
    ), f"Report creation failed: {response.text}"
    response_data = response.json()
    assert (
        response_data.get("code") == 200
    ), f"Report creation returned error: {response_data}"

    reporter_id = _get_reporter_id(integration_client)
    report = _find_report(db_session, agent_id, reporter_id)
    assert report is not None, "Report should be created in database"
    assert report.reason_codes == ["SENSITIVE_CONTENT"]
    assert report.description == "Report from non-admin user"


def test_create_report_with_reason_codes(
    integration_client, db_session, report_superuser
):
    """测试使用 reason_codes 创建举报（新 API）"""
    # 创建一个 agent 作为被举报的目标
    agent_id = integration_client.create_agent(
        name="Test Report Agent Codes",
        visibility="PUBLIC",
    )

    # 准备举报数据，使用新的 reason_codes API
    report_payload = {
        "target_id": agent_id,
        "target_type": "AGENT",
        "reason_codes": ["SENSITIVE_CONTENT", "MISINFORMATION"],
        "description": "Test report with reason_codes",
        "image_urls": [],
    }

    # 提交举报
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=report_payload,
    )

    # 验证响应
    assert (
        response.status_code == 200
    ), f"Report creation failed: {response.text}"

    response_data = response.json()
    assert (
        response_data.get("code") == 200
    ), f"Report creation returned error: {response_data}"
    assert (
        response_data.get("message") == "success"
    ), f"Unexpected response structure: {response_data}"

    # 获取当前用户 ID
    reporter_id = _get_reporter_id(integration_client)

    # 检查数据库内的举报记录
    report = _find_report(db_session, agent_id, reporter_id)

    assert report is not None, "Report not found in database"
    assert report.target_id == agent_id, "Report target ID mismatch"
    assert report.target_type == "AGENT", "Report target type mismatch"
    assert report.reason_codes == [
        "SENSITIVE_CONTENT",
        "MISINFORMATION",
    ], "Report reason codes mismatch"
    # 只使用 reason_codes 时，reason_ids 应该为空列表
    assert (
        report.reason_ids == []
    ), "Report reason IDs should be empty when only reason_codes provided"
    assert (
        report.description == "Test report with reason_codes"
    ), "Report description mismatch"
    assert report.image_urls == [], "Report image URLs mismatch"
    # 验证 report_type 为 None 或 REPORT（向后兼容）
    assert (
        report.report_type is None or report.report_type == ReportType.REPORT
    ), f"Report type should be None or REPORT, got {report.report_type}"


def test_create_report_with_reason_ids(
    integration_client, db_session, report_superuser
):
    """测试使用 reason_ids 创建举报（向后兼容，旧 API）"""
    # 创建一个 agent 作为被举报的目标
    agent_id = integration_client.create_agent(
        name="Test Report Agent IDs",
        visibility="PUBLIC",
    )

    # 准备举报数据，使用旧的 reason_ids API（向后兼容）
    # 注意：reason_ids 会被自动转换为 reason_codes
    report_payload = {
        "target_id": agent_id,
        "target_type": "AGENT",
        "reason_ids": [1],  # SENSITIVE_CONTENT
        # reason_codes 不提供，会从 reason_ids 自动转换
        "description": "Test report with reason_ids (backward compatibility)",
        "image_urls": [],
    }

    # 提交举报
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=report_payload,
    )

    # 验证响应
    assert (
        response.status_code == 200
    ), f"Report creation failed: {response.text}"

    response_data = response.json()
    assert (
        response_data.get("code") == 200
    ), f"Report creation returned error: {response_data}"
    assert (
        response_data.get("message") == "success"
    ), f"Unexpected response structure: {response_data}"

    # 获取当前用户 ID
    reporter_id = _get_reporter_id(integration_client)

    # 检查数据库内的举报记录
    report = _find_report(db_session, agent_id, reporter_id)

    assert report is not None, "Report not found in database"
    assert report.target_id == agent_id, "Report target ID mismatch"
    assert report.target_type == "AGENT", "Report target type mismatch"
    # reason_ids 应该被保存（向后兼容）
    assert report.reason_ids == [1], "Report reason IDs mismatch"
    # reason_codes 应该从 reason_ids 转换而来
    assert report.reason_codes == [
        "SENSITIVE_CONTENT"
    ], "Report reason codes mismatch (should be converted from reason_ids)"
    assert (
        report.description
        == "Test report with reason_ids (backward compatibility)"
    ), "Report description mismatch"
    assert report.image_urls == [], "Report image URLs mismatch"
    # 验证 report_type 为 None 或 REPORT（向后兼容）
    assert (
        report.report_type is None or report.report_type == ReportType.REPORT
    ), "Report type should be None or REPORT for legacy reports"


def test_create_feedback_with_reason_codes(
    integration_client, db_session, report_superuser
):
    """测试使用 reason_codes 创建反馈（新 API）"""
    # 准备反馈数据，使用新的 reason_codes API
    # 注意：feedback 模式下，target_id 和 target_type 可以为空字符串（Android 端的实现）
    feedback_payload = {
        "target_id": "",  # feedback 模式下为空字符串
        "target_type": "USER",  # feedback 模式下使用默认类型
        "reason_codes": ["CHAT_NOT_NATURAL", "UI_INCONVENIENT"],
        "description": "Test feedback with reason_codes",
        "image_urls": [],
        "report_type": "FEEDBACK",
    }

    # 提交反馈
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=feedback_payload,
    )

    # 验证响应
    assert (
        response.status_code == 200
    ), f"Feedback creation failed: {response.text}"

    response_data = response.json()
    assert (
        response_data.get("code") == 200
    ), f"Feedback creation returned error: {response_data}"
    assert (
        response_data.get("message") == "success"
    ), f"Unexpected response structure: {response_data}"

    # 获取当前用户 ID
    reporter_id = _get_reporter_id(integration_client)

    # 检查数据库内的反馈记录
    feedback = _find_feedback(db_session, reporter_id)

    assert feedback is not None, "Feedback not found in database"
    assert feedback.target_id == "", "Feedback target ID should be empty string"
    assert feedback.target_type == "USER", "Feedback target type mismatch"
    assert feedback.reason_codes == [
        "CHAT_NOT_NATURAL",
        "UI_INCONVENIENT",
    ], "Feedback reason codes mismatch"
    # 只使用 reason_codes 时，reason_ids 应该为空列表
    assert (
        feedback.reason_ids == []
    ), "Feedback reason IDs should be empty when only reason_codes provided"
    assert (
        feedback.description == "Test feedback with reason_codes"
    ), "Feedback description mismatch"
    assert feedback.image_urls == [], "Feedback image URLs mismatch"
    # 验证 report_type 为 FEEDBACK
    assert (
        feedback.report_type == ReportType.FEEDBACK
    ), f"Feedback report_type should be FEEDBACK, got {feedback.report_type}"
    # 验证 status 为 PENDING（默认值）
    assert (
        feedback.status == ReportStatus.PENDING
    ), f"Feedback status should be PENDING, got {feedback.status}"


def test_create_image_feedback_with_new_reason_codes(
    integration_client, db_session, report_superuser
):
    """测试图片反馈可使用新增的图片质量 reason_codes。"""
    feedback_payload = {
        "target_id": "IMAGE_FEEDBACK_deadbeef",
        "target_type": "USER",
        "reason_codes": [
            "IMAGE_LOW_QUALITY",
            "IMAGE_CONTENT_MISMATCH",
            "IMAGE_OTHER",
        ],
        "description": "[IMAGE_FEEDBACK][vote=dislike] image quality is too low",
        "image_urls": ["https://cdn.example.com/chat_images/test.png"],
        "report_type": "FEEDBACK",
    }

    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=feedback_payload,
    )
    assert (
        response.status_code == 200
    ), f"Image feedback creation failed: {response.text}"
    response_data = response.json()
    assert (
        response_data.get("code") == 200
    ), f"Unexpected response: {response_data}"

    reporter_id = _get_reporter_id(integration_client)
    feedback = _find_feedback(db_session, reporter_id)
    assert feedback is not None, "Image feedback not found in database"
    assert feedback.target_id == "IMAGE_FEEDBACK_deadbeef"
    assert feedback.target_type == "USER"
    assert feedback.reason_codes == [
        "IMAGE_LOW_QUALITY",
        "IMAGE_CONTENT_MISMATCH",
        "IMAGE_OTHER",
    ]
    assert feedback.report_type == ReportType.FEEDBACK


def test_create_feedback_with_reason_ids(
    integration_client, db_session, report_superuser
):
    """测试使用 reason_ids 创建反馈（向后兼容，旧 API）

    验证 feedback 使用 reason_ids 时，会被正确转换为 feedback 的 reason_codes。
    """
    # 准备反馈数据，使用旧的 reason_ids API（向后兼容）
    # 注意：reason_ids 会被自动转换为 reason_codes（使用 feedback 的映射）
    feedback_payload = {
        "target_id": "",  # feedback 模式下为空字符串
        "target_type": "USER",  # feedback 模式下使用默认类型
        "reason_ids": [
            1,
            5,
        ],  # 会被转换为 CHAT_NOT_NATURAL, UI_INCONVENIENT（feedback 的映射）
        # reason_codes 不提供，会从 reason_ids 自动转换
        "description": "Test feedback with reason_ids (backward compatibility)",
        "image_urls": [],
        "report_type": "FEEDBACK",
    }

    # 提交反馈
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=feedback_payload,
    )

    # 验证响应
    assert (
        response.status_code == 200
    ), f"Feedback creation failed: {response.text}"

    response_data = response.json()
    assert (
        response_data.get("code") == 200
    ), f"Feedback creation returned error: {response_data}"
    assert (
        response_data.get("message") == "success"
    ), f"Unexpected response structure: {response_data}"

    # 获取当前用户 ID
    reporter_id = _get_reporter_id(integration_client)

    # 检查数据库内的反馈记录
    feedback = _find_feedback(db_session, reporter_id)

    assert feedback is not None, "Feedback not found in database"
    assert feedback.target_id == "", "Feedback target ID should be empty string"
    assert feedback.target_type == "USER", "Feedback target type mismatch"
    # reason_ids 应该被保存（向后兼容）
    assert feedback.reason_ids == [1, 5], "Feedback reason IDs mismatch"
    # reason_codes 应该从 reason_ids 转换而来（使用 feedback 的映射）
    assert feedback.reason_codes == [
        "CHAT_NOT_NATURAL",
        "UI_INCONVENIENT",
    ], "Feedback reason codes mismatch (should be converted from reason_ids using feedback mapping)"
    assert (
        feedback.description
        == "Test feedback with reason_ids (backward compatibility)"
    ), "Feedback description mismatch"
    assert feedback.image_urls == [], "Feedback image URLs mismatch"
    # 验证 report_type 为 FEEDBACK
    assert (
        feedback.report_type == ReportType.FEEDBACK
    ), f"Feedback report_type should be FEEDBACK, got {feedback.report_type}"
    # 验证 status 为 PENDING（默认值）
    assert (
        feedback.status == ReportStatus.PENDING
    ), f"Feedback status should be PENDING, got {feedback.status}"


def test_create_feedback_with_reason_id_zero(
    integration_client, db_session, report_superuser
):
    """测试使用 reason_id 0 (OTHER) 创建反馈

    验证 feedback 使用 reason_id 0 时，会被正确转换为 "OTHER"。
    """
    # 准备反馈数据，使用 reason_id 0（OTHER）
    feedback_payload = {
        "target_id": "",
        "target_type": "USER",
        "reason_ids": [0],  # OTHER
        "description": "Test feedback with reason_id 0 (OTHER)",
        "image_urls": [],
        "report_type": "FEEDBACK",
    }

    # 提交反馈
    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=feedback_payload,
    )

    # 验证响应
    assert (
        response.status_code == 200
    ), f"Feedback creation failed: {response.text}"

    response_data = response.json()
    assert (
        response_data.get("code") == 200
    ), f"Feedback creation returned error: {response_data}"

    # 获取当前用户 ID
    reporter_id = _get_reporter_id(integration_client)

    # 检查数据库内的反馈记录
    feedback = _find_feedback(db_session, reporter_id)

    assert feedback is not None, "Feedback not found in database"
    assert feedback.reason_ids == [0], "Feedback reason IDs mismatch"
    # reason_id 0 应该被转换为 "OTHER"
    assert feedback.reason_codes == [
        "OTHER"
    ], "Feedback reason code should be OTHER for reason_id 0"
    assert (
        feedback.report_type == ReportType.FEEDBACK
    ), f"Feedback report_type should be FEEDBACK, got {feedback.report_type}"


def test_delete_report_by_reporter(
    integration_client, db_session, report_superuser
):
    """测试举报人可以删除自己提交的举报记录"""
    agent_id = integration_client.create_agent(
        name="Test Delete Report Agent",
        visibility="PUBLIC",
    )

    report_payload = {
        "target_id": agent_id,
        "target_type": "AGENT",
        "reason_codes": ["SENSITIVE_CONTENT"],
        "description": "Test report to be deleted",
        "image_urls": [],
    }

    response = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=report_payload,
    )
    assert (
        response.status_code == 200
    ), f"Report creation failed: {response.text}"
    response_data = response.json()
    assert (
        response_data.get("code") == 200
    ), f"Report creation returned error: {response_data}"

    reporter_id = _get_reporter_id(integration_client)
    report = _find_report(db_session, agent_id, reporter_id)
    assert report is not None, "Report not found in database"

    delete_resp = integration_client.client.delete(
        f"{integration_client.base_url}/api/v1/report/{report.id}"
    )
    assert (
        delete_resp.status_code == 200
    ), f"Report deletion failed: {delete_resp.text}"
    delete_data = delete_resp.json()
    assert (
        delete_data.get("code") == 200
    ), f"Report deletion returned error: {delete_data}"

    deleted = db_session.query(Report).filter(Report.id == report.id).first()
    assert deleted is None, "Report should be deleted from database"


def test_get_report_detail_includes_reporter_user_info(
    integration_client, db_session, report_superuser
):
    """验证举报详情接口返回举报人详细信息。"""
    agent_id = integration_client.create_agent(
        name="Test Report Detail With Reporter Info",
        visibility="PUBLIC",
    )
    report_payload = {
        "target_id": agent_id,
        "target_type": "AGENT",
        "reason_codes": ["SENSITIVE_CONTENT"],
        "description": "Test report detail should include reporter info",
        "image_urls": [],
    }
    create_resp = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=report_payload,
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json().get("code") == 200, create_resp.text

    reporter_id = _get_reporter_id(integration_client)
    _set_reporter_profile_for_detail_check(db_session, reporter_id)
    report = _find_report(db_session, agent_id, reporter_id)
    assert report is not None, "Report should exist before querying detail API"

    detail_resp = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/report/{report.id}"
    )
    assert detail_resp.status_code == 200, detail_resp.text
    detail_data = detail_resp.json()

    reporter_user_info = detail_data.get("reporter_user_info")
    assert reporter_user_info is not None
    assert reporter_user_info["id"] == reporter_id
    assert reporter_user_info["nickname"] == "ReportDetailTester"
    assert reporter_user_info["email"] == "report-detail-tester@example.com"
    assert reporter_user_info["created_at"] is not None


def test_list_reports_includes_reporter_user_info(
    integration_client, db_session, report_superuser
):
    """验证举报列表接口返回举报人详细信息。"""
    agent_id = integration_client.create_agent(
        name="Test Report List With Reporter Info",
        visibility="PUBLIC",
    )
    report_payload = {
        "target_id": agent_id,
        "target_type": "AGENT",
        "reason_codes": ["MISINFORMATION"],
        "description": "Test report list should include reporter info",
        "image_urls": [],
    }
    create_resp = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=report_payload,
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json().get("code") == 200, create_resp.text

    reporter_id = _get_reporter_id(integration_client)
    _set_reporter_profile_for_detail_check(db_session, reporter_id)
    report = _find_report(db_session, agent_id, reporter_id)
    assert report is not None, "Report should exist before querying list API"

    list_resp = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/report/",
        params={"skip": 0, "limit": 50, "order_by": "created_at_desc"},
    )
    assert list_resp.status_code == 200, list_resp.text
    list_data = list_resp.json()

    report_item = next(
        (item for item in list_data["items"] if item["id"] == report.id),
        None,
    )
    assert (
        report_item is not None
    ), "Expected report item to be present in report list"
    reporter_user_info = report_item.get("reporter_user_info")
    assert reporter_user_info is not None
    assert reporter_user_info["id"] == reporter_id
    assert reporter_user_info["nickname"] == "ReportDetailTester"
    assert reporter_user_info["email"] == "report-detail-tester@example.com"


def test_list_reports_filters_by_target_id(
    integration_client, db_session, report_superuser
):
    """验证举报列表支持按 target_id 过滤。"""
    target_agent_id = integration_client.create_agent(
        name="Target Agent For Target ID Filter",
        visibility="PUBLIC",
    )
    other_agent_id = integration_client.create_agent(
        name="Other Agent For Target ID Filter",
        visibility="PUBLIC",
    )

    target_payload = {
        "target_id": target_agent_id,
        "target_type": "AGENT",
        "reason_codes": ["SENSITIVE_CONTENT"],
        "description": "Report for target_id filter test",
        "image_urls": [],
    }
    other_payload = {
        "target_id": other_agent_id,
        "target_type": "AGENT",
        "reason_codes": ["MISINFORMATION"],
        "description": "Noise report for target_id filter test",
        "image_urls": [],
    }

    target_resp = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=target_payload,
    )
    assert target_resp.status_code == 200, target_resp.text
    assert target_resp.json().get("code") == 200, target_resp.text

    other_resp = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=other_payload,
    )
    assert other_resp.status_code == 200, other_resp.text
    assert other_resp.json().get("code") == 200, other_resp.text

    list_resp = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/report/",
        params={
            "target_id": target_agent_id,
            "skip": 0,
            "limit": 50,
            "order_by": "created_at_desc",
        },
    )
    assert list_resp.status_code == 200, list_resp.text
    list_data = list_resp.json()
    assert len(list_data["items"]) >= 1
    assert all(
        item["target_id"] == target_agent_id for item in list_data["items"]
    )


def test_update_report_github_issue_success(
    integration_client, db_session, report_superuser
):
    """测试管理员可以为举报记录绑定 GitHub issue 链接。"""
    agent_id = integration_client.create_agent(
        name="Test Github Issue Agent",
        visibility="PUBLIC",
    )
    report_payload = {
        "target_id": agent_id,
        "target_type": "AGENT",
        "reason_codes": ["SENSITIVE_CONTENT"],
        "description": "Test report for github issue binding",
        "image_urls": [],
    }
    create_resp = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=report_payload,
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json().get("code") == 200, create_resp.text

    reporter_id = _get_reporter_id(integration_client)
    report = _find_report(db_session, agent_id, reporter_id)
    assert (
        report is not None
    ), "Report should be created before updating github issue"

    github_issue_url = "https://github.com/example-org/example-repo/issues/123"
    update_resp = integration_client.client.put(
        f"{integration_client.base_url}/api/v1/report/{report.id}/github-issue",
        json={"github_issue": github_issue_url},
    )
    assert update_resp.status_code == 200, update_resp.text
    update_data = update_resp.json()
    assert update_data["id"] == report.id
    assert update_data["github_issue"] == github_issue_url

    db_session.expire_all()
    updated_report = (
        db_session.query(Report).filter(Report.id == report.id).first()
    )
    assert updated_report is not None
    assert updated_report.github_issue == github_issue_url


def test_update_report_github_issue_invalid_url(
    integration_client, db_session, report_superuser
):
    """测试不合法的 GitHub issue URL 会被拒绝。"""
    agent_id = integration_client.create_agent(
        name="Test Github Invalid URL",
        visibility="PUBLIC",
    )
    report_payload = {
        "target_id": agent_id,
        "target_type": "AGENT",
        "reason_codes": ["MISINFORMATION"],
        "description": "Test invalid github issue URL",
        "image_urls": [],
    }
    create_resp = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json=report_payload,
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json().get("code") == 200, create_resp.text

    reporter_id = _get_reporter_id(integration_client)
    report = _find_report(db_session, agent_id, reporter_id)
    assert report is not None, "Report should be created before validation test"

    update_resp = integration_client.client.put(
        f"{integration_client.base_url}/api/v1/report/{report.id}/github-issue",
        json={"github_issue": "https://example.com/not-github-issue"},
    )
    assert update_resp.status_code == 400, update_resp.text
    assert "Invalid GitHub issue URL format" in update_resp.text

    db_session.expire_all()
    unchanged_report = (
        db_session.query(Report).filter(Report.id == report.id).first()
    )
    assert unchanged_report is not None
    assert unchanged_report.github_issue is None


def test_get_report_conversation_groups(
    integration_client, db_session, report_superuser
):
    """验证举报详情可返回举报人的 user_id:agent_id 聊天分组列表。"""
    reporter_id = _get_reporter_id(integration_client)
    target_agent_id = integration_client.create_agent(
        name="Report Conversation Target Agent",
        visibility="PUBLIC",
    )
    another_agent_id = integration_client.create_agent(
        name="Report Conversation Another Agent",
        visibility="PUBLIC",
    )

    now = datetime.now(timezone.utc)
    _seed_chat_rounds(
        db_session,
        user_id=reporter_id,
        agent_id=target_agent_id,
        chat_id=f"chat-{uuid.uuid4().hex[:12]}",
        rounds=5,
        start_at=now - timedelta(hours=2),
    )
    _seed_chat_rounds(
        db_session,
        user_id=reporter_id,
        agent_id=another_agent_id,
        chat_id=f"chat-{uuid.uuid4().hex[:12]}",
        rounds=3,
        start_at=now - timedelta(hours=1),
    )

    create_resp = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json={
            "target_id": target_agent_id,
            "target_type": "AGENT",
            "reason_codes": ["MISINFORMATION"],
            "description": "Seeded report for conversation groups",
            "image_urls": [],
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json().get("code") == 200, create_resp.text
    report = _find_report(db_session, target_agent_id, reporter_id)
    assert report is not None

    response = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/report/{report.id}/conversation-groups"
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total"] == 2

    grouped_by_agent = {item["agent_id"]: item for item in payload["items"]}
    assert grouped_by_agent[target_agent_id]["user_id"] == reporter_id
    assert grouped_by_agent[target_agent_id]["total_rounds"] == 5
    assert grouped_by_agent[another_agent_id]["total_rounds"] == 3


def test_get_report_conversation_messages_round_pagination(
    integration_client, db_session, report_superuser
):
    """验证聊天明细按轮次分页：每页 20 轮，第一页最新，下一页更旧。"""
    reporter_id = _get_reporter_id(integration_client)
    target_agent_id = integration_client.create_agent(
        name="Report Conversation Paging Agent",
        visibility="PUBLIC",
    )
    chat_id = f"chat-{uuid.uuid4().hex[:12]}"
    _seed_chat_rounds(
        db_session,
        user_id=reporter_id,
        agent_id=target_agent_id,
        chat_id=chat_id,
        rounds=25,
        start_at=datetime.now(timezone.utc) - timedelta(hours=3),
    )

    create_resp = integration_client.client.post(
        f"{integration_client.base_url}/api/v1/report/",
        json={
            "target_id": target_agent_id,
            "target_type": "AGENT",
            "reason_codes": ["SENSITIVE_CONTENT"],
            "description": "Seeded report for conversation paging",
            "image_urls": [],
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    assert create_resp.json().get("code") == 200, create_resp.text
    report = _find_report(db_session, target_agent_id, reporter_id)
    assert report is not None

    page_one_resp = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/report/{report.id}/conversation-messages",
        params={
            "user_id": reporter_id,
            "agent_id": target_agent_id,
            "page": 1,
            "size": 20,
        },
    )
    assert page_one_resp.status_code == 200, page_one_resp.text
    page_one = page_one_resp.json()
    assert page_one["total_rounds"] == 25
    assert page_one["has_more"] is True
    assert len(page_one["messages"]) == 40
    assert page_one["messages"][0]["content"] == "ai-24"
    assert page_one["messages"][1]["content"] == "user-24"

    page_two_resp = integration_client.client.get(
        f"{integration_client.base_url}/api/v1/report/{report.id}/conversation-messages",
        params={
            "user_id": reporter_id,
            "agent_id": target_agent_id,
            "page": 2,
            "size": 20,
        },
    )
    assert page_two_resp.status_code == 200, page_two_resp.text
    page_two = page_two_resp.json()
    assert page_two["has_more"] is False
    assert len(page_two["messages"]) == 10
    assert page_two["messages"][-1]["content"] == "user-0"
