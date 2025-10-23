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

    }
}
