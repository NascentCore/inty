package com.inty.imate.utils

import android.content.Context
import com.inty.imate.R

/** Maps Credential Manager exceptions to clearer user-visible toasts where we can infer the case. */
object CredentialToastMapper {
    /**
     * Credential Manager surfaces "[16] Account reauth failed" when GMS cannot complete the OAuth
     * token flow (often underlying NETWORK_ERROR — see AuthPII / GmsNetworkStack in logcat).
     */
    fun toastMessage(context: Context, throwable: Throwable, rawMessage: String?): String {
        val raw = rawMessage.orEmpty()
        val fromCredentialManager =
            throwable.javaClass.name.startsWith("androidx.credentials")
        if (!fromCredentialManager || !looksLikeGoogleReauthFailure(raw)) {
            return raw
        }
        return context.getString(R.string.login_google_sign_in_connectivity)
    }

    /**
     * Avoid matching unrelated "[16]" text; pair with Credential Manager exceptions only (caller).
     */
    private fun looksLikeGoogleReauthFailure(raw: String): Boolean =
        raw.contains("reauth", ignoreCase = true) ||
            (raw.contains("[16]") && raw.contains("account", ignoreCase = true))
}
