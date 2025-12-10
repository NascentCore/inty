package com.ai.intellimate.settings

import com.ai.intellimate.BuildConfig

const val GOOGLE_PLAY_APP_URL_PREFIX = "https://play.google.com/store/apps/details?id="

fun playStoreUrl(): String {
    val appId = BuildConfig.APPLICATION_ID
    return "$GOOGLE_PLAY_APP_URL_PREFIX$appId"
}
