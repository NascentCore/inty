package ai.sxwl.android.data.store

import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.GlobalScope
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

/**
 * DataStore 读写实现：8 个低优先级用户级设置项（不迁移 MMKV 旧值，无值时用默认值）。
 *
 * 提供同步 get 与异步 set，内部通过内存缓存 + runBlocking 首值加载满足 [IntySetting] 门面的同步读需求；
 * 用户切换时调用 [onUserChanged] 失效缓存。
 */
object IntySettingsDataStore {

    private const val PREFIX_USER_STORE = "inty_settings_user_"
    private const val KEY_CHAT_FONT_SIZE_SP = "chat_font_size_sp"
    private const val KEY_CHAT_MODEL_ID = "chat_model_id"
    private const val KEY_CHAT_LIST_FULL_SCREEN = "chat_list_full_screen"
    private const val KEY_AUTO_PLAY_ANIMATION = "auto_play_animation"
    private const val KEY_TEXT_STREAMING = "text_streaming"
    private const val KEY_SHOW_SCENE_ACTION_BUTTON = "show_scene_action_button"
    private const val KEY_SHOW_KEEP_TALKING = "show_keep_talking"
    private const val KEY_AUTO_PLAY_AUDIO = "auto_play_audio"

    private const val DEFAULT_CHAT_FONT_SIZE_SP = 14f
    private const val DEFAULT_CHAT_MODEL_ID = "gemini_3_flash"
    private const val DEFAULT_CHAT_LIST_FULL_SCREEN = false
    private const val DEFAULT_AUTO_PLAY_ANIMATION = true
    private const val DEFAULT_TEXT_STREAMING = true
    private const val DEFAULT_SHOW_SCENE_ACTION_BUTTON = false
    private const val DEFAULT_SHOW_KEEP_TALKING = false
    private const val DEFAULT_AUTO_PLAY_AUDIO = true

    private val lock = Any()
    private var cachedUid: String? = null
    private var cache = Cache()

    private data class Cache(
        var chatFontSizeSp: Float = DEFAULT_CHAT_FONT_SIZE_SP,
        var chatModelId: String = DEFAULT_CHAT_MODEL_ID,
        var chatListFullScreen: Boolean = DEFAULT_CHAT_LIST_FULL_SCREEN,
        var autoPlayAnimation: Boolean = DEFAULT_AUTO_PLAY_ANIMATION,
        var textStreaming: Boolean = DEFAULT_TEXT_STREAMING,
        var showSceneActionButton: Boolean = DEFAULT_SHOW_SCENE_ACTION_BUTTON,
        var showKeepTalking: Boolean = DEFAULT_SHOW_KEEP_TALKING,
        var autoPlayAudio: Boolean = DEFAULT_AUTO_PLAY_AUDIO,
    )

    private fun store(uid: String): DataStore<Preferences> {
        return dataStore("$PREFIX_USER_STORE$uid")
    }

    /** 失效缓存，使用于用户切换后，下次 get 会按新 uid 重新加载。 */
    fun onUserChanged() {
        synchronized(lock) {
            cachedUid = null
        }
    }

    private fun ensureCache(uid: String) {
        synchronized(lock) {
            if (cachedUid == uid) return
            runBlocking {
                val prefs = store(uid).data.first()
                cache = Cache(
                    chatFontSizeSp = prefs[floatPreferencesKey(KEY_CHAT_FONT_SIZE_SP)] ?: DEFAULT_CHAT_FONT_SIZE_SP,
                    chatModelId = prefs[stringPreferencesKey(KEY_CHAT_MODEL_ID)] ?: DEFAULT_CHAT_MODEL_ID,
                    chatListFullScreen = prefs[booleanPreferencesKey(KEY_CHAT_LIST_FULL_SCREEN)] ?: DEFAULT_CHAT_LIST_FULL_SCREEN,
                    autoPlayAnimation = prefs[booleanPreferencesKey(KEY_AUTO_PLAY_ANIMATION)] ?: DEFAULT_AUTO_PLAY_ANIMATION,
                    textStreaming = prefs[booleanPreferencesKey(KEY_TEXT_STREAMING)] ?: DEFAULT_TEXT_STREAMING,
                    showSceneActionButton = prefs[booleanPreferencesKey(KEY_SHOW_SCENE_ACTION_BUTTON)] ?: DEFAULT_SHOW_SCENE_ACTION_BUTTON,
                    showKeepTalking = prefs[booleanPreferencesKey(KEY_SHOW_KEEP_TALKING)] ?: DEFAULT_SHOW_KEEP_TALKING,
                    autoPlayAudio = prefs[booleanPreferencesKey(KEY_AUTO_PLAY_AUDIO)] ?: DEFAULT_AUTO_PLAY_AUDIO,
                )
                cachedUid = uid
            }
        }
    }

    fun getChatFontSizeSp(uid: String): Float {
        ensureCache(uid)
        return synchronized(lock) { cache.chatFontSizeSp }
    }

    fun setChatFontSizeSp(uid: String, value: Float) {
        ensureCache(uid)
        synchronized(lock) { cache.chatFontSizeSp = value }
        GlobalScope.launch(Dispatchers.IO) { store(uid).putFloat(KEY_CHAT_FONT_SIZE_SP, value) }
    }

    fun getChatModelId(uid: String): String {
        ensureCache(uid)
        return synchronized(lock) { cache.chatModelId }
    }

    fun setChatModelId(uid: String, value: String) {
        ensureCache(uid)
        synchronized(lock) { cache.chatModelId = value }
        GlobalScope.launch(Dispatchers.IO) { store(uid).putString(KEY_CHAT_MODEL_ID, value) }
    }

    fun getChatListFullScreen(uid: String): Boolean {
        ensureCache(uid)
        return synchronized(lock) { cache.chatListFullScreen }
    }

    fun setChatListFullScreen(uid: String, value: Boolean) {
        ensureCache(uid)
        synchronized(lock) { cache.chatListFullScreen = value }
        GlobalScope.launch(Dispatchers.IO) { store(uid).putBoolean(KEY_CHAT_LIST_FULL_SCREEN, value) }
    }

    fun getAutoPlayAnimation(uid: String): Boolean {
        ensureCache(uid)
        return synchronized(lock) { cache.autoPlayAnimation }
    }

    fun setAutoPlayAnimation(uid: String, value: Boolean) {
        ensureCache(uid)
        synchronized(lock) { cache.autoPlayAnimation = value }
        GlobalScope.launch(Dispatchers.IO) { store(uid).putBoolean(KEY_AUTO_PLAY_ANIMATION, value) }
    }

    fun getTextStreaming(uid: String): Boolean {
        ensureCache(uid)
        return synchronized(lock) { cache.textStreaming }
    }

    fun setTextStreaming(uid: String, value: Boolean) {
        ensureCache(uid)
        synchronized(lock) { cache.textStreaming = value }
        GlobalScope.launch(Dispatchers.IO) { store(uid).putBoolean(KEY_TEXT_STREAMING, value) }
    }

    fun getShowSceneActionButton(uid: String): Boolean {
        ensureCache(uid)
        return synchronized(lock) { cache.showSceneActionButton }
    }

    fun setShowSceneActionButton(uid: String, value: Boolean) {
        ensureCache(uid)
        synchronized(lock) { cache.showSceneActionButton = value }
        GlobalScope.launch(Dispatchers.IO) { store(uid).putBoolean(KEY_SHOW_SCENE_ACTION_BUTTON, value) }
    }

    fun getShowKeepTalking(uid: String): Boolean {
        ensureCache(uid)
        return synchronized(lock) { cache.showKeepTalking }
    }

    fun setShowKeepTalking(uid: String, value: Boolean) {
        ensureCache(uid)
        synchronized(lock) { cache.showKeepTalking = value }
        GlobalScope.launch(Dispatchers.IO) { store(uid).putBoolean(KEY_SHOW_KEEP_TALKING, value) }
    }

    fun getAutoPlayAudio(uid: String): Boolean {
        ensureCache(uid)
        return synchronized(lock) { cache.autoPlayAudio }
    }

    fun setAutoPlayAudio(uid: String, value: Boolean) {
        ensureCache(uid)
        synchronized(lock) { cache.autoPlayAudio = value }
        GlobalScope.launch(Dispatchers.IO) { store(uid).putBoolean(KEY_AUTO_PLAY_AUDIO, value) }
    }
}
