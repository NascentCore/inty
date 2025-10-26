package ai.sxwl.android.data.http.config

/** 项目内部的常量定义 */
class Constant {
    companion object {
// 这是指 prduction 端点。
// 域名和DNS位于namecheap上，指向开发实例的公共IP。
// Nginx 在 dev 实例上运行以 proxy 到不同的云端实例
// 端口。
        const val USER_HOST = "app.inty.cc"
// 这是指共享开发端点。
// 这是调试构建（默认构建类型）的端点。
        const val USER_HOST_DEV = "dev.inty.sxwl.ai"
// 这是指可以访问的本地端点
// 一个 Android 模拟器。用于本地开发。
// https://stackoverflow.com/a/6310592
        const val USER_HOST_LOCAL = "localhost:8000"

        const val SYS_NOTIFICATION_ID = "SYS_NOTIFICATION_ID_888"

    }
}
