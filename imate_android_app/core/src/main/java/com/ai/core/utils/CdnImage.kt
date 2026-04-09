package com.ai.core.utils

/**
 * 获取 CDN 裁剪图片的 url。
 *
 * 规则与 android_app 保持一致：对于 images.sxwl.dev 的 inty-static 资源，通过 Cloudflare
 * `/cdn-cgi/image/width=...,quality=.../` 进行按宽度裁剪与质量压缩。
 */
fun getCdnImageUrl(originUrl: String?, width: Int = 1080, quality: Int = 75): String? {
    if (originUrl.isNullOrBlank()) return null
    return when {
        originUrl.contains("/cdn-cgi/image/") -> originUrl
        // Google GCS 原图，这个 url 不支持拼接 cdn 访问
        originUrl.startsWith("https://storage.googleapis.com") -> originUrl
        originUrl.contains("/inty-static", ignoreCase = true) -> {
            // 有这样的：
            // https://images.sxwl.dev/inty-static//inty-static/agents/.../avatar.jpeg
            val regex = Regex("/inty-static", RegexOption.IGNORE_CASE)
            originUrl.replaceFirst(
                regex,
                "/cdn-cgi/image/width=$width,quality=$quality/inty-static",
            )
        }
        else -> originUrl
    }
}

