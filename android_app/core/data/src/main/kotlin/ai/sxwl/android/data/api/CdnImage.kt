package ai.sxwl.android.data.api

/**
 * 获取cdn裁剪图片的url
 *
 * 使用cdn自动裁剪图片的示例，原图url是
 * https://images.sxwl.dev/inty-static/backgrounds/user-01JWZ34Y4D1C92GD86A5R6EWYJ/b4cb39bfe2fc4a92aec3bd406cc2ebaa/1758095758195/sample_0.jpg
 * 拼接/cdn-cgi/image/quality=75/后
 * https://images.sxwl.dev/cdn-cgi/image/quality=75/inty-static/backgrounds/user-01JWZ34Y4D1C92GD86A5R6EWYJ/b4cb39bfe2fc4a92aec3bd406cc2ebaa/1758095758195/sample_0.jpg
 * 也可以是/cdn-cgi/image/width=720,quality=75,format=webp/这样（目前webp转化不生效）
 *
 * @param originUrl 原始图片url
 * @param width 需要的宽度
 * @param quality 需要的图片质量 默认75%的原图质量
 * @return 业务cdn处理后的url，也可能null，也可能不处理
 */
fun getCdnImageUrl(originUrl: String?, width: Int = 1080, quality: Int = 75): String? {
    if (originUrl.isNullOrBlank()) return null
    return when {
        originUrl.contains("/cdn-cgi/image/") -> originUrl
        // google gsc原图，这个url不支持拼接cdn访问
        originUrl.startsWith("https://storage.googleapis.com") -> originUrl

        originUrl.contains("/inty-static", ignoreCase = true) -> {
            // 有这样的
            // https://images.sxwl.dev/inty-static//inty-static/agents/a9d14f3d-8306-45cd-9d23-200722f94e73/avatar-3ac67f42c36a4d9b8f6935bee20b94b1.jpeg
            val regex = Regex("/inty-static", RegexOption.IGNORE_CASE)
            originUrl.replaceFirst(
                regex,
                "/cdn-cgi/image/width=$width,quality=$quality/inty-static",
            )
        }

        else -> originUrl
    }
}
