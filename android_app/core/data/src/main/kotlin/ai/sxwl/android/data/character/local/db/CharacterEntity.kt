/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.local.db

import androidx.room.ColumnInfo
import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "characters")
data class CharacterEntity(
    @PrimaryKey @ColumnInfo(name = "agent_id") val agentId: String,
    @ColumnInfo(name = "name") val name: String,
    @ColumnInfo(name = "avatar") val avatar: String,
    @ColumnInfo(name = "intro") val intro: String,
    @ColumnInfo(name = "readable_id") val readableId: String,
    @ColumnInfo(name = "category") val category: String,
    @ColumnInfo(name = "energy_points") val energyPoints: Int,
    @ColumnInfo(name = "updated_at") val updatedAt: Long,
)
