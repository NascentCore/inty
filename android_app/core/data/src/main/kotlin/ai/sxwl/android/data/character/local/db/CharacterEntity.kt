/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.local.db

import ai.sxwl.android.data.api.model.CreatorInfo
import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.TypeConverters

@Entity(tableName = "characters")
@TypeConverters(CharacterTypeConverters::class)
data class CharacterEntity(
    @PrimaryKey @ColumnInfo(name = "agent_id") val agentId: String,
    @ColumnInfo(name = "name") val name: String,
    @ColumnInfo(name = "avatar") val avatar: String,
    @ColumnInfo(name = "intro") val intro: String,
    @ColumnInfo(name = "readable_id") val readableId: String,
    @ColumnInfo(name = "category") val category: String,
    @ColumnInfo(name = "energy_points") val energyPoints: Int,
    @ColumnInfo(name = "updated_at") val updatedAt: Long,
    @ColumnInfo(name = "background") val background: String,
    @ColumnInfo(name = "background_animate") val backgroundAnimatedUrl: String,
    @ColumnInfo(name = "gender") val gender: String = "",
    @ColumnInfo(name = "is_followed") val isFollowed: Boolean = false,
    @ColumnInfo(name = "opening") val opening: String = "",
    @ColumnInfo(name = "opening_audio_url") val openingAudioUrl: String = "",
    @ColumnInfo(name = "voice_preview") val voicePreview: String = "",
    @ColumnInfo(name = "created_at") val createdAt: String = "",
    @ColumnInfo(name = "creator") val creator: CreatorInfo? = null,
    @ColumnInfo(name = "tags") val tags: List<String>? = null,
    @ColumnInfo(name = "settings") val settings: Map<String, Any>? = null,
    @ColumnInfo(name = "visibility") val visibility: String = "",
    @ColumnInfo(name = "prompt") val prompt: String = "",
    @ColumnInfo(name = "follower_count") val followerCount: Int = 0,
    @ColumnInfo(name = "connector_count") val connectorCount: Int = 0,
    @ColumnInfo(name = "deleted_at") val deletedAt: Long? = null,
    @ColumnInfo(name = "background_images") val backgroundImages: List<String>? = null,
)
