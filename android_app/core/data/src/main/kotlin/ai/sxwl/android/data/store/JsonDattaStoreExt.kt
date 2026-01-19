package ai.sxwl.android.data.store

import androidx.datastore.core.Serializer
import androidx.datastore.dataStore
import java.io.InputStream
import java.io.OutputStream
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.serializer

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
