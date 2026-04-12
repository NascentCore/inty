package com.ai.intellimate.chat.data

// CREATED_BY_AGENT

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.ChatMode
import ai.sxwl.android.data.api.model.ChatSettingsReq
import ai.sxwl.android.data.api.model.ChatSettingsResponse
import ai.sxwl.android.data.api.model.SendMsgResponse
import ai.sxwl.android.data.chat.data.ChatRemoteDataSource
import ai.sxwl.android.data.chat.local.db.IntyChatDatabase
import ai.sxwl.android.data.chat.local.db.MessageEntity
import ai.sxwl.android.data.chat.local.db.createTempSendingLoadingEntity
import ai.sxwl.android.data.chat.local.db.toEntity
import ai.sxwl.android.data.chat.local.db.toUpdate
import ai.sxwl.android.data.http.BusinessErrorCodes
import ai.sxwl.android.data.store.dataStore
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.Utils
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Matrix
import android.media.ExifInterface
import android.net.Uri
import androidx.core.net.toUri
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.paging.ExperimentalPagingApi
import androidx.paging.Pager
import androidx.paging.PagingConfig
import androidx.paging.PagingData
import com.ai.intellimate.boost.BoostManager
import com.ai.intellimate.boost.BoostStorage
import com.ai.intellimate.boost.PointSource
import com.architecture.httplib.core.HttpResult
import java.io.File
import java.io.FileOutputStream
import kotlin.time.Duration.Companion.days
import kotlin.time.Duration.Companion.milliseconds
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.channelFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody

data class ChatPreparedImageUpload(
    val uploadedImageUrl: String,
    val localCompressedImageUri: String,
    val width: Int,
    val height: Int,
)

data class ChatPreparedLocalImage(
    val localCompressedFile: File,
    val localCompressedImageUri: String,
    val width: Int,
    val height: Int,
)

/**
 * 聊天消息的 Paging Repository 使用 RemoteMediator 实现数据库查询和网络同步
 *
 * 使用场景：
 * - 在聊天页面中使用 Paging 加载聊天记录
 * - 自动从网络同步数据到数据库
 * - 支持下拉刷新和上拉加载更多
 *
 * 可配置项：
 * - agentId: 智能体 ID
 * - pageSize: 每页加载的消息数量，默认 20
 * - prefetchDistance: 预取距离，默认 3
 * - enablePlaceholders: 是否启用占位符，默认 false
 */
class ChatMessageRepository(
    private val database: IntyChatDatabase = IntyChatDatabase.getInstance(),
    private val remoteDataSource: ChatRemoteDataSource = ChatRemoteDataSource(),
    private val localDataSource: ChatLocalDataSource = ChatLocalDataSource(database),
) {
    companion object {
        private val KEY_LAST_RANK_DATE = longPreferencesKey("last_rank_date")
    }

    /** 获取聊天消息的 PagingData Flow 返回的 Flow 会从数据库读取数据，并在需要时通过 RemoteMediator 从网络同步 */
    @OptIn(ExperimentalPagingApi::class)
    fun getMessagesFlow(agentId: String): Flow<PagingData<MessageEntity>> {
        return Pager(
                config = PagingConfig(pageSize = 20, enablePlaceholders = false),
                remoteMediator =
                    ChatMessageRemoteMediator(
                        agentId = agentId,
                        database = database,
                        remoteDataSource = remoteDataSource,
                    ),
                pagingSourceFactory = { database.chatMessageDao().pagingSource(agentId) },
            )
            .flow
    }

    suspend fun clearMessages(agentId: String) {
        localDataSource.chatMessageDao.deleteByAgent(agentId)
    }

    suspend fun sendMessage(
        agentId: String,
        content: String,
        localImageUri: String? = null,
        preUploadTask: Deferred<HttpResult<ChatPreparedImageUpload>>? = null,
    ): HttpResult<SendMsgResponse> {
        LogUtils.d("RoomImpl.sendMessage called for $agentId: $content")

        val trimmed = content.trimEnd()
        val timestamp = java.time.Instant.ofEpochMilli(System.currentTimeMillis()).toString()
        // AI implementation summary:
        // 1) append local user message + loading placeholder immediately;
        // 2) resolve uploaded URL via pre-upload task first, fallback to direct upload;
        // 3) keep the temporary user bubble image as local URI to avoid blank waiting state.
        localDataSource.appendSendingMessages(agentId, trimmed, localImageUri)

        return try {
            val preparedImageUpload =
                if (localImageUri.isNullOrBlank()) {
                    null
                } else {
                    when (
                        val resolvedUpload = resolveChatInputImage(localImageUri, preUploadTask)
                    ) {
                        is HttpResult.Success -> resolvedUpload.data
                        is HttpResult.Failure -> {
                            localDataSource.removeSendingMessage(agentId)
                            return HttpResult.Failure(resolvedUpload.message, resolvedUpload.code)
                        }
                    }
                }
            val compressedImageUri = preparedImageUpload?.localCompressedImageUri
            if (!compressedImageUri.isNullOrBlank() && compressedImageUri != localImageUri) {
                localDataSource.updateSendingUserImage(
                    agentId = agentId,
                    imageUrl = compressedImageUri,
                    width = preparedImageUpload.width,
                    height = preparedImageUpload.height,
                )
            }
            val uploadedImageUrl = preparedImageUpload?.uploadedImageUrl
            val userBubbleImageUri = compressedImageUri ?: localImageUri

            val result =
                try {
                    remoteDataSource.sendMessage(agentId, trimmed, uploadedImageUrl)
                } catch (e: Exception) {
                    LogUtils.e("RoomImpl.sendMessage exception: ${e.message}")
                    HttpResult.Failure(e.message ?: "unknown error", -1)
                }

            if (
                result is HttpResult.Success &&
                    result.data.code != BusinessErrorCodes.SUBSCRIPTION_REQUIRED_CODE
            ) {
                localDataSource.removeSendingMessage(agentId)
                result.data.data?.let { data ->
                    val buildMessages = buildList {
                        add(
                            MessageEntity(
                                id = data.user_message_id.toString(),
                                content = trimmed,
                                role = "user",
                                metaData =
                                    MessageEntity.MetaData(
                                        agentId = agentId,
                                        generatedImage =
                                            userBubbleImageUri?.let {
                                                MessageEntity.MetaData.GeneratedImage(
                                                    imageUrl = it,
                                                    width = preparedImageUpload?.width,
                                                    height = preparedImageUpload?.height,
                                                )
                                            },
                                    ),
                                timestamp = timestamp,
                            )
                        )
                        addAll(data.choices.map { it.message.toEntity(agentId) })
                    }

                    localDataSource.appendMessages(buildMessages)

                    LogUtils.d(
                        "RoomImpl.sendMessage saving ${buildMessages.size} assistant messages for agentId=$agentId"
                    )
                }
            } else {
                localDataSource.markSendingFailedAndRemoveLoading(agentId)
            }

            result
        } catch (e: Exception) {
            localDataSource.markSendingFailedAndRemoveLoading(agentId)
            throw e
        }
    }

    suspend fun preUploadChatInputImage(
        localImageUri: String
    ): HttpResult<ChatPreparedImageUpload> {
        val preparedImageResult = prepareChatInputImage(localImageUri)
        return when (preparedImageResult) {
            is HttpResult.Success -> uploadPreparedChatInputImage(preparedImageResult.data)
            is HttpResult.Failure ->
                HttpResult.Failure(preparedImageResult.message, preparedImageResult.code)
        }
    }

    suspend fun updateSendingUserImage(
        agentId: String,
        imageUrl: String,
        width: Int?,
        height: Int?,
    ) {
        localDataSource.updateSendingUserImage(agentId, imageUrl, width, height)
    }

    private suspend fun resolveChatInputImage(
        localImageUri: String,
        preUploadTask: Deferred<HttpResult<ChatPreparedImageUpload>>?,
    ): HttpResult<ChatPreparedImageUpload> {
        val preUploadResult = awaitPreUploadResult(preUploadTask)
        if (preUploadResult is HttpResult.Success) {
            return preUploadResult
        }
        return when (val directUploadResult = uploadChatInputImage(localImageUri.toUri())) {
            is HttpResult.Success -> directUploadResult
            is HttpResult.Failure ->
                HttpResult.Failure(directUploadResult.message, directUploadResult.code)
        }
    }

    private suspend fun awaitPreUploadResult(
        preUploadTask: Deferred<HttpResult<ChatPreparedImageUpload>>?
    ): HttpResult<ChatPreparedImageUpload>? {
        if (preUploadTask == null) {
            return null
        }
        return try {
            preUploadTask.await()
        } catch (cancelled: CancellationException) {
            null
        }
    }

    suspend fun prepareChatInputImage(localImageUri: String): HttpResult<ChatPreparedLocalImage> {
        return withContext(Dispatchers.IO) {
            val imageUri = localImageUri.toUri()
            try {
                val preparedImage = prepareChatInputImageInternal(imageUri)
                if (preparedImage.isFailure) {
                    val error = preparedImage.exceptionOrNull()
                    HttpResult.Failure(error?.message ?: "Failed to prepare selected image", -1)
                } else {
                    HttpResult.Success(preparedImage.getOrThrow())
                }
            } catch (e: Exception) {
                LogUtils.e("prepareChatInputImage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "Failed to prepare selected image", -1)
            }
        }
    }

    suspend fun uploadPreparedChatInputImage(
        preparedImage: ChatPreparedLocalImage
    ): HttpResult<ChatPreparedImageUpload> {
        return withContext(Dispatchers.IO) {
            try {
                val requestBody =
                    preparedImage.localCompressedFile.asRequestBody(
                        "image/jpeg".toMediaTypeOrNull()
                    )
                val multipart =
                    MultipartBody.Part.createFormData(
                        "file",
                        preparedImage.localCompressedFile.name,
                        requestBody,
                    )
                when (val uploadResult = NetServiceMgr.getUserApi().uploadAvatar(multipart)) {
                    is HttpResult.Success -> {
                        val resolvedUrl =
                            uploadResult.data.url.ifBlank { uploadResult.data.avatar_url }
                        if (resolvedUrl.isBlank()) {
                            HttpResult.Failure("Image upload returned empty url", -1)
                        } else {
                            HttpResult.Success(
                                ChatPreparedImageUpload(
                                    uploadedImageUrl = resolvedUrl,
                                    localCompressedImageUri = preparedImage.localCompressedImageUri,
                                    width = preparedImage.width,
                                    height = preparedImage.height,
                                )
                            )
                        }
                    }
                    is HttpResult.Failure -> {
                        HttpResult.Failure(uploadResult.message, uploadResult.code)
                    }
                }
            } catch (e: Exception) {
                LogUtils.e("uploadChatInputImage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "Image upload failed", -1)
            }
        }
    }

    private suspend fun uploadChatInputImage(imageUri: Uri): HttpResult<ChatPreparedImageUpload> {
        val preparedImageResult = prepareChatInputImage(imageUri.toString())
        return when (preparedImageResult) {
            is HttpResult.Success -> uploadPreparedChatInputImage(preparedImageResult.data)
            is HttpResult.Failure ->
                HttpResult.Failure(preparedImageResult.message, preparedImageResult.code)
        }
    }

    private fun prepareChatInputImageInternal(imageUri: Uri): Result<ChatPreparedLocalImage> {
        val context = Utils.getApp()
        val (originalWidth, originalHeight) =
            decodeImageBounds(imageUri).getOrElse { error ->
                return Result.failure(error)
            }
        val scaledSize =
            ChatInputImageScaling.scaleToTargetArea(
                originalWidth = originalWidth,
                originalHeight = originalHeight,
            )
        val sampleSize =
            maxOf(originalWidth / scaledSize.width, originalHeight / scaledSize.height, 1)
        val decodedBitmap =
            decodeBitmapWithSample(imageUri, sampleSize).getOrElse { error ->
                return Result.failure(error)
            }
        val orientation =
            readExifOrientation(imageUri).getOrElse { ExifInterface.ORIENTATION_NORMAL }
        val orientedBitmap =
            applyExifOrientation(decodedBitmap, orientation).let { oriented ->
                if (oriented.width == scaledSize.width && oriented.height == scaledSize.height) {
                    oriented
                } else {
                    Bitmap.createScaledBitmap(oriented, scaledSize.width, scaledSize.height, true)
                        .also {
                            if (it !== oriented) {
                                oriented.recycle()
                            }
                        }
                }
            }
        val compressedFile = File.createTempFile("chat_input_compressed_", ".jpg", context.cacheDir)
        return try {
            FileOutputStream(compressedFile).use { output ->
                if (!orientedBitmap.compress(Bitmap.CompressFormat.JPEG, 85, output)) {
                    return Result.failure(IllegalStateException("Failed to compress image"))
                }
            }
            Result.success(
                ChatPreparedLocalImage(
                    localCompressedFile = compressedFile,
                    localCompressedImageUri = Uri.fromFile(compressedFile).toString(),
                    width = orientedBitmap.width,
                    height = orientedBitmap.height,
                )
            )
        } finally {
            orientedBitmap.recycle()
        }
    }

    /**
     * Decodes only image dimensions (width, height) without loading pixel data. Uses
     * [BitmapFactory.Options.inJustDecodeBounds]; the stream is read only to fill options.
     */
    private fun decodeImageBounds(imageUri: Uri): Result<Pair<Int, Int>> {
        val context = Utils.getApp()
        return try {
            val options = BitmapFactory.Options().apply { inJustDecodeBounds = true }
            val inputStream = context.contentResolver.openInputStream(imageUri)
            if (inputStream == null) {
                return Result.failure(IllegalStateException("Failed to read selected image"))
            }
            inputStream.use { input ->
                BitmapFactory.decodeStream(input, null, options)
                // inJustDecodeBounds: decodeStream returns null; dimensions are in options.
            }
            if (options.outWidth <= 0 || options.outHeight <= 0) {
                Result.failure(IllegalStateException("Failed to decode selected image bounds"))
            } else {
                Result.success(options.outWidth to options.outHeight)
            }
        } catch (error: Exception) {
            Result.failure(error)
        }
    }

    private fun decodeBitmapWithSample(imageUri: Uri, sampleSize: Int): Result<Bitmap> {
        val context = Utils.getApp()
        return try {
            val options = BitmapFactory.Options().apply { inSampleSize = sampleSize }
            val bitmap =
                context.contentResolver.openInputStream(imageUri)?.use { input ->
                    BitmapFactory.decodeStream(input, null, options)
                }
            if (bitmap == null) {
                Result.failure(IllegalStateException("Failed to decode selected image"))
            } else {
                Result.success(bitmap)
            }
        } catch (error: Exception) {
            Result.failure(error)
        }
    }

    private fun readExifOrientation(imageUri: Uri): Result<Int> {
        val context = Utils.getApp()
        return try {
            val orientation =
                context.contentResolver.openInputStream(imageUri)?.use { input ->
                    ExifInterface(input)
                        .getAttributeInt(
                            ExifInterface.TAG_ORIENTATION,
                            ExifInterface.ORIENTATION_NORMAL,
                        )
                } ?: ExifInterface.ORIENTATION_NORMAL
            Result.success(orientation)
        } catch (error: Exception) {
            Result.failure(error)
        }
    }

    private fun applyExifOrientation(bitmap: Bitmap, orientation: Int): Bitmap {
        val matrix =
            Matrix().apply {
                when (orientation) {
                    ExifInterface.ORIENTATION_FLIP_HORIZONTAL -> postScale(-1f, 1f)
                    ExifInterface.ORIENTATION_ROTATE_180 -> postRotate(180f)
                    ExifInterface.ORIENTATION_FLIP_VERTICAL -> postScale(1f, -1f)
                    ExifInterface.ORIENTATION_TRANSPOSE -> {
                        postRotate(90f)
                        postScale(-1f, 1f)
                    }
                    ExifInterface.ORIENTATION_ROTATE_90 -> postRotate(90f)
                    ExifInterface.ORIENTATION_TRANSVERSE -> {
                        postRotate(-90f)
                        postScale(-1f, 1f)
                    }
                    ExifInterface.ORIENTATION_ROTATE_270 -> postRotate(270f)
                }
            }
        if (matrix.isIdentity) {
            return bitmap
        }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true).also {
            if (it !== bitmap) {
                bitmap.recycle()
            }
        }
    }

    suspend fun recallLastAssistantMessage(agentId: String) {
        LogUtils.d("RoomImpl.recallLastAssistantMessage called for $agentId")
        val lastAssistantMessage = localDataSource.getLatesAgentMessage(agentId)

        if (lastAssistantMessage == null) {
            LogUtils.w("RoomImpl.recallLastAssistantMessage: No assistant message to recall")
            return
        }

        localDataSource.removeMessage(
            agentId,
            lastAssistantMessage.id,
            lastAssistantMessage.indexId,
        )
        // localDataSource.appendSendingLoadingOnly(agentId)

        val loadingMsg = createTempSendingLoadingEntity(agentId)
        localDataSource.appendMessages(listOf(loadingMsg))

        val result =
            try {
                remoteDataSource.sendMessage(agentId, userText = "recall")
            } catch (e: Exception) {
                LogUtils.e("RoomImpl.recallLastAssistantMessage exception: ${e.message}")
                HttpResult.Failure(e.message ?: "unknown error", -1)
            }

        localDataSource.removeMessages(listOf(loadingMsg))

        if (result is HttpResult.Success) {
            val choices = result.data.data?.choices ?: emptyList()
            if (choices.isNotEmpty()) {
                val assistantMsgs = choices.map { it.message.toEntity(agentId) }
                localDataSource.appendMessages(assistantMsgs)
            }
        } else {
            localDataSource.upsert(lastAssistantMessage)
        }
    }

    suspend fun getMessageCounts(agentId: String) = localDataSource.getMessageCounts(agentId)

    suspend fun countUserMessages(agentId: String) = localDataSource.countUserMessages(agentId)

    suspend fun getMessage(agentId: String, msgId: String) =
        localDataSource.getMessage(agentId, msgId)

    suspend fun loadRecentMessages(agentId: String, count: Int) {
        val result =
            runCatching {
                    LogUtils.d("加载最近消息:Count=$count")
                    remoteDataSource.getMessages(agentId, count, 0)
                }
                .getOrElse { HttpResult.Failure(it.message ?: "unknown error", -1) }

        if (result is HttpResult.Success) {
            val entities = result.data.messages?.map { it.toUpdate(agentId) }.orEmpty()

            if (entities.isNotEmpty()) {
                localDataSource.upsert(entities)
            }
        }
    }

    suspend fun setMessageVote(
        agentId: String,
        messageId: String,
        userVote: MessageEntity.UserVote,
    ) {
        withContext(Dispatchers.IO) {
            try {
                localDataSource.setMessageVote(agentId, messageId, userVote)

                val result = remoteDataSource.voteMessage(agentId, messageId, userVote.name)

                if (result is HttpResult.Failure) {
                    throw Exception(result.message)
                }
            } catch (error: Exception) {
                // 不再回滚本地状态：远程投票失败时保留用户已选的 like/dislike，避免 UI 闪一下又恢复
                // 只提示错误日志，不抛出异常
                LogUtils.e("Vote message remote failure (local vote kept): ${error.message}")
                throw error
            }
        }
    }

    suspend fun resetMessageVote(agentId: String, msgId: String) {
        withContext(Dispatchers.IO) { localDataSource.setMessageVote(agentId, msgId, null) }
    }

    suspend fun addImageGenerationErrorTips(agentId: String, messageId: String) {
        // 在消息列表中添加 tips 消息（使用字符串常量，后续在 UI 层处理）
        val tipMessage =
            MessageEntity(
                id = messageId,
                content = "image_generation_error_tip", // 特殊标记，UI 层会转换为实际文案
                role = "system",
                indexId = "image_generation_error_${System.nanoTime()}",
                metaData = MessageEntity.MetaData(agentId = agentId),
            )

        withContext(Dispatchers.IO) { localDataSource.appendMessages(listOf(tipMessage)) }
    }

    suspend fun appendBoostSystemMessage(agentId: String, content: String) {

        withContext(Dispatchers.IO) {
            val lastMessageId = localDataSource.getLatestMessageId(agentId)

            val message =
                MessageEntity(
                    id = lastMessageId ?: "${Long.MAX_VALUE}",
                    content = content,
                    role = "system",
                    indexId = "boost_${System.nanoTime()}",
                    metaData = MessageEntity.MetaData(agentId = agentId),
                )

            localDataSource.appendMessages(listOf(message))
        }
    }

    suspend fun removeMessage(agentId: String, msgId: String, indexId: String) {
        localDataSource.removeMessage(agentId, msgId, indexId)
    }

    suspend fun getImageMessages(agentId: String) = localDataSource.getImageMessages(agentId)

    fun messageCountFlow(agentId: String) = localDataSource.messageCountFlow(agentId)

    fun userMessageCountFlow(agentId: String) = localDataSource.userMessageCountFlow(agentId)

    suspend fun purchaseForMoment(agentId: String, messageId: String, price: Int) {
        if (BoostStorage.boostState.first().availablePoints >= price) {
            when (val result = remoteDataSource.unlockSurpriseSnap(messageId.toLong())) {
                is HttpResult.Success -> {
                    if (BoostManager.consume(price, PointSource.ForMoment)) {
                        localDataSource.setForMomentPurchased(agentId, messageId)
                    } else {
                        throw Exception("Not enough credits.")
                    }
                }
                is HttpResult.Failure -> {
                    throw Exception(result.message)
                }
            }
        } else {
            throw Exception("Not enough credits.")
        }
    }

    suspend fun shouldShowRank(): Boolean {
        val lastRankDate = dataStore().data.map { it[KEY_LAST_RANK_DATE] }.first() ?: 0
        val currentDate = System.currentTimeMillis()

        return (localDataSource.getYesterdaySendCount() > 20 &&
                currentDate.milliseconds - lastRankDate.milliseconds > 7.days)
            .also {
                if (it) {
                    dataStore().edit { preferences ->
                        preferences[KEY_LAST_RANK_DATE] = currentDate
                    }
                }
            }
    }

    /** 清除 last_rank_date 缓存，仅用于 Debug 设置页调试。 */
    suspend fun clearLastRankDateCache() {
        dataStore().edit { it.remove(KEY_LAST_RANK_DATE) }
    }

    fun fetchChatModes(): Flow<List<ChatMode>> {

        return channelFlow {
            launch { localDataSource.getChatModes().collect { send(it) } }
            launch {
                val result = remoteDataSource.getChatModes()

                if (result is HttpResult.Success) {
                    localDataSource.setChatModes(result.data)
                }
            }
        }
    }

    /** 获取聊天设置 */
    suspend fun getChatSettings(agentId: String): ChatSettingsResponse.ChatSettingRspData {
        return withContext(Dispatchers.IO) {
            when (val result = remoteDataSource.getChatSettings(agentId)) {
                is HttpResult.Success -> result.data
                is HttpResult.Failure -> throw Exception(result.message)
            }
        }
    }

    /** 更新聊天设置 */
    suspend fun updateChatSettings(agentId: String, settings: ChatSettingsReq) {
        return withContext(Dispatchers.IO) {
            when (val result = remoteDataSource.updateChatSettings(agentId, settings)) {
                is HttpResult.Success -> result.data
                is HttpResult.Failure -> throw Exception(result.message)
            }
        }
    }
}
