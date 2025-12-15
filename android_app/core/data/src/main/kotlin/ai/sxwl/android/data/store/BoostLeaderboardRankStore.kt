package ai.sxwl.android.data.store

// CREATED_BY_AGENT

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.emptyPreferences
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.architecture.httplib.utils.MoshiUtils
import java.io.IOException
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map

private val Context.boostLeaderboardRankDataStore by
    preferencesDataStore(name = "boost_leaderboard_rank_cache")

data class BoostLeaderboardRankCache(
    val updatedAtMs: Long = 0,
    val ranksByAgentId: Map<String, Int> = emptyMap(),
)

/** 使用 DataStore 缓存上一版 Boost 排行榜的名次，用于计算趋势。 */
object BoostLeaderboardRankStore {

    private val CACHE_KEY = stringPreferencesKey("boost_leaderboard_rank_cache_json")

    suspend fun readCache(context: Context): BoostLeaderboardRankCache {
        val json =
            context.boostLeaderboardRankDataStore.data
                .catch { exception ->
                    if (exception is IOException) {
                        emit(emptyPreferences())
                    } else {
                        throw exception
                    }
                }
                .map { prefs -> prefs[CACHE_KEY].orEmpty() }
                .first()

        if (json.isBlank()) return BoostLeaderboardRankCache()
        return runCatching { MoshiUtils.fromJson<BoostLeaderboardRankCache>(json) }
            .getOrNull()
            ?: BoostLeaderboardRankCache()
    }

    suspend fun saveCache(context: Context, cache: BoostLeaderboardRankCache) {
        val json = MoshiUtils.toJson(cache)
        context.boostLeaderboardRankDataStore.edit { prefs -> prefs[CACHE_KEY] = json }
    }
}

