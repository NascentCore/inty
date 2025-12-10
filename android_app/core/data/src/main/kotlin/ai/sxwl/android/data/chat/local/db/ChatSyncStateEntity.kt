package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "chat_sync_state")
data class ChatSyncStateEntity(
    @PrimaryKey val agentId: String,
    val offset: Int = 0,
    val hasMore: Boolean = true,
    val isInitialLoaded: Boolean = false,
    val lastSyncedAt: Long = 0L,
    val updatedAt: Long = 0L,
)
