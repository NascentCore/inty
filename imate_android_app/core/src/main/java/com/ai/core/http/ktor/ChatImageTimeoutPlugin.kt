package com.ai.core.http.ktor

import io.ktor.client.plugins.api.createClientPlugin
import io.ktor.client.plugins.timeout

private const val CHAT_IMAGE_READ_TIMEOUT_MILLIS = 60_000L

val ChatImageTimeoutPlugin =
    createClientPlugin("ChatImageTimeoutPlugin") {
        onRequest { request, _ ->
            val method = request.method.value
            val path = request.url.build().encodedPath
            if (method == "POST" && path.startsWith("/api/v1/chat/images/")) {
                request.timeout { socketTimeoutMillis = CHAT_IMAGE_READ_TIMEOUT_MILLIS }
            }
        }
    }

