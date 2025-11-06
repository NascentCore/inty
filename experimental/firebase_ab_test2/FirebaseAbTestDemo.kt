package experimental.firebase_ab_test2

import android.content.Context
import android.os.Bundle
import android.util.Log
import com.google.firebase.FirebaseApp
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.ktx.Firebase
import com.google.firebase.remoteconfig.ktx.remoteConfig
import com.google.firebase.remoteconfig.ktx.remoteConfigSettings
import java.util.UUID
import kotlin.random.Random

object FirebaseAbTestDemo {
    private const val TAG = "FirebaseAbTestDemo"
    private const val REMOTE_CONFIG_VARIANT_PARAM = "profile_variant"
    private const val REMOTE_CONFIG_THEME_COLOR_PARAM = "profile_theme_color"
    private const val DEFAULT_VARIANT = "control"
    private const val DEFAULT_THEME_COLOR = "#FF4081"

    fun initialize(context: Context, onConfigReady: (RemoteConfigResult) -> Unit) {
        if (FirebaseApp.getApps(context).isEmpty()) {
            FirebaseApp.initializeApp(context)
        }

        val analytics = Firebase.analytics
        val remoteConfig = Firebase.remoteConfig

        remoteConfig.setConfigSettingsAsync(
            remoteConfigSettings {
                minimumFetchIntervalInSeconds = 0
            }
        )

        remoteConfig.setDefaultsAsync(
            mapOf(
                REMOTE_CONFIG_VARIANT_PARAM to DEFAULT_VARIANT,
                REMOTE_CONFIG_THEME_COLOR_PARAM to DEFAULT_THEME_COLOR
            )
        )

        val profile = UserProfile.random()
        profile.registerWithFirebase(analytics)
        Log.d(TAG, "Generated profile: $profile")

        remoteConfig.fetchAndActivate()
            .addOnSuccessListener {
                onConfigReady(
                    RemoteConfigResult(
                        variant = remoteConfig.getString(REMOTE_CONFIG_VARIANT_PARAM).ifBlank { DEFAULT_VARIANT },
                        themeColor = remoteConfig.getString(REMOTE_CONFIG_THEME_COLOR_PARAM).ifBlank { DEFAULT_THEME_COLOR }
                    )
                )
            }
            .addOnFailureListener { error ->
                Log.w(TAG, "Remote Config fetch failed", error)
                onConfigReady(RemoteConfigResult())
            }
    }

    data class RemoteConfigResult(
        val variant: String = DEFAULT_VARIANT,
        val themeColor: String = DEFAULT_THEME_COLOR
    )
}

private const val USER_PROPERTY_GENDER = "profile_gender"
private const val USER_PROPERTY_AGE = "profile_age_bracket"
private const val USER_PROPERTY_SEGMENT = "profile_segment"

private data class UserProfile(
    val userId: String,
    val gender: Gender,
    val ageBracket: AgeBracket,
    val loyaltyTier: LoyaltyTier
) {
    fun registerWithFirebase(analytics: FirebaseAnalytics) {
        analytics.setUserId(userId)
        analytics.setUserProperty(USER_PROPERTY_GENDER, gender.value)
        analytics.setUserProperty(USER_PROPERTY_AGE, ageBracket.value)
        analytics.setUserProperty(USER_PROPERTY_SEGMENT, loyaltyTier.value)

        val payload = Bundle().apply {
            putString(USER_PROPERTY_GENDER, gender.value)
            putString(USER_PROPERTY_AGE, ageBracket.value)
            putString(USER_PROPERTY_SEGMENT, loyaltyTier.value)
        }

        analytics.logEvent("profile_generated", payload)
    }

    companion object {
        private val random = Random(System.currentTimeMillis())

        fun random(): UserProfile = UserProfile(
            userId = UUID.randomUUID().toString(),
            gender = Gender.entries.random(random),
            ageBracket = AgeBracket.entries.random(random),
            loyaltyTier = LoyaltyTier.entries.random(random)
        )
    }
}

private enum class Gender(val value: String) {
    FEMALE("female"),
    MALE("male"),
    NON_BINARY("non_binary")
}

private enum class AgeBracket(val value: String) {
    AGE_18_24("18_24"),
    AGE_25_34("25_34"),
    AGE_35_44("35_44"),
    AGE_45_PLUS("45_plus")
}

private enum class LoyaltyTier(val value: String) {
    FREE("free"),
    PLUS("plus"),
    PREMIUM("premium")
}
