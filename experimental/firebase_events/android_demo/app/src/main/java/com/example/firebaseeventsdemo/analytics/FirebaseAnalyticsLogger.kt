package com.example.firebaseeventsdemo.analytics

// CREATED_BY_AGENT

import android.os.Bundle
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.ktx.logEvent

class FirebaseAnalyticsLogger(
    private val analytics: FirebaseAnalytics,
    private val appVersion: String
) {

    fun initUserProperties(userTier: String, preferredCharacter: String) {
        analytics.setUserProperty("app_version", appVersion)
        analytics.setUserProperty("user_tier", userTier)
        analytics.setUserProperty("favorite_character", preferredCharacter)
    }

    fun logTutorialBegin(level: Int, screen: String) {
        analytics.logEvent(FirebaseAnalytics.Event.TUTORIAL_BEGIN) {
            param(FirebaseAnalytics.Param.LEVEL, level.toLong())
            param(FirebaseAnalytics.Param.SCREEN_CLASS, screen)
            param("engagement_time_msec", 12000L)
        }
    }

    fun logLevelUp(level: Int, characterId: String, timeSpentMs: Long) {
        analytics.logEvent(FirebaseAnalytics.Event.LEVEL_UP) {
            param(FirebaseAnalytics.Param.LEVEL, level.toLong())
            param("character_id", characterId)
            param("time_spent_ms", timeSpentMs)
            param(FirebaseAnalytics.Param.SCORE, (level * 120).toLong())
        }
    }

    fun logSignUp(method: String, tier: String) {
        analytics.logEvent(FirebaseAnalytics.Event.SIGN_UP) {
            param(FirebaseAnalytics.Param.METHOD, method)
            param("user_tier", tier)
            param("geo_hint", "US")
        }
    }

    fun logInAppPurchase(itemId: String, value: Double, currency: String) {
        analytics.logEvent(FirebaseAnalytics.Event.PURCHASE) {
            param(FirebaseAnalytics.Param.ITEM_ID, itemId)
            param(FirebaseAnalytics.Param.VALUE, value)
            param(FirebaseAnalytics.Param.CURRENCY, currency)
        }
    }

    fun logCustomEvent(name: String, params: Bundle) {
        analytics.logEvent(name, params)
    }
}
