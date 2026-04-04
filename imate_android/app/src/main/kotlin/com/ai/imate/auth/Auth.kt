package com.ai.imate.auth

import android.content.Context
import android.util.Log
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialException
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.remove
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStoreFile
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.ai.imate.BuildConfig
import com.ai.imate.data.ApiEnvelope
import com.ai.imate.data.LoginPayload
import com.ai.imate.data.LoginRequest
import com.ai.imate.data.UserSession
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import retrofit2.http.Body
import retrofit2.http.POST

interface AuthApi {
    @POST("/api/v1/auth/google/login")
    suspend fun login(@Body request: LoginRequest): ApiEnvelope<LoginPayload>
}

interface AuthRepository {
    suspend fun loginWithEmailPassword(email: String, password: String): Result<UserSession>

    suspend fun loginWithGoogleToken(idToken: String): Result<UserSession>
}

class RetrofitAuthRepository(private val authApi: AuthApi) : AuthRepository {
    override suspend fun loginWithEmailPassword(email: String, password: String): Result<UserSession> {
        val envelope = authApi.login(LoginRequest(email = email, password = password))
        return envelope.toSessionResult()
    }

    override suspend fun loginWithGoogleToken(idToken: String): Result<UserSession> {
        val envelope = authApi.login(LoginRequest(idToken = idToken))
        return envelope.toSessionResult()
    }

    private fun ApiEnvelope<LoginPayload>.toSessionResult(): Result<UserSession> {
        if (code != 200 || data == null) {
            val errorMessage = message ?: "Login failed"
            return Result.failure(IllegalStateException(errorMessage))
        }
        val nickname = data.user.nickname.orEmpty()
        val email = data.user.email.orEmpty()
        return Result.success(
            UserSession(
                token = data.token,
                userId = data.user.id,
                email = email,
                nickname = nickname,
            )
        )
    }

    companion object {
        fun fromBaseUrl(baseUrl: String): RetrofitAuthRepository {
            val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()
            val retrofit =
                Retrofit.Builder()
                    .baseUrl(baseUrl)
                    .addConverterFactory(MoshiConverterFactory.create(moshi))
                    .build()
            val authApi = retrofit.create(AuthApi::class.java)
            return RetrofitAuthRepository(authApi)
        }
    }
}

interface SessionStore {
    val sessionFlow: Flow<UserSession?>
    val officialAssistantEnabledFlow: Flow<Boolean>
    suspend fun saveSession(session: UserSession)
    suspend fun clearSession()
    suspend fun setOfficialAssistantEnabled(enabled: Boolean)
}

class DataStoreSessionStore(context: Context) : SessionStore {
    private val dataStore =
        PreferenceDataStoreFactory.create(
            corruptionHandler = null,
            produceFile = { context.preferencesDataStoreFile(PREF_FILE_NAME) },
        )

    override val sessionFlow: Flow<UserSession?> =
        dataStore.data
            .catch { emit(emptyPreferences()) }
            .map { pref ->
                val token = pref[tokenKey] ?: return@map null
                val userId = pref[userIdKey] ?: return@map null
                val email = pref[emailKey].orEmpty()
                val nickname = pref[nicknameKey].orEmpty()
                UserSession(token = token, userId = userId, email = email, nickname = nickname)
            }

    override val officialAssistantEnabledFlow: Flow<Boolean> =
        dataStore.data
            .catch { emit(emptyPreferences()) }
            .map { pref -> pref[officialAssistantEnabledKey] ?: true }

    override suspend fun saveSession(session: UserSession) {
        dataStore.edit { pref ->
            pref[tokenKey] = session.token
            pref[userIdKey] = session.userId
            pref[emailKey] = session.email
            pref[nicknameKey] = session.nickname
        }
    }

    override suspend fun clearSession() {
        dataStore.edit { pref ->
            pref.remove(tokenKey)
            pref.remove(userIdKey)
            pref.remove(emailKey)
            pref.remove(nicknameKey)
        }
    }

    override suspend fun setOfficialAssistantEnabled(enabled: Boolean) {
        dataStore.edit { pref ->
            pref[officialAssistantEnabledKey] = enabled
        }
    }

    private companion object {
        private const val PREF_FILE_NAME = "imate_pref"
        private val tokenKey = stringPreferencesKey("token")
        private val userIdKey = stringPreferencesKey("user_id")
        private val emailKey = stringPreferencesKey("email")
        private val nicknameKey = stringPreferencesKey("nickname")
        private val officialAssistantEnabledKey = booleanPreferencesKey("official_assistant_enabled")
    }
}

interface AnalyticsLogger {
    fun logEvent(name: String)
}

class LogcatAnalyticsLogger : AnalyticsLogger {
    override fun logEvent(name: String) {
        Log.i("iMateAnalytics", name)
    }
}

class AuthManager(
    private val authRepository: AuthRepository,
    private val sessionStore: SessionStore,
    private val analyticsLogger: AnalyticsLogger,
) {
    private companion object {
        private const val ERROR_EMAIL_PASSWORD_REQUIRED = "Email and password are required"
        private const val ERROR_ID_TOKEN_REQUIRED = "Google id_token is required"
    }

    suspend fun loginWithEmailPassword(email: String, password: String): Result<UserSession> {
        if (email.isBlank() || password.isBlank()) {
            return Result.failure(IllegalArgumentException(ERROR_EMAIL_PASSWORD_REQUIRED))
        }
        analyticsLogger.logEvent("login_email_clicked")
        return authRepository.loginWithEmailPassword(email, password).onSuccess { session ->
            sessionStore.saveSession(session)
            analyticsLogger.logEvent("login_email_success")
        }
    }

    suspend fun loginWithGoogleToken(idToken: String): Result<UserSession> {
        if (idToken.isBlank()) {
            return Result.failure(IllegalArgumentException(ERROR_ID_TOKEN_REQUIRED))
        }
        analyticsLogger.logEvent("login_google_clicked")
        return authRepository.loginWithGoogleToken(idToken).onSuccess { session ->
            sessionStore.saveSession(session)
            analyticsLogger.logEvent("login_google_success")
        }
    }

    suspend fun logout() {
        sessionStore.clearSession()
        analyticsLogger.logEvent("logout_clicked")
    }
}

data class AuthUiState(
    val isLoading: Boolean = false,
    val session: UserSession? = null,
    val emailInput: String = "",
    val passwordInput: String = "",
    val errorMessage: String? = null,
    val officialAssistantEnabled: Boolean = true,
)

class AuthViewModel(
    private val authManager: AuthManager,
    private val sessionStore: SessionStore,
) : ViewModel() {
    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            combine(
                sessionStore.sessionFlow,
                sessionStore.officialAssistantEnabledFlow,
            ) { session, officialEnabled ->
                Pair(session, officialEnabled)
            }.collect { (session, officialEnabled) ->
                _uiState.value =
                    _uiState.value.copy(
                        session = session,
                        officialAssistantEnabled = officialEnabled,
                    )
            }
        }
    }

    fun updateEmailInput(value: String) {
        _uiState.value = _uiState.value.copy(emailInput = value, errorMessage = null)
    }

    fun updatePasswordInput(value: String) {
        _uiState.value = _uiState.value.copy(passwordInput = value, errorMessage = null)
    }

    fun loginByEmailPassword() {
        val email = _uiState.value.emailInput.trim()
        val password = _uiState.value.passwordInput
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            val result = authManager.loginWithEmailPassword(email, password)
            _uiState.value =
                _uiState.value.copy(
                    isLoading = false,
                    passwordInput = "",
                    errorMessage = result.exceptionOrNull()?.message,
                )
        }
    }

    fun loginByGoogleToken(idToken: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true, errorMessage = null)
            val result = authManager.loginWithGoogleToken(idToken)
            _uiState.value =
                _uiState.value.copy(
                    isLoading = false,
                    errorMessage = result.exceptionOrNull()?.message,
                )
        }
    }

    fun logout() {
        viewModelScope.launch {
            authManager.logout()
        }
    }

    fun setOfficialAssistantEnabled(enabled: Boolean) {
        viewModelScope.launch {
            sessionStore.setOfficialAssistantEnabled(enabled)
        }
    }

    companion object {
        fun factory(authManager: AuthManager, sessionStore: SessionStore): ViewModelProvider.Factory {
            return object : ViewModelProvider.Factory {
                @Suppress("UNCHECKED_CAST")
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    return AuthViewModel(authManager, sessionStore) as T
                }
            }
        }
    }
}

object GoogleCredentialClient {
    suspend fun getGoogleIdToken(context: Context): Result<String> {
        return try {
            val credentialManager = CredentialManager.create(context)
            val option = GetSignInWithGoogleOption.Builder(BuildConfig.WEB_CLIENT_ID).build()
            val request = GetCredentialRequest.Builder().addCredentialOption(option).build()
            val response = credentialManager.getCredential(context = context, request = request)
            val credential = response.credential
            if (credential !is CustomCredential) {
                return Result.failure(IllegalStateException("Unsupported credential type"))
            }
            if (credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                return Result.failure(IllegalStateException("Unsupported credential payload"))
            }
            val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
            Result.success(googleIdTokenCredential.idToken)
        } catch (error: GetCredentialException) {
            Result.failure(error)
        } catch (error: GoogleIdTokenParsingException) {
            Result.failure(error)
        }
    }
}
