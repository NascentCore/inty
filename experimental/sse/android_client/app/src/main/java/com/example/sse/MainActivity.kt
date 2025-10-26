package com.example.sse

import android.os.Bundle
import android.widget.Button
import android.widget.EditText
import android.widget.TextView
import androidx.activity.ComponentActivity
import androidx.activity.viewModels
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import androidx.lifecycle.ViewModel
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.sse.EventSource
import okhttp3.sse.EventSourceListener
import okhttp3.sse.EventSources
import java.util.concurrent.TimeUnit

class MainActivity : ComponentActivity() {
    private val viewModel: SseViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        val output = findViewById<TextView>(R.id.output)
        val input = findViewById<EditText>(R.id.input)
        val btnSend = findViewById<Button>(R.id.btnSend)
        val btnConnect = findViewById<Button>(R.id.btnConnect)
        val btnDisconnect = findViewById<Button>(R.id.btnDisconnect)

        viewModel.logs.observe(this) { text ->
            output.text = text
        }

        btnConnect.setOnClickListener {
            viewModel.connect()
        }
        btnDisconnect.setOnClickListener {
            viewModel.disconnect()
        }
        btnSend.setOnClickListener {
            val message = input.text?.toString()?.trim().orEmpty()
            if (message.isNotEmpty()) {
                lifecycleScope.launch {
                    viewModel.sendMessage(message)
                }
            }
        }
    }
}

class SseViewModel : ViewModel() {
    private val _logs = MutableLiveData("")
    val logs: LiveData<String> = _logs

    private val client: OkHttpClient = OkHttpClient.Builder()
        .readTimeout(0, TimeUnit.MILLISECONDS) // Never time out the stream
        .build()

    private var eventSource: EventSource? = null

    private fun append(line: String) {
        val current = _logs.value ?: ""
        _logs.postValue(
            if (current.isEmpty()) line else (current + "\n" + line)
        )
    }

    fun connect() {
        if (eventSource != null) return
        val request = Request.Builder()
            .url(SERVER_BASE + "/stream")
            .header("Accept", "text/event-stream")
            .build()

        val listener = object : EventSourceListener() {
            override fun onOpen(es: EventSource, response: okhttp3.Response) {
                append("[open] connected")
            }
            override fun onEvent(
                es: EventSource,
                id: String?,
                type: String?,
                data: String
            ) {
                val label = if (type != null) type else "message"
                append("[event] ${'$'}label: ${'$'}data")
            }
            override fun onClosed(es: EventSource) {
                append("[closed]")
            }
            override fun onFailure(
                es: EventSource,
                t: Throwable?,
                response: okhttp3.Response?
            ) {
                append("[error] ${'$'}{t?.message ?: "unknown"}")
                eventSource = null
            }
        }

        eventSource = EventSources.createFactory(client).newEventSource(request, listener)
    }

    fun disconnect() {
        eventSource?.cancel()
        eventSource = null
    }

    suspend fun sendMessage(message: String) {
        withContext(Dispatchers.IO) {
            val json = "{" + "\"message\":\"" + message.replace("\"", "\\\"") + "\"}"
            val body = json.toRequestBody("application/json".toMediaType())
            val request = Request.Builder()
                .url(SERVER_BASE + "/publish")
                .post(body)
                .build()
            try {
                client.newCall(request).execute().use { resp ->
                    append("[send] ${'$'}{resp.code}")
                }
            } catch (e: Exception) {
                append("[send-error] ${'$'}{e.message}")
            }
        }
    }

    companion object {
        private const val SERVER_BASE = "http://10.0.2.2:8009"
    }
}
