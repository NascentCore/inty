package com.ai.imate

import com.ai.imate.auth.AnalyticsLogger
import com.ai.imate.auth.AuthManager
import com.ai.imate.auth.AuthRepository
import com.ai.imate.auth.SessionStore
import com.ai.imate.data.UserSession
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class AuthManagerTest {
    @Test
    fun email_password_login_success_saves_session() = runTest {
        val fakeRepo = FakeAuthRepository()
        val fakeStore = FakeSessionStore()
        val fakeAnalytics = FakeAnalyticsLogger()
        val manager =
            AuthManager(
                authRepository = fakeRepo,
                sessionStore = fakeStore,
                analyticsLogger = fakeAnalytics,
            )

        val result = manager.loginWithEmailPassword("reviewer@example.com", "pass123")

        assertTrue(result.isSuccess)
        assertEquals("reviewer@example.com", fakeStore.sessionFlowState.value?.email)
        assertEquals(
            listOf("login_email_clicked", "login_email_success"),
            fakeAnalytics.events,
        )
    }

    @Test
    fun google_login_success_saves_session() = runTest {
        val fakeRepo = FakeAuthRepository()
        val fakeStore = FakeSessionStore()
        val fakeAnalytics = FakeAnalyticsLogger()
        val manager =
            AuthManager(
                authRepository = fakeRepo,
                sessionStore = fakeStore,
                analyticsLogger = fakeAnalytics,
            )

        val result = manager.loginWithGoogleToken("google-token")

        assertTrue(result.isSuccess)
        assertEquals("google@example.com", fakeStore.sessionFlowState.value?.email)
        assertEquals(
            listOf("login_google_clicked", "login_google_success"),
            fakeAnalytics.events,
        )
    }

    private class FakeAuthRepository : AuthRepository {
        override suspend fun loginWithEmailPassword(
            email: String,
            password: String,
        ): Result<UserSession> {
            return Result.success(
                UserSession(
                    token = "token-email",
                    userId = "user-email",
                    email = email,
                    nickname = "Reviewer",
                )
            )
        }

        override suspend fun loginWithGoogleToken(idToken: String): Result<UserSession> {
            return Result.success(
                UserSession(
                    token = "token-google",
                    userId = "user-google",
                    email = "google@example.com",
                    nickname = "GoogleUser",
                )
            )
        }
    }

    private class FakeSessionStore : SessionStore {
        val sessionFlowState = MutableStateFlow<UserSession?>(null)
        private val officialState = MutableStateFlow(true)

        override val sessionFlow: Flow<UserSession?> = sessionFlowState
        override val officialAssistantEnabledFlow: Flow<Boolean> = officialState

        override suspend fun saveSession(session: UserSession) {
            sessionFlowState.value = session
        }

        override suspend fun clearSession() {
            sessionFlowState.value = null
        }

        override suspend fun setOfficialAssistantEnabled(enabled: Boolean) {
            officialState.value = enabled
        }
    }

    private class FakeAnalyticsLogger : AnalyticsLogger {
        val events = mutableListOf<String>()

        override fun logEvent(name: String) {
            events.add(name)
        }
    }
}
