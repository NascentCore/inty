package ai.sxwl.android.data.chat.local.db

// CREATED_BY_AGENT

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface ChatSyncStateDao {

    @Query("SELECT * FROM sync_state WHERE agentId = :agentId LIMIT 1")
    fun observe(agentId: String): Flow<SyncStateEntity?>

    @Query("SELECT * FROM sync_state WHERE agentId = :agentId LIMIT 1")
    suspend fun get(agentId: String): SyncStateEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(entity: SyncStateEntity)

    @Query("DELETE FROM sync_state WHERE agentId = :agentId")
    suspend fun delete(agentId: String)

    @Query("DELETE FROM sync_state") suspend fun deleteAll()
}
