package com.ai.core.data.store

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.doublePreferencesKey
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.floatPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.core.stringSetPreferencesKey
import androidx.datastore.preferences.preferencesDataStoreFile
import java.util.concurrent.ConcurrentHashMap
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map

/**
 * DataStore 管理器，用于统一管理应用中的 DataStore Preferences 实例。
 *
 * ## 功能特性
 * - 提供 DataStore 实例的注册和复用机制，避免重复创建
 * - 支持按模块名称创建独立的 DataStore 实例
 * - 提供全局 DataStore 作为默认存储
 * - 使用线程安全的 ConcurrentHashMap 管理实例注册表
 *
 * ## 使用场景
 * - 需要持久化存储键值对数据时
 * - 需要按模块隔离存储数据时
 * - 需要响应式数据流（Flow）监听数据变化时
 *
 * ## 技术实现
 * - 使用 PreferenceDataStoreFactory 创建 DataStore 实例
 * - 数据存储在应用私有目录，文件格式为 Protocol Buffer
 * - 使用 IO 线程和 SupervisorJob 执行数据操作
 */
object DataStoreManager {

    /**
     * DataStore 实例注册表，key 为模块名称（null 表示全局 DataStore），value 为对应的 DataStore 实例 使用 ConcurrentHashMap
     * 确保线程安全
     */
    private val dataStoreRegistry = ConcurrentHashMap<String, DataStore<Preferences>>()

    /** 全局默认 DataStore 的 key，当 name 参数为 null 时使用此 key */
    private const val GLOBAL_DATASTORE_KEY = "global"

    /**
     * 获取或创建 DataStore 实例。
     *
     * 如果指定名称的 DataStore 已存在，则直接返回；否则创建新实例并注册到注册表中。
     *
     * ## 实现细节
     * - 使用 `getOrPut` 确保同一名称的 DataStore 只创建一次
     * - 使用 `applicationContext` 避免内存泄漏
     * - 使用 IO 线程和 SupervisorJob 执行数据操作
     * - 数据文件存储在应用私有目录，文件名为 `{name}.preferences_pb`
     *
     * @param context Android Context，用于获取应用上下文和文件目录
     * @param name 模块名称，用于区分不同的 DataStore 实例。如果为 null，则使用全局 DataStore
     * @return DataStore 实例，可用于存储和读取 Preferences 数据
     */
    fun getOrCreateDataStore(context: Context, name: String?): DataStore<Preferences> {
        return dataStoreRegistry.getOrPut(name ?: GLOBAL_DATASTORE_KEY) {
            PreferenceDataStoreFactory.create(
                corruptionHandler = null,
                migrations = listOf(),
                scope = CoroutineScope(Dispatchers.IO + SupervisorJob()),
            ) {
                context.applicationContext.preferencesDataStoreFile(name ?: GLOBAL_DATASTORE_KEY)
            }
        }
    }

    /**
     * 清空所有已注册的 DataStore 实例中的所有数据。
     *
     * ## 使用场景
     * - 用户退出登录时清除所有本地存储数据
     * - 应用重置功能
     * - 调试和测试场景
     *
     * ## 注意事项
     * - 此操作会清空所有模块的 DataStore 数据，请谨慎使用
     * - 操作是异步的，使用 suspend 函数确保数据完全清空
     * - 清空后 DataStore 实例仍然保留在注册表中，可以继续使用
     */
    suspend fun clearAll() {
        dataStoreRegistry.forEach { store -> store.value.clear() }
    }
}

/**
 * 获取指定名称的 DataStore 实例，如果名称为 null 则返回全局 DataStore。
 *
 * 这是获取 DataStore 实例的便捷方法，内部使用 `Utils.getApp()` 获取应用上下文。
 *
 * ## 使用示例
 *
 * ```kotlin
 * // 获取全局 DataStore
 * val globalStore = dataStore()
 *
 * // 获取指定模块的 DataStore
 * val userStore = dataStore("user_settings")
 *
 * // 使用扩展方法读写数据
 * userStore.putString("username", "张三")
 * val usernameFlow = userStore.getString("username")
 * ```
 *
 * @param name 模块名称，用于区分不同的 DataStore 实例。如果为 null，则返回全局 DataStore
 * @return DataStore 实例，可用于存储和读取 Preferences 数据
 */
fun dataStore(context: Context, name: String? = null): DataStore<Preferences> {
    return DataStoreManager.getOrCreateDataStore(context, name)
}

/**
 * 清空当前 DataStore 中的所有数据。
 *
 * ## 使用场景
 * - 清除某个模块的所有存储数据
 * - 重置用户设置
 *
 * ## 注意事项
 * - 此操作会清空当前 DataStore 的所有数据，请谨慎使用
 * - 操作是异步的，使用 suspend 函数确保数据完全清空
 */
suspend fun DataStore<Preferences>.clear() {
    edit { it.clear() }
}

/**
 * 向 DataStore 中写入指定类型的数据。
 *
 * ## 使用场景
 * - 需要存储自定义类型的数据时
 * - 需要类型安全的存储操作时
 *
 * ## 性能优化建议
 * - 如果同一 key 的查询很频繁，建议将 key 常量化，避免重复创建 Preferences.Key 对象
 *
 * ## 使用示例
 *
 * ```kotlin
 * val KEY_USERNAME = stringPreferencesKey("username")
 * dataStore.put(KEY_USERNAME, "张三")
 * ```
 *
 * @param key Preferences 键，用于标识存储的数据
 * @param value 要存储的值，类型必须与 key 的类型匹配
 */
suspend fun <T> DataStore<Preferences>.put(key: Preferences.Key<T>, value: T) = edit {
    it[key] = value
}

/**
 * 从 DataStore 中读取指定类型的数据，返回 Flow 流。
 *
 * ## 特性
 * - 返回 Flow，支持响应式编程
 * - 使用 `distinctUntilChanged()` 优化，只在值真正改变时发出新值
 * - 类型安全，编译时检查类型匹配
 *
 * ## 使用场景
 * - 需要监听数据变化时
 * - 在 Compose 中使用 `collectAsState()` 获取数据
 *
 * ## 性能优化建议
 * - 如果同一 key 的查询很频繁，建议将 key 常量化，避免重复创建 Preferences.Key 对象
 *
 * ## 使用示例
 *
 * ```kotlin
 * val KEY_USERNAME = stringPreferencesKey("username")
 * val usernameFlow = dataStore.get(KEY_USERNAME)
 *
 * // 在 Compose 中使用
 * val username by usernameFlow.collectAsState(initial = null)
 * ```
 *
 * @param key Preferences 键，用于标识要读取的数据
 * @return Flow<T?>，当数据不存在时返回 null
 */
fun <T> DataStore<Preferences>.get(key: Preferences.Key<T>) =
    data.map { it[key] }.distinctUntilChanged()

/**
 * 从 DataStore 中读取 Int 类型的数据，返回 Flow 流。
 *
 * ## 特性
 * - 返回 Flow<Int?>，当数据不存在时返回 null
 * - 使用 `distinctUntilChanged()` 优化，只在值真正改变时发出新值
 *
 * ## 使用示例
 *
 * ```kotlin
 * val ageFlow = dataStore.getInt("user_age")
 * // 在 Compose 中使用
 * val age by ageFlow.collectAsState(initial = null)
 * ```
 *
 * @param key 存储键名
 * @return Flow<Int?>，数据流
 */
fun DataStore<Preferences>.getInt(key: String) =
    data.map { it[intPreferencesKey(key)] }.distinctUntilChanged()

/**
 * 向 DataStore 中写入 Int 类型的数据。
 *
 * ## 使用示例
 *
 * ```kotlin
 * dataStore.putInt("user_age", 25)
 * ```
 *
 * @param key 存储键名
 * @param value 要存储的 Int 值
 */
suspend fun DataStore<Preferences>.putInt(key: String, value: Int) = edit {
    it[intPreferencesKey(key)] = value
}

/**
 * 从 DataStore 中读取 String 类型的数据，返回 Flow 流。
 *
 * ## 特性
 * - 返回 Flow<String?>，当数据不存在时返回 null
 * - 使用 `distinctUntilChanged()` 优化，只在值真正改变时发出新值
 *
 * ## 使用示例
 *
 * ```kotlin
 * val usernameFlow = dataStore.getString("username")
 * // 在 Compose 中使用
 * val username by usernameFlow.collectAsState(initial = null)
 * ```
 *
 * @param key 存储键名
 * @return Flow<String?>，数据流
 */
fun DataStore<Preferences>.getString(key: String) =
    data.map { it[stringPreferencesKey(key)] }.distinctUntilChanged()

/**
 * 向 DataStore 中写入 String 类型的数据。
 *
 * ## 使用示例
 *
 * ```kotlin
 * dataStore.putString("username", "张三")
 * ```
 *
 * @param key 存储键名
 * @param value 要存储的 String 值
 */
suspend fun DataStore<Preferences>.putString(key: String, value: String) = edit {
    it[stringPreferencesKey(key)] = value
}

/**
 * 从 DataStore 中读取 Long 类型的数据，返回 Flow 流。
 *
 * ## 特性
 * - 返回 Flow<Long?>，当数据不存在时返回 null
 * - 使用 `distinctUntilChanged()` 优化，只在值真正改变时发出新值
 *
 * ## 使用场景
 * - 存储时间戳
 * - 存储大整数
 *
 * ## 使用示例
 *
 * ```kotlin
 * val timestampFlow = dataStore.getLong("last_login_time")
 * ```
 *
 * @param key 存储键名
 * @return Flow<Long?>，数据流
 */
fun DataStore<Preferences>.getLong(key: String) =
    data.map { it[longPreferencesKey(key)] }.distinctUntilChanged()

/**
 * 向 DataStore 中写入 Long 类型的数据。
 *
 * ## 使用示例
 *
 * ```kotlin
 * dataStore.putLong("last_login_time", System.currentTimeMillis())
 * ```
 *
 * @param key 存储键名
 * @param value 要存储的 Long 值
 */
suspend fun DataStore<Preferences>.putLong(key: String, value: Long) = edit {
    it[longPreferencesKey(key)] = value
}

/**
 * 从 DataStore 中读取 Float 类型的数据，返回 Flow 流。
 *
 * ## 特性
 * - 返回 Flow<Float?>，当数据不存在时返回 null
 * - 使用 `distinctUntilChanged()` 优化，只在值真正改变时发出新值
 *
 * ## 使用示例
 *
 * ```kotlin
 * val ratingFlow = dataStore.getFloat("user_rating")
 * ```
 *
 * @param key 存储键名
 * @return Flow<Float?>，数据流
 */
fun DataStore<Preferences>.getFloat(key: String) =
    data.map { it[floatPreferencesKey(key)] }.distinctUntilChanged()

/**
 * 向 DataStore 中写入 Float 类型的数据。
 *
 * ## 使用示例
 *
 * ```kotlin
 * dataStore.putFloat("user_rating", 4.5f)
 * ```
 *
 * @param key 存储键名
 * @param value 要存储的 Float 值
 */
suspend fun DataStore<Preferences>.putFloat(key: String, value: Float) = edit {
    it[floatPreferencesKey(key)] = value
}

/**
 * 从 DataStore 中读取 Double 类型的数据，返回 Flow 流。
 *
 * ## 特性
 * - 返回 Flow<Double?>，当数据不存在时返回 null
 * - 使用 `distinctUntilChanged()` 优化，只在值真正改变时发出新值
 *
 * ## 使用示例
 *
 * ```kotlin
 * val priceFlow = dataStore.getDouble("product_price")
 * ```
 *
 * @param key 存储键名
 * @return Flow<Double?>，数据流
 */
fun DataStore<Preferences>.getDouble(key: String) =
    data.map { it[doublePreferencesKey(key)] }.distinctUntilChanged()

/**
 * 向 DataStore 中写入 Double 类型的数据。
 *
 * ## 使用示例
 *
 * ```kotlin
 * dataStore.putDouble("product_price", 99.99)
 * ```
 *
 * @param key 存储键名
 * @param value 要存储的 Double 值
 */
suspend fun DataStore<Preferences>.putDouble(key: String, value: Double) = edit {
    it[doublePreferencesKey(key)] = value
}

/**
 * 从 DataStore 中读取 Boolean 类型的数据，返回 Flow 流。
 *
 * ## 特性
 * - 返回 Flow<Boolean?>，当数据不存在时返回 null
 * - 使用 `distinctUntilChanged()` 优化，只在值真正改变时发出新值
 *
 * ## 使用场景
 * - 存储开关状态
 * - 存储功能启用/禁用标志
 *
 * ## 使用示例
 *
 * ```kotlin
 * val isEnabledFlow = dataStore.getBoolean("feature_enabled")
 * // 在 Compose 中使用
 * val isEnabled by isEnabledFlow.collectAsState(initial = false)
 * ```
 *
 * @param key 存储键名
 * @return Flow<Boolean?>，数据流
 */
fun DataStore<Preferences>.getBoolean(key: String) =
    data.map { it[booleanPreferencesKey(key)] }.distinctUntilChanged()

/**
 * 向 DataStore 中写入 Boolean 类型的数据。
 *
 * ## 使用示例
 *
 * ```kotlin
 * dataStore.putBoolean("feature_enabled", true)
 * ```
 *
 * @param key 存储键名
 * @param value 要存储的 Boolean 值
 */
suspend fun DataStore<Preferences>.putBoolean(key: String, value: Boolean) = edit {
    it[booleanPreferencesKey(key)] = value
}

/**
 * 从 DataStore 中读取 Set<String> 类型的数据，返回 Flow 流。
 *
 * ## 特性
 * - 返回 Flow<Set<String>?>，当数据不存在时返回 null
 * - 使用 `distinctUntilChanged()` 优化，只在值真正改变时发出新值
 *
 * ## 使用场景
 * - 存储标签列表
 * - 存储收藏项 ID 集合
 * - 存储多选选项
 *
 * ## 使用示例
 *
 * ```kotlin
 * val tagsFlow = dataStore.getStringSet("user_tags")
 * // 在 Compose 中使用
 * val tags by tagsFlow.collectAsState(initial = emptySet())
 * ```
 *
 * @param key 存储键名
 * @return Flow<Set<String>?>，数据流
 */
fun DataStore<Preferences>.getStringSet(key: String) =
    data.map { it[stringSetPreferencesKey(key)] }.distinctUntilChanged()

/**
 * 向 DataStore 中写入 Set<String> 类型的数据。
 *
 * ## 使用示例
 *
 * ```kotlin
 * dataStore.putStringSet("user_tags", setOf("标签1", "标签2", "标签3"))
 * ```
 *
 * @param key 存储键名
 * @param value 要存储的 Set<String> 值
 */
suspend fun DataStore<Preferences>.putStringSet(key: String, value: Set<String>) = edit {
    it[stringSetPreferencesKey(key)] = value
}
