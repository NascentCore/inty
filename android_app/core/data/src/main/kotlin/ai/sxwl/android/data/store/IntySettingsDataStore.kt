package ai.sxwl.android.data.store

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

/**
 * DataStore 读写实现：8 个低优先级用户级设置项（不迁移 MMKV 旧值，无值时用默认值）。
 *
 * 提供同步 get 与异步 set，内部通过内存缓存 + runBlocking 首值加载满足 [IntySetting] 门面的同步读需求； 用户切换时调用 [onUserChanged]
 * 失效缓存。 为避免 set 后异步写未完成时 onUserChanged 或 ensureCacheUnderLock 重载从 DataStore 读到旧值，对每个 uid 记录未完成的写
 * Job 列表， 在 [onUserChanged] 与 [ensureCacheUnderLock] 重载前等待该 uid 全部写完成。
 */
object IntySettingsDataStore {

    private const val PREFIX_USER_STORE = "inty_settings_user_"
    private const val KEY_CHAT_FONT_SIZE_SP = "chat_font_size_sp"
    private const val KEY_CHAT_MODEL_ID = "chat_model_id"
    private const val KEY_CHAT_LIST_FULL_SCREEN = "chat_list_full_screen"
    private const val KEY_AUTO_PLAY_ANIMATION = "auto_play_animation"
    private const val KEY_TEXT_STREAMING = "text_streaming"
    private const val KEY_SHOW_SCENE_ACTION_BUTTON = "show_scene_action_button"
    private const val KEY_SEND_UX_UI_GESTURE_SIGNALS = "send_ux_ui_gesture_signals"
    private const val KEY_SHOW_KEEP_TALKING = "show_keep_talking"
    private const val KEY_AUTO_PLAY_AUDIO = "auto_play_audio"

    private const val DEFAULT_CHAT_FONT_SIZE_SP = 14f
    private const val DEFAULT_CHAT_MODEL_ID = "gemini_3_flash"
    private const val DEFAULT_CHAT_LIST_FULL_SCREEN = false
    private const val DEFAULT_AUTO_PLAY_ANIMATION = true
    private const val DEFAULT_TEXT_STREAMING = true
    private const val DEFAULT_SHOW_SCENE_ACTION_BUTTON = false
    private const val DEFAULT_SEND_UX_UI_GESTURE_SIGNALS = false
    private const val DEFAULT_SHOW_KEEP_TALKING = false
    private const val DEFAULT_AUTO_PLAY_AUDIO = true

    private val lock = Any()
    private var cachedUid: String? = null
    private var cache = Cache()
    /**
     * 每个 uid 未完成的 DataStore 写 Job 列表；onUserChanged/ensureCacheUnderLock 重载前会 join 该 uid 全部 Job
     * 以免读到未落盘的值。
     */
    private val pendingWrites = mutableMapOf<String, MutableList<Job>>()

    private data class Cache(
        var chatFontSizeSp: Float = DEFAULT_CHAT_FONT_SIZE_SP,
        var chatModelId: String = DEFAULT_CHAT_MODEL_ID,
        var chatListFullScreen: Boolean = DEFAULT_CHAT_LIST_FULL_SCREEN,
        var autoPlayAnimation: Boolean = DEFAULT_AUTO_PLAY_ANIMATION,
        var textStreaming: Boolean = DEFAULT_TEXT_STREAMING,
        var showSceneActionButton: Boolean = DEFAULT_SHOW_SCENE_ACTION_BUTTON,
        var sendUxUiGestureSignals: Boolean = DEFAULT_SEND_UX_UI_GESTURE_SIGNALS,
        var showKeepTalking: Boolean = DEFAULT_SHOW_KEEP_TALKING,
        var autoPlayAudio: Boolean = DEFAULT_AUTO_PLAY_AUDIO,
    )

    private fun store(uid: String): DataStore<Preferences> {
        return dataStore("$PREFIX_USER_STORE$uid")
    }

    /** 失效缓存，使用于用户切换后，下次 get 会按新 uid 重新加载。先等待当前缓存 uid 的未完成写再失效，避免丢写。 */
    fun onUserChanged() {
        synchronized(lock) {
            cachedUid?.let { uid ->
                pendingWrites[uid]?.forEach { runBlocking { it.join() } }
                pendingWrites.remove(uid)
            }
            cachedUid = null
        }
    }

    /** 必须在已持有 lock 时调用；保证返回时 cache 对应 uid，且仍持有 lock。 */
    private fun ensureCacheUnderLock(uid: String) {
        if (cachedUid == uid) return
        pendingWrites[uid]?.forEach { runBlocking { it.join() } }
        pendingWrites.remove(uid)
        runBlocking {
            val prefs = store(uid).data.first()
            cache =
                Cache(
                    chatFontSizeSp =
                        prefs[floatPreferencesKey(KEY_CHAT_FONT_SIZE_SP)]
                            ?: DEFAULT_CHAT_FONT_SIZE_SP,
                    chatModelId =
                        prefs[stringPreferencesKey(KEY_CHAT_MODEL_ID)] ?: DEFAULT_CHAT_MODEL_ID,
                    chatListFullScreen =
                        prefs[booleanPreferencesKey(KEY_CHAT_LIST_FULL_SCREEN)]
                            ?: DEFAULT_CHAT_LIST_FULL_SCREEN,
                    autoPlayAnimation =
                        prefs[booleanPreferencesKey(KEY_AUTO_PLAY_ANIMATION)]
                            ?: DEFAULT_AUTO_PLAY_ANIMATION,
                    textStreaming =
                        prefs[booleanPreferencesKey(KEY_TEXT_STREAMING)] ?: DEFAULT_TEXT_STREAMING,
                    showSceneActionButton =
                        prefs[booleanPreferencesKey(KEY_SHOW_SCENE_ACTION_BUTTON)]
                            ?: DEFAULT_SHOW_SCENE_ACTION_BUTTON,
                    sendUxUiGestureSignals =
                        prefs[booleanPreferencesKey(KEY_SEND_UX_UI_GESTURE_SIGNALS)]
                            ?: DEFAULT_SEND_UX_UI_GESTURE_SIGNALS,
                    showKeepTalking =
                        prefs[booleanPreferencesKey(KEY_SHOW_KEEP_TALKING)]
                            ?: DEFAULT_SHOW_KEEP_TALKING,
                    autoPlayAudio =
                        prefs[booleanPreferencesKey(KEY_AUTO_PLAY_AUDIO)] ?: DEFAULT_AUTO_PLAY_AUDIO,
                )
            cachedUid = uid
        }
    }

    /** 写完成后从 pendingWrites 移除该 job，避免同 uid 反复写导致列表无限增长。 */
    private fun registerPendingWrite(uid: String, job: Job) {
        val list = pendingWrites.getOrPut(uid) { mutableListOf() }
        list.add(job)
        job.invokeOnCompletion {
            synchronized(lock) {
                pendingWrites[uid]?.remove(job)
                if (pendingWrites[uid].isNullOrEmpty()) pendingWrites.remove(uid)
            }
        }
    }

    fun getChatFontSizeSp(uid: String): Float {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.chatFontSizeSp
        }
    }

    fun setChatFontSizeSp(uid: String, value: Float) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.chatFontSizeSp = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putFloat(KEY_CHAT_FONT_SIZE_SP, value)
                }
            registerPendingWrite(uid, job)
        }
    }

    fun getChatModelId(uid: String): String {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.chatModelId
        }
    }

    fun setChatModelId(uid: String, value: String) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.chatModelId = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putString(KEY_CHAT_MODEL_ID, value)
                }
            registerPendingWrite(uid, job)
        }
    }

    fun getChatListFullScreen(uid: String): Boolean {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.chatListFullScreen
        }
    }

    fun setChatListFullScreen(uid: String, value: Boolean) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.chatListFullScreen = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putBoolean(KEY_CHAT_LIST_FULL_SCREEN, value)
                }
            registerPendingWrite(uid, job)
        }
    }

    fun getAutoPlayAnimation(uid: String): Boolean {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.autoPlayAnimation
        }
    }

    fun setAutoPlayAnimation(uid: String, value: Boolean) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.autoPlayAnimation = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putBoolean(KEY_AUTO_PLAY_ANIMATION, value)
                }
            registerPendingWrite(uid, job)
        }
    }

    fun getTextStreaming(uid: String): Boolean {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.textStreaming
        }
    }

    fun setTextStreaming(uid: String, value: Boolean) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.textStreaming = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putBoolean(KEY_TEXT_STREAMING, value)
                }
            registerPendingWrite(uid, job)
        }
    }

    fun getShowSceneActionButton(uid: String): Boolean {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.showSceneActionButton
        }
    }

    fun setShowSceneActionButton(uid: String, value: Boolean) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.showSceneActionButton = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putBoolean(KEY_SHOW_SCENE_ACTION_BUTTON, value)
                }
            registerPendingWrite(uid, job)
        }
    }

    fun getSendUxUiGestureSignals(uid: String): Boolean {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.sendUxUiGestureSignals
        }
    }

    fun setSendUxUiGestureSignals(uid: String, value: Boolean) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.sendUxUiGestureSignals = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putBoolean(KEY_SEND_UX_UI_GESTURE_SIGNALS, value)
                }
            registerPendingWrite(uid, job)
        }
    }

    fun getShowKeepTalking(uid: String): Boolean {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.showKeepTalking
        }
    }

    fun setShowKeepTalking(uid: String, value: Boolean) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.showKeepTalking = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putBoolean(KEY_SHOW_KEEP_TALKING, value)
                }
            registerPendingWrite(uid, job)
        }
    }

    fun getAutoPlayAudio(uid: String): Boolean {
        return synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.autoPlayAudio
        }
    }

    fun setAutoPlayAudio(uid: String, value: Boolean) {
        synchronized(lock) {
            ensureCacheUnderLock(uid)
            cache.autoPlayAudio = value
            val job =
                GlobalScope.launch(Dispatchers.IO) {
                    store(uid).putBoolean(KEY_AUTO_PLAY_AUDIO, value)
                }
            registerPendingWrite(uid, job)
        }
    }
}
