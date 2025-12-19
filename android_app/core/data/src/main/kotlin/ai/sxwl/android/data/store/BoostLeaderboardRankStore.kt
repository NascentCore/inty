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

/**
 * DataStore Preferences 扩展属性，用于创建或获取 Boost 排行榜排名缓存的数据存储实例。
 *
 * 技术架构说明：
 * - 使用 Android DataStore Preferences API 进行键值对存储
 * - DataStore 是 Android 推荐的现代数据持久化方案，替代 SharedPreferences
 * - 通过委托属性（by preferencesDataStore）实现单例模式，确保每个 Context 只有一个实例
 * - 数据存储在应用私有目录，文件名为 "boost_leaderboard_rank_cache.preferences_pb"
 */
private val Context.boostLeaderboardRankDataStore by
    preferencesDataStore(name = "boost_leaderboard_rank_cache")

/**
 * Boost 排行榜排名缓存数据模型。
 *
 * @param updatedAtMs 缓存更新时间戳（毫秒），用于追踪缓存的新鲜度
 * @param ranksByAgentId 角色ID到排名的映射表，key 为 agentId，value 为该角色的排名（数字越小排名越靠前）
 */
data class BoostLeaderboardRankCache(
    val updatedAtMs: Long = 0,
    val ranksByAgentId: Map<String, Int> = emptyMap(),
)

/**
 * Boost 排行榜排名缓存存储管理器。
 *
 * ## 工作原理
 *
 * 该 Store 用于持久化保存 Boost 排行榜的排名快照，支持排行榜趋势计算功能。 工作流程如下：
 * 1. **读取缓存**：用户打开排行榜时，调用 `readCache()` 读取上次保存的排名数据
 * 2. **计算趋势**：将当前排名与缓存中的历史排名进行比较，计算排名变化趋势（上升/下降/持平）
 * 3. **保存缓存**：获取最新排行榜数据后，调用 `saveCache()` 保存当前排名作为新的基准
 *
 * ## 技术架构
 *
 * ### 存储层
 * - **DataStore Preferences**：使用 Android DataStore Preferences API 进行键值对存储
 *     - 异步、类型安全、支持 Flow 响应式编程
 *     - 数据以 Protocol Buffer 格式存储在应用私有目录
 *     - 相比 SharedPreferences，提供更好的数据一致性和错误处理
 *
 * ### 序列化层
 * - **Moshi**：使用 Moshi JSON 库进行对象序列化/反序列化
 *     - 将 `BoostLeaderboardRankCache` 对象序列化为 JSON 字符串存储
 *     - 读取时将 JSON 字符串反序列化为对象
 *     - 支持类型安全的 JSON 处理
 *
 * ### 异步处理
 * - **Kotlin Coroutines**：所有操作均为 suspend 函数，支持协程异步执行
 * - **Flow API**：使用 Flow 进行响应式数据读取
 *     - `.catch`：捕获 IOException 异常，返回空 Preferences（首次使用时）
 *     - `.map`：将 Preferences 中的 JSON 字符串提取出来
 *     - `.first()`：获取 Flow 的第一个值（即当前存储的数据）
 *
 * ### 错误处理
 * - 读取时如果发生 IOException（如文件不存在），返回空的 `BoostLeaderboardRankCache`
 * - JSON 反序列化失败时，返回空的 `BoostLeaderboardRankCache`，避免应用崩溃
 * - 其他异常会向上抛出，由调用方处理
 *
 * ## 使用场景
 *
 * 在 `BoostLeaderboardActivity` 中使用：
 * - 每次加载排行榜时，先读取历史排名缓存
 * - 使用 `BoostLeaderboardTrendCalculator` 比较当前排名和历史排名，计算趋势
 * - 加载完成后，保存当前排名作为新的缓存基准
 *
 * 这样用户每次打开排行榜时，都能看到每个角色的排名变化趋势（上升/下降/持平）。
 */
object BoostLeaderboardRankStore {

    /** DataStore Preferences 中的键名，用于存储序列化后的 JSON 字符串。 */
    private val CACHE_KEY = stringPreferencesKey("boost_leaderboard_rank_cache_json")

    /**
     * 从 DataStore 读取排行榜排名缓存。
     *
     * ## 实现细节
     * 1. **Flow 数据流处理**：
     *     - `boostLeaderboardRankDataStore.data` 返回 `Flow<Preferences>`
     *     - 使用 `.catch` 捕获 IOException（首次使用时文件不存在）
     *     - 使用 `.map` 提取 JSON 字符串
     *     - 使用 `.first()` 获取当前值（Flow 是冷流，需要终端操作符触发）
     * 2. **错误处理**：
     *     - IOException：返回空缓存（首次使用或文件损坏）
     *     - JSON 解析失败：返回空缓存（数据格式不兼容）
     *     - 其他异常：向上抛出，由调用方处理
     * 3. **返回值**：
     *     - 如果缓存不存在或解析失败，返回空的 `BoostLeaderboardRankCache()`
     *     - 否则返回反序列化后的缓存对象
     *
     * @param context Android Context，用于访问 DataStore
     * @return 排行榜排名缓存对象，如果不存在则返回空对象
     */
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
        return runCatching { MoshiUtils.fromJson<BoostLeaderboardRankCache>(json) }.getOrNull()
            ?: BoostLeaderboardRankCache()
    }

    /**
     * 将排行榜排名缓存保存到 DataStore。
     *
     * ## 实现细节
     * 1. **序列化**：使用 Moshi 将 `BoostLeaderboardRankCache` 对象序列化为 JSON 字符串
     * 2. **存储**：使用 DataStore 的 `edit` 函数进行事务性写入
     *     - `edit` 是 suspend 函数，支持协程异步执行
     *     - 内部使用事务机制，确保数据一致性
     *     - 如果写入失败，会自动回滚
     *
     * ## 性能考虑
     * - DataStore 的写入操作是异步的，不会阻塞主线程
     * - 使用事务机制，确保多线程环境下的数据安全
     * - 数据以 Protocol Buffer 格式存储，相比 JSON 文件更高效
     *
     * @param context Android Context，用于访问 DataStore
     * @param cache 要保存的排行榜排名缓存对象
     */
    suspend fun saveCache(context: Context, cache: BoostLeaderboardRankCache) {
        val json = MoshiUtils.toJson(cache)
        context.boostLeaderboardRankDataStore.edit { prefs -> prefs[CACHE_KEY] = json }
    }
}
