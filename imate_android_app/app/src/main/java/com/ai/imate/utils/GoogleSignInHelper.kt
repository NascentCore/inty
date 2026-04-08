package com.ai.imate.utils

import android.content.Context
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.GetCredentialResponse
import androidx.credentials.exceptions.GetCredentialException
import com.ai.imate.BuildConfig
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

object GoogleSignInHelper {

    suspend fun signInWithGoogle(context: Context): Result<String> =
        withContext(Dispatchers.Main) {
            try {
                val credentialManager = CredentialManager.create(context)
                val signInWithGoogleOption =
                    GetSignInWithGoogleOption.Builder(serverClientId = BuildConfig.WEB_CLIENT_ID)
                        .build()
                val request =
                    GetCredentialRequest.Builder()
                        .addCredentialOption(signInWithGoogleOption)
                        .build()
                val response = credentialManager.getCredential(request = request, context = context)
                handleResponse(response)
            } catch (e: GetCredentialException) {
                Result.failure(e)
            }
        }

    private fun handleResponse(response: GetCredentialResponse): Result<String> {
        return when (val credential = response.credential) {
            is CustomCredential -> {
                if (credential.type == GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL) {
                    try {
                        val googleIdTokenCredential = GoogleIdTokenCredential.createFrom(credential.data)
                        Result.success(googleIdTokenCredential.idToken)
                    } catch (e: GoogleIdTokenParsingException) {
                        Result.failure(e)
                    }
                } else {
                    Result.failure(IllegalStateException("Unexpected credential type: ${credential.type}"))
                }
            }
            else -> Result.failure(IllegalStateException("Unexpected credential: ${credential::class.java.name}"))
        }
    }
}
