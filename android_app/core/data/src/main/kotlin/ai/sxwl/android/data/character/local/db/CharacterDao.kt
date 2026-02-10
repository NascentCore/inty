/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.local.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

@Dao
interface CharacterDao {
    @Query("SELECT * FROM characters WHERE agent_id = :agentId LIMIT 1")
    fun observeCharacter(agentId: String): Flow<CharacterEntity?>

    @Query("SELECT * FROM characters WHERE agent_id = :agentId LIMIT 1")
    suspend fun getCharacter(agentId: String): CharacterEntity?

    @Query("SELECT * FROM characters WHERE agent_id IN (:agentIds)")
    suspend fun getCharacters(agentIds: List<String>): List<CharacterEntity>

    @Insert(onConflict = OnConflictStrategy.REPLACE) suspend fun upsert(character: CharacterEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertAll(characters: List<CharacterEntity>)

    @Query(
        "UPDATE characters SET energy_points = :energyPoints, updated_at = :updatedAt WHERE agent_id = :agentId"
    )
    suspend fun updateEnergy(agentId: String, energyPoints: Int, updatedAt: Long)

    @Query("UPDATE characters SET last_unlock_by_credits = :date WHERE agent_id = :agentId")
    suspend fun unlockAgentByCredits(agentId: String, date: String)

    @Query(
        "SELECT * FROM characters WHERE name LIKE '%' || :query || '%' COLLATE NOCASE ORDER BY name LIMIT :limit"
    )
    suspend fun searchCharactersByName(query: String, limit: Int = 100): List<CharacterEntity>

    @Query(
        "SELECT * FROM characters " +
            "WHERE tags IS NOT NULL AND LOWER(tags) LIKE '%' || LOWER(:query) || '%' " +
            "ORDER BY name LIMIT :limit"
    )
    suspend fun searchCharactersByTag(query: String, limit: Int = 100): List<CharacterEntity>

    @Query("SELECT * FROM festival_memory WHERE agentId = :agentId ORDER BY id DESC")
    fun getFestivalMemories(agentId: String): Flow<List<FestivalMemory>>

    @Query("DELETE FROM festival_memory WHERE agentId = :agentId")
    suspend fun clearMemories(agentId: String)

    @Upsert suspend fun upsert(memories: List<FestivalMemory>)
}
