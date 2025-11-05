package com.inty.experimental.firebase

import android.app.Application
import android.graphics.Color
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.google.firebase.FirebaseApp
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.analytics.ktx.logEvent
import com.google.firebase.ktx.Firebase
import com.google.firebase.remoteconfig.FirebaseRemoteConfig
import com.google.firebase.remoteconfig.ktx.remoteConfig
import com.google.firebase.remoteconfig.ktx.remoteConfigSettings

/**
 * 在 Application 层初始化 Remote Config，并提供默认值。
 */
fun initializeRemoteConfig(application: Application) {
    FirebaseApp.initializeApp(application)

    val remoteConfig = Firebase.remoteConfig
    val settings = remoteConfigSettings {
        minimumFetchIntervalInSeconds = 3600
    }
    remoteConfig.setConfigSettingsAsync(settings)
    remoteConfig.setDefaultsAsync(
        mapOf(
            PARAM_NEW_FEATURE_ENABLED to false,
            PARAM_CTA_BUTTON_COLOR to DEFAULT_CTA_COLOR,
        ),
    )

    remoteConfig.fetchAndActivate()
        .addOnSuccessListener { Firebase.analytics.logEvent(EVENT_AB_FETCH_SUCCESS, null) }
        .addOnFailureListener { Firebase.analytics.logEvent(EVENT_AB_FETCH_FAIL, null) }
}

/**
 * 示例 Activity：根据 Remote Config 参数切换 UI，并记录曝光/点击事件。
 */
abstract class FirebaseAbTestActivity : ComponentActivity() {

    private val remoteConfig: FirebaseRemoteConfig by lazy { Firebase.remoteConfig }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val featureEnabled = remoteConfig.getBoolean(PARAM_NEW_FEATURE_ENABLED)
        val buttonColor = remoteConfig.getString(PARAM_CTA_BUTTON_COLOR)

        Firebase.analytics.logEvent(EVENT_AB_VARIANT_EXPOSED) {
            param(PARAM_NEW_FEATURE_ENABLED, featureEnabled.toString())
            param(PARAM_CTA_BUTTON_COLOR, buttonColor)
        }

        setContent {
            MaterialTheme {
                AbTestScreen(
                    featureEnabled = featureEnabled,
                    buttonColor = buttonColor,
                    onCtaClick = {
                        Firebase.analytics.logEvent(EVENT_CTA_CLICKED) {
                            param(PARAM_NEW_FEATURE_ENABLED, featureEnabled.toString())
                            param(PARAM_CTA_BUTTON_COLOR, buttonColor)
                        }
                    },
                )
            }
        }
    }
}

@Composable
private fun AbTestScreen(
    featureEnabled: Boolean,
    buttonColor: String,
    onCtaClick: () -> Unit,
) {
    val colorInt = runCatching { Color.parseColor(buttonColor) }.getOrDefault(Color.parseColor(DEFAULT_CTA_COLOR))

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        if (featureEnabled) {
            Text(text = "实验功能已开启 🎉")
            Spacer(modifier = Modifier.height(16.dp))
        }
        Button(
            onClick = onCtaClick,
            colors = ButtonDefaults.buttonColors(containerColor = androidx.compose.ui.graphics.Color(colorInt)),
        ) {
            Text(text = "开始体验")
        }
    }
}

private const val PARAM_NEW_FEATURE_ENABLED = "new_feature_enabled"
private const val PARAM_CTA_BUTTON_COLOR = "cta_button_color"
private const val DEFAULT_CTA_COLOR = "#FF6F61"

private const val EVENT_AB_FETCH_SUCCESS = "ab_fetch_success"
private const val EVENT_AB_FETCH_FAIL = "ab_fetch_fail"
private const val EVENT_AB_VARIANT_EXPOSED = "ab_variant_exposed"
private const val EVENT_CTA_CLICKED = "cta_clicked"
