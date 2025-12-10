package ai.sxwl.android.data.store

// CREATED_BY_AGENT

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import java.io.IOException
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.map

private val Context.personaPreferenceDataStore by preferencesDataStore(name = "persona_settings")

/**
 * 使用 DataStore 保存聊天抽屉中的个性化偏好文本。
 */
object PersonaPreferenceStore {

    private val PREFERENCE_KEY = stringPreferencesKey("user_persona_preference")

    /**
     * 获取偏好文本 Flow。
     */
    fun preferenceFlow(context: Context): Flow<String> {
        return context.personaPreferenceDataStore.data
            .catch { exception ->
                if (exception is IOException) {
                    emit(emptyPreferences())
                } else {
                    throw exception
                }
            }
            .map { prefs -> prefs[PREFERENCE_KEY].orEmpty() }
    }

    /**
     * 保存偏好文本，空值时移除键。
     */
    suspend fun savePreference(context: Context, value: String) {
        context.personaPreferenceDataStore.edit { prefs ->
            if (value.isBlank()) {
                prefs.remove(PREFERENCE_KEY)
            } else {
                prefs[PREFERENCE_KEY] = value
            }
        }
    }
}
