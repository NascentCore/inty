package com.architecture.httplib.beans

import com.squareup.moshi.JsonClass


/**
 * 不需要，不需要
 * Alt + K 能自动生成代码
 *
 */
@JsonClass(generateAdapter = true)
data class FakerBaseResponse(
    val code: Int,
    val `data`: List<Any>,
    val status: String,
    val total: Int
)