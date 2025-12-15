/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.local.db

import ai.sxwl.android.data.api.model.CreatorInfo
import androidx.room.TypeConverter
import com.architecture.httplib.utils.MoshiUtils
import com.squareup.moshi.Types

/**
 * Room TypeConverter 用于序列化/反序列化复杂类型
 */
class CharacterTypeConverters {

    // List<String> 转换器
    @TypeConverter
    fun fromStringList(value: String?): List<String>? {
        if (value.isNullOrBlank()) return null
        return try {
            val type = Types.newParameterizedType(List::class.java, String::class.java)
            MoshiUtils.moshiBuild.adapter<List<String>>(type).fromJson(value)
        } catch (e: Exception) {
            null
        }
    }

    @TypeConverter
    fun toStringList(value: List<String>?): String? {
        if (value.isNullOrEmpty()) return null
        return try {
            val type = Types.newParameterizedType(List::class.java, String::class.java)
            MoshiUtils.moshiBuild.adapter<List<String>>(type).toJson(value) ?: null
        } catch (e: Exception) {
            null
        }
    }

    // Map<String, Any> 转换器
    @TypeConverter
    fun fromStringMap(value: String?): Map<String, Any>? {
        if (value.isNullOrBlank()) return null
        return try {
            val type = Types.newParameterizedType(Map::class.java, String::class.java, Any::class.java)
            MoshiUtils.moshiBuild.adapter<Map<String, Any>>(type).fromJson(value)
        } catch (e: Exception) {
            null
        }
    }

    @TypeConverter
    fun toStringMap(value: Map<String, Any>?): String? {
        if (value.isNullOrEmpty()) return null
        return try {
            val type = Types.newParameterizedType(Map::class.java, String::class.java, Any::class.java)
            MoshiUtils.moshiBuild.adapter<Map<String, Any>>(type).toJson(value) ?: null
        } catch (e: Exception) {
            null
        }
    }

    // CreatorInfo 转换器
    @TypeConverter
    fun fromCreatorInfo(value: String?): CreatorInfo? {
        if (value.isNullOrBlank()) return null
        return try {
            MoshiUtils.fromJson<CreatorInfo>(value)
        } catch (e: Exception) {
            null
        }
    }

    @TypeConverter
    fun toCreatorInfo(value: CreatorInfo?): String? {
        if (value == null) return null
        return try {
            MoshiUtils.toJson(value)
        } catch (e: Exception) {
            null
        }
    }
}

