/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost

import android.content.Context
import androidx.datastore.core.Serializer
import androidx.datastore.dataStore
import java.io.InputStream
import java.io.OutputStream
import kotlinx.serialization.SerializationException
import kotlinx.serialization.json.Json

/** 负责 BoostStateSnapshot 的序列化 / 反序列化。 */
object BoostStateSerializer : Serializer<BoostStateSnapshot> {

    private val json =
        Json {
            encodeDefaults = true
            ignoreUnknownKeys = true
        }

    override val defaultValue: BoostStateSnapshot = BoostStateSnapshot()

    override suspend fun readFrom(input: InputStream): BoostStateSnapshot {
        return try {
            if (input.available() == 0) {
                defaultValue
            } else {
                json.decodeFromString(
                    BoostStateSnapshot.serializer(),
                    input.readBytes().decodeToString(),
                )
            }
        } catch (_: SerializationException) {
            defaultValue
        }
    }

    override suspend fun writeTo(t: BoostStateSnapshot, output: OutputStream) {
        output.write(json.encodeToString(BoostStateSnapshot.serializer(), t).encodeToByteArray())
    }
}

/** app 范围内共享的 DataStore 实例。 */
val Context.boostStateDataStore by dataStore(
    fileName = BoostConfig.STORAGE_FILE_NAME,
    serializer = BoostStateSerializer,
)
