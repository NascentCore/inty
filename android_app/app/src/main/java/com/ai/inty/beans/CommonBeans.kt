package com.ai.inty.beans

import androidx.annotation.Keep
import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass


@JsonClass(generateAdapter = true)
data class ReportItem(
    val code: String = "",
    val description: String = "",
    val id: Int = 0
)


@JsonClass(generateAdapter = true)
data class ReportReq(
    val description: String = "",
    @Json(name = "image_urls")
    val imageUrls: List<String?> = listOf(),
    @Json(name = "reason_ids")
    val reasonIds: List<Int> = listOf(),
    @Json(name = "target_id")
    val targetId: String,
    @Json(name = "target_type")
    val targetType: String = "USER"
)

@JsonClass(generateAdapter = true)
data class ReportResponse(
    val code: Int = 0,
    val message: String = "",
    val data: String? = null
)

/**
 * 检查App版本号，判断更新与否，强制更新与否的接口返回
 */
@Keep
data class AppVersionRsp(
    val code: Int? = null,
    val data: AppVersionData? = null,
    val message: String? = null
) {

    @Keep
    data class AppVersionData(
        val changelog: String? = null,//更新变动文案
        val current_version: String? = null,//本地app的版本
        val download_url: String? = null,//更新app跳转的url，这里是google play的链接
        val error: String? = null,//错误信息
        val force_update: Boolean = false,//是否强制更新
        val latest_version: String? = null,//最新的版本
        val latest_version_code: Int? = null,//最新的版本号
        val message: String? = null,//描述文案
        val minimum_version: String? = null,
        val update_required: Boolean = false//是否有新版，需要更新
    )
}
