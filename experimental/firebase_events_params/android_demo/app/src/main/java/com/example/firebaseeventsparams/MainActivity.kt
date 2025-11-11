package com.example.firebaseeventsparams

import android.os.Bundle
import androidx.appcompat.app.AppCompatActivity
import androidx.core.os.bundleOf
import com.example.firebaseeventsparams.databinding.ActivityMainBinding
import com.google.firebase.analytics.FirebaseAnalytics
import com.google.firebase.analytics.ktx.analytics
import com.google.firebase.ktx.Firebase

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var firebaseAnalytics: FirebaseAnalytics
    private var clickCount: Int = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        firebaseAnalytics = Firebase.analytics

        binding.eventParamsText.text = getString(R.string.event_result_placeholder)
        binding.sendEventButton.setOnClickListener {
            val params = buildDemoParams()
            firebaseAnalytics.logEvent(EVENT_NAME, params)
            binding.eventParamsText.text = formatParamsForDisplay(params)
        }
    }

    private fun buildDemoParams(): Bundle {
        clickCount += 1
        val timestamp = System.currentTimeMillis()
        return bundleOf(
            "button_label" to "send_event_button",
            "screen_name" to "main_activity",
            "is_test_device" to true,
            "click_index" to clickCount,
            "clicked_at_ms" to timestamp
        )
    }

    private fun formatParamsForDisplay(params: Bundle): String {
        val lines = params.keySet().sorted().map { key ->
            val value = params.get(key)
            "$key = $value"
        }
        return lines.joinToString(separator = "\n")
    }

    companion object {
        private const val EVENT_NAME = "button_clicked"
    }
}
