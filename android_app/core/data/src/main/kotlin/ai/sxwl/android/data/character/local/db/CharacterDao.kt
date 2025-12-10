/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.local.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import kotlinx.coroutines.flow.Flow

@Dao
interface CharacterDao {
    @Query("SELECT * FROM characters WHERE agent_id = :agentId LIMIT 1")
    fun observeCharacter(agentId: String): Flow<CharacterEntity?>

    @Query("SELECT * FROM characters WHERE agent_id = :agentId LIMIT 1")
    suspend fun getCharacter(agentId: String): CharacterEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(character: CharacterEntity)

    @Query(
        "UPDATE characters SET energy_points = :energyPoints, updated_at = :updatedAt WHERE agent_id = :agentId"
    )
    suspend fun updateEnergy(agentId: String, energyPoints: Int, updatedAt: Long)
}
