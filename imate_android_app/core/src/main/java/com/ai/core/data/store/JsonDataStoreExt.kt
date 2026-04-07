package com.ai.core.data.store

import androidx.datastore.core.Serializer
import androidx.datastore.dataStore
import java.io.InputStream
import java.io.OutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.serializer

/**
 * 创建基于 JSON 序列化的 DataStore 委托属性。
 *
 * 该扩展函数简化了 Jetpack DataStore 的创建过程，自动处理 JSON 序列化/反序列化。 使用 Kotlin Serialization
 * 进行数据转换，支持任意可序列化的数据类型。
 *
 * 使用示例:
 * ```kotlin
 * @Serializable
 * data class UserSettings(val theme: String = "light", val fontSize: Int = 14)
 *
 * // 在 Context 扩展中使用
 * val Context.userSettingsStore by jsonDataStore("user_settings.json", UserSettings())
 * ```
 *
 * @param T 要存储的数据类型，必须使用 @Serializable 注解标记
 * @param fileName DataStore 文件名，存储在应用私有目录下
 * @param defaultValue 当文件不存在或读取失败时返回的默认值
 * @return DataStore 委托属性，可用于 Context 扩展
 */
inline fun <reified T : Any> jsonDataStore(fileName: String, defaultValue: T) =
    dataStore<T>(
        fileName = fileName,
        serializer =
            object : Serializer<T> {
                private val ser = Json.serializersModule.serializer<T>()

                override val defaultValue: T = defaultValue

                override suspend fun readFrom(input: InputStream): T =
                    Json.decodeFromString(ser, input.readBytes().decodeToString())

                override suspend fun writeTo(t: T, output: OutputStream) {
                    withContext(Dispatchers.IO) {
                        output.write(Json.encodeToString(ser, t).encodeToByteArray())
                    }
                }
            },
    )
