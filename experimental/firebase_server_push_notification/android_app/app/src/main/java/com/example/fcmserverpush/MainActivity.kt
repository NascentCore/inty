package com.example.fcmserverpush

import android.os.Bundle
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.lifecycleScope
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.logging.HttpLoggingInterceptor
import org.json.JSONObject

class MainActivity : AppCompatActivity() {

    private val client: OkHttpClient by lazy {
        OkHttpClient.Builder()
            .addInterceptor(HttpLoggingInterceptor().apply {
                level = HttpLoggingInterceptor.Level.BODY
            })
            .build()
    }

    private var deviceToken: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val statusText = findViewById<TextView>(R.id.status_text)
        val tokenText = findViewById<TextView>(R.id.token_text)
        val submitButton = findViewById<Button>(R.id.submit_button)

        FirebaseMessaging.getInstance().token
            .addOnSuccessListener { token ->
                deviceToken = token
                tokenText.text = token
                statusText.text = getString(R.string.token_ready)
            }
            .addOnFailureListener { error ->
                statusText.text = getString(R.string.token_failed, error.localizedMessage)
            }

        lifecycleScope.launch {
            JobResultBus.results.collect { jobResult ->
                statusText.text = getString(
                    R.string.job_finished,
                    jobResult.jobId,
                    jobResult.message
                )
            }
        }

        submitButton.setOnClickListener {
            val token = deviceToken
            if (token.isNullOrBlank()) {
                Toast.makeText(this, R.string.token_missing, Toast.LENGTH_SHORT).show()
                return@setOnClickListener
            }

            lifecycleScope.launch {
                statusText.text = getString(R.string.job_submitting)
                val jobId = submitLongRunningTask(token)
                statusText.text = getString(R.string.job_submitted, jobId)
            }
        }
    }

    private suspend fun submitLongRunningTask(deviceToken: String): String = withContext(Dispatchers.IO) {
        val body = JSONObject()
            .put("device_token", deviceToken)
            .put("payload", JSONObject().put("requested_by", "android_app"))
            .toString()
            .toRequestBody("application/json".toMediaType())

        val request = Request.Builder()
            .url("${ServerConfig.BASE_URL}/process")
            .post(body)
            .build()

        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) {
                throw IllegalStateException("请求失败: ${response.code}")
            }
            val responseJson = JSONObject(response.body?.string().orEmpty())
            responseJson.getString("job_id")
        }
    }
}
