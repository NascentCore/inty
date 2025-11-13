package ai.sxwl.android.firebase

/**
 * FCM Token upload callback interface
 *
 * Used to decouple FCMService (infrastructure layer) from UserService (data layer)
 * Implementation should be provided by the application layer
 */
interface FCMTokenUploadCallback {
    /**
     * Called when FCM token needs to be uploaded to server
     *
     * @param token FCM registration token
     */
    suspend fun uploadToken(token: String)
}
