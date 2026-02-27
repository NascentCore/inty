package ai.sxwl.android.data.character.local.db

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "festival_memory")
data class FestivalMemory(
    @PrimaryKey val id: Long,
    val agentId: String,
    // 日期
    val festivalDate: String = "",
    // 节日名称
    val festivalName: String? = null,
    val memory: String = "",
) {
    val title: String
        get() = festivalName ?: festivalDate
}
