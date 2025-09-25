package com.ai.inty

/** 项目内的常量 定义 */
class Constant {
    companion object {
        // This refers to the production backend endpoint.
        // The domain & DNS is on namecheap, pointing to the public IP of the dev instance.
        // Nginx is running on the dev instance to proxy to different backend instances on different
        // ports.
        const val USER_HOST = "app.inty.cc"

        // This refers to the shared development backend endpoint.
        // This is the backend endpoint for the debug build (default build type).
        const val USER_HOST_DEV = "dev.inty.sxwl.ai"

        // This refers to the local backend endpoint that can be accessed
        // an Android emulator. Used for local development.
        // https://stackoverflow.com/a/6310592
        const val USER_HOST_LOCAL = "localhost:8000"

        const val SYS_NOTIFICATION_ID = "SYS_NOTIFICATION_ID_888"

        const val ROUTE_HOME_URL = "http://inty.ai/"
        const val ROUTE_MAIN = "${ROUTE_HOME_URL}main"
        const val ROUTE_CHAT = "${ROUTE_HOME_URL}chat"
        const val ROUTE_SETTING = "${ROUTE_HOME_URL}setting"
        const val ROUTE_SETTING_MY = "${ROUTE_HOME_URL}setting/my"
        const val ROUTE_AGENT_INFO = "${ROUTE_HOME_URL}agent/info"
        const val ROUTE_CREATE_ROLE = "${ROUTE_HOME_URL}create/role"
        const val ROUTE_AVATAR_GENERATE = "${ROUTE_HOME_URL}avatar/generate"
        const val ROUTE_REG_INFO = "${ROUTE_HOME_URL}reg/info"
        const val ROUTE_LOGIN = "${ROUTE_HOME_URL}login"
        const val ROUTE_REPORT = "${ROUTE_HOME_URL}report"
        const val ROUTE_VIP_CENTER = "${ROUTE_HOME_URL}vip_center"
        const val ROUTE_SUBSCRIPTION_MANAGEMENT = "${ROUTE_HOME_URL}subscription_management"

        const val ACTION_USER_PROFILE_CHANGED = "ACTION_USER_PROFILE_CHANGED"
    }
}
