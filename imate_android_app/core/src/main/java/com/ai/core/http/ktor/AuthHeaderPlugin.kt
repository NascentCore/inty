package com.ai.core.http.ktor

import io.ktor.client.plugins.api.createClientPlugin

class AuthHeaderPluginConfig {
    var bearerTokenProvider: () -> String? = { null }
}

val AuthHeaderPlugin =
    createClientPlugin("AuthHeaderPlugin", ::AuthHeaderPluginConfig) {
        val tokenProvider = pluginConfig.bearerTokenProvider
        onRequest { request, _ ->
            val token = tokenProvider().orEmpty().trim()
            if (token.isNotEmpty() && request.headers["Authorization"] == null) {
                request.headers.append("Authorization", "Bearer $token")
            }
        }
    }

