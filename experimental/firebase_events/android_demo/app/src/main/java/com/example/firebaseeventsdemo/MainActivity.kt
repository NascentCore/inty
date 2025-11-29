package com.example.firebaseeventsdemo

// CREATED_BY_AGENT

import android.os.Bundle
import android.widget.Button
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.example.firebaseeventsdemo.analytics.FirebaseAnalyticsLogger
import com.google.firebase.FirebaseApp
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.ktx.Firebase

class MainActivity : AppCompatActivity() {

    private lateinit var analyticsLogger: FirebaseAnalyticsLogger

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        FirebaseApp.initializeApp(this)
        analyticsLogger = FirebaseAnalyticsLogger(Firebase.analytics, BuildConfig.VERSION_NAME)
        analyticsLogger.initUserProperties(userTier = "free", preferredCharacter = "nora")

        bindUi()
    }

    private fun bindUi() {
        findViewById<Button>(R.id.btn_tutorial_begin).setOnClickListener {
            analyticsLogger.logTutorialBegin(level = 1, screen = "TutorialActivity")
            shortToast(R.string.toast_tutorial_begin)
        }

        findViewById<Button>(R.id.btn_level_up).setOnClickListener {
            analyticsLogger.logLevelUp(level = 7, characterId = "char_arisa", timeSpentMs = 480000L)
            shortToast(R.string.toast_level_up)
        }

        findViewById<Button>(R.id.btn_sign_up).setOnClickListener {
            analyticsLogger.logSignUp(method = "google", tier = "premium_trial")
            shortToast(R.string.toast_sign_up)
        }

        findViewById<Button>(R.id.btn_purchase).setOnClickListener {
            analyticsLogger.logInAppPurchase(itemId = "gem_pack_large", value = 14.99, currency = "USD")
            shortToast(R.string.toast_purchase)
        }
    }

    private fun shortToast(messageRes: Int) {
        Toast.makeText(this, messageRes, Toast.LENGTH_SHORT).show()
    }
}
