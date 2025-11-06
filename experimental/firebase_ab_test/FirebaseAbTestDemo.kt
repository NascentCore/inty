@file:Suppress("TooManyFunctions")

package experimental.firebase_ab_test

import android.content.Context
import android.os.Bundle
import android.util.Log
import com.google.firebase.FirebaseApp
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.installations.FirebaseInstallations
import com.google.firebase.ktx.Firebase
import com.google.firebase.remoteconfig.ktx.remoteConfig
import com.google.firebase.remoteconfig.ktx.remoteConfigSettings
import java.util.UUID
import java.util.concurrent.CopyOnWriteArraySet
import kotlin.random.Random

object FirebaseAbTestDemo {
    private const val TAG = "FirebaseAbTestDemo"
    private const val REMOTE_CONFIG_VARIANT_PARAM = "profile_variant"
    private const val REMOTE_CONFIG_THEME_COLOR_PARAM = "profile_theme_color"
    private const val DEFAULT_VARIANT = "control"
    private const val DEFAULT_THEME_COLOR = "#FF4081"
    private const val DEVELOPMENT_FETCH_INTERVAL_SECONDS = 0L

    private val listeners = CopyOnWriteArraySet<(RemoteConfigSnapshot) -> Unit>()
    private var latestSnapshot: RemoteConfigSnapshot = RemoteConfigSnapshot()
    private var initialized = false

    fun initialize(context: Context) {
        if (initialized) {
            Log.d(TAG, "Already initialized, dispatch cached snapshot.")
            dispatchSnapshot(latestSnapshot)
            return
        }

        if (FirebaseApp.getApps(context).isEmpty()) {
            FirebaseApp.initializeApp(context)
        }

        val analytics = Firebase.analytics
        val remoteConfig = Firebase.remoteConfig

        remoteConfig.setConfigSettingsAsync(
            remoteConfigSettings {
                minimumFetchIntervalInSeconds = DEVELOPMENT_FETCH_INTERVAL_SECONDS
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

        FirebaseInstallations.getInstance().id
            .addOnSuccessListener { installationId ->
                Log.d(TAG, "Firebase Installation ID: $installationId")
            }
            .addOnFailureListener { error ->
                Log.w(TAG, "Failed to obtain installation id", error)
            }

        remoteConfig.fetchAndActivate()
            .addOnSuccessListener { activated ->
                if (activated) {
                    Log.d(TAG, "Remote Config fetched and activated.")
                } else {
                    Log.d(TAG, "Remote Config fetched, values already active.")
                }

                val snapshot = RemoteConfigSnapshot(
                    variant = remoteConfig.getString(REMOTE_CONFIG_VARIANT_PARAM).ifBlank { DEFAULT_VARIANT },
                    themeColor = remoteConfig.getString(REMOTE_CONFIG_THEME_COLOR_PARAM).ifBlank { DEFAULT_THEME_COLOR }
                )

                latestSnapshot = snapshot
                dispatchSnapshot(snapshot)
            }
            .addOnFailureListener { error ->
                Log.w(TAG, "Remote Config fetch failed", error)
                dispatchSnapshot(latestSnapshot)
            }

        initialized = true
    }

    fun observeFeatureFlag(listener: (RemoteConfigSnapshot) -> Unit) {
        listeners.add(listener)
        runCatching { listener(latestSnapshot) }.onFailure { error ->
            Log.w(TAG, "Remote Config listener threw on initial dispatch", error)
        }
    }

    fun removeObserver(listener: (RemoteConfigSnapshot) -> Unit) {
        listeners.remove(listener)
    }

    fun currentSnapshot(): RemoteConfigSnapshot = latestSnapshot

    private fun dispatchSnapshot(snapshot: RemoteConfigSnapshot) {
        listeners.forEach { callback ->
            runCatching { callback(snapshot) }.onFailure { error ->
                Log.w(TAG, "Remote Config listener threw on update", error)
            }
        }
    }

    data class RemoteConfigSnapshot(
        val variant: String = DEFAULT_VARIANT,
        val themeColor: String = DEFAULT_THEME_COLOR
    ) {
        override fun toString(): String = "RemoteConfigSnapshot(variant=$variant, themeColor=$themeColor)"
    }
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
        analytics.setUserProperty(USER_PROPERTY_GENDER, gender.propertyValue)
        analytics.setUserProperty(USER_PROPERTY_AGE, ageBracket.propertyValue)
        analytics.setUserProperty(USER_PROPERTY_SEGMENT, loyaltyTier.propertyValue)

        val eventPayload = Bundle().apply {
            putString(USER_PROPERTY_GENDER, gender.propertyValue)
            putString(USER_PROPERTY_AGE, ageBracket.propertyValue)
            putString(USER_PROPERTY_SEGMENT, loyaltyTier.propertyValue)
        }

        analytics.logEvent("profile_generated", eventPayload)
    }

    companion object {
        private val random = Random(System.currentTimeMillis())

        fun random(): UserProfile {
            val userId = UUID.randomUUID().toString()
            val gender = Gender.entries.random(random)
            val age = AgeBracket.entries.random(random)
            val tier = LoyaltyTier.entries.random(random)

            return UserProfile(
                userId = userId,
                gender = gender,
                ageBracket = age,
                loyaltyTier = tier
            )
        }
    }
}

private enum class Gender(val propertyValue: String) {
    FEMALE("female"),
    MALE("male"),
    NON_BINARY("non_binary")
}

private enum class AgeBracket(val propertyValue: String) {
    AGE_18_24("18_24"),
    AGE_25_34("25_34"),
    AGE_35_44("35_44"),
    AGE_45_PLUS("45_plus")
}

private enum class LoyaltyTier(val propertyValue: String) {
    FREE("free"),
    PLUS("plus"),
    PREMIUM("premium")
}
