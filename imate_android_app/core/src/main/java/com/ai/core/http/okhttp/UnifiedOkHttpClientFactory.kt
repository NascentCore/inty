package com.ai.core.http.okhttp

import java.net.InetAddress
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.TimeUnit
import okhttp3.ConnectionPool
import okhttp3.Dns
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response

object UnifiedOkHttpClientFactory {
    private const val CONNECT_TIMEOUT_MS = 15_000L
    private const val WRITE_TIMEOUT_MS = 15_000L
    private const val READ_TIMEOUT_MS = 30_000L

    private const val MAX_CONNECTIONS = 5
    private const val KEEP_ALIVE_DURATION_MS = 300_000L

    private const val CHAT_IMAGE_READ_TIMEOUT_SECONDS = 60

    fun create(
        authTokenProvider: () -> String?,
    ): OkHttpClient {
        return OkHttpClient.Builder()
            .connectTimeout(CONNECT_TIMEOUT_MS, TimeUnit.MILLISECONDS)
            .writeTimeout(WRITE_TIMEOUT_MS, TimeUnit.MILLISECONDS)
            .readTimeout(READ_TIMEOUT_MS, TimeUnit.MILLISECONDS)
            .connectionPool(
                ConnectionPool(
                    MAX_CONNECTIONS,
                    KEEP_ALIVE_DURATION_MS,
                    TimeUnit.MILLISECONDS,
                )
            )
            .dns(CachedDns())
            .addInterceptor(ChatImageTimeoutInterceptor)
            .addInterceptor(AuthInterceptor(authTokenProvider))
            .build()
    }

    private object ChatImageTimeoutInterceptor : Interceptor {
        override fun intercept(chain: Interceptor.Chain): Response {
            val request = chain.request()
            return if (shouldApplyChatImageReadTimeout(request)) {
                chain.withReadTimeout(CHAT_IMAGE_READ_TIMEOUT_SECONDS, TimeUnit.SECONDS).proceed(request)
            } else {
                chain.proceed(request)
            }
        }
    }

    private fun shouldApplyChatImageReadTimeout(request: Request): Boolean {
        val path = request.url.encodedPath
        return request.method == "POST" && path.startsWith("/api/v1/chat/images/")
    }

    private class AuthInterceptor(
        private val authTokenProvider: () -> String?,
    ) : Interceptor {
        override fun intercept(chain: Interceptor.Chain): Response {
            val request = chain.request()
            val token = authTokenProvider().orEmpty().trim()
            if (token.isEmpty() || request.header("Authorization") != null) {
                return chain.proceed(request)
            }
            val authedRequest = request.newBuilder().addHeader("Authorization", "Bearer $token").build()
            return chain.proceed(authedRequest)
        }
    }

    private class CachedDns : Dns {
        private val cache = ConcurrentHashMap<String, List<InetAddress>>()
        private val cacheExpiry = ConcurrentHashMap<String, Long>()
        private val cacheDurationMs = 5 * 60 * 1000L

        override fun lookup(hostname: String): List<InetAddress> {
            val now = System.currentTimeMillis()
            val expiry = cacheExpiry[hostname] ?: 0L
            if (now > expiry) {
                cache.remove(hostname)
                cacheExpiry.remove(hostname)
            }
            return cache.getOrPut(hostname) {
                val result = Dns.SYSTEM.lookup(hostname)
                cacheExpiry[hostname] = now + cacheDurationMs
                result
            }
        }
    }
}

