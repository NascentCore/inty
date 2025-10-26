from fastapi import APIRouter

from app.api.v1.endpoints import (
    agents,
    auth,
    chat,
    chats,
    evaluation,
    images,
    notification,
    report,
    settings,
    subscription,
    text_to_speech,
    users,
    version,
)
from app.core.config import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)

api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(users.router, tags=["users"])
# TODO：了解当前的实现，仅调用@GET("/api/v1/notifications/")
# 当前的实现也可能不安全，因为它将 api 暴露给互联网。
#相反，我们应该有一个内部服务来将主动消息发布到firebase，
# 并让firebase将消息传播到应用程序。内部服务应受Token pr保护。
#TODO：弄清楚我们是否只能相信firebase来群体消息？
api_router.include_router(
    notification.router,
    tags=["notification"],
)

api_router.include_router(report.router, tags=["report"])
api_router.include_router(agents.router, tags=["agents", "characters"])
api_router.include_router(chats.router, tags=["chats"])
api_router.include_router(chat.router, tags=["chat"])
api_router.include_router(images.router, tags=["images", "resources"])
api_router.include_router(settings.router, tags=["settings"])
# TODO：考虑删除 /resources 端点。
# api_路由器。include_router(资源。路由器，标签=[“资源”]）

api_router.include_router(subscription.router, tags=["subscription"])
# TODO：考虑删除 /admin 端点，当前实现未使用。
# 将 admin api 暴露到互联网也是非常危险的。
# 相反，我们应该有一个内部服务来管理控制台设置。
# api_router.include_router(admin.路由器，标签=[“管理员”]）
# TODO：考虑删除/评估端点。
# 这用于评估AI角色，不是应用程序运行时的一部分。
#正好，我们应该有一个内部服务来评估AI角色。
# 现在仍然保留端点，因为它用于评估 AI 角色。
api_router.include_router(
    evaluation.router,
    tags=["evaluation"],
    include_in_schema=False,
)
api_router.include_router(version.router, tags=["version"])
api_router.include_router(text_to_speech.router, tags=["text_to_speech"])
