/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.repository

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.character.local.db.CharacterDao
import ai.sxwl.android.data.character.local.db.CharacterDatabase
import ai.sxwl.android.data.character.local.db.CharacterEntity
import kotlin.math.max
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext

class CharacterRepository(
    private val dao: CharacterDao = CharacterDatabase.getInstance().characterDao(),
    private val dispatcher: CoroutineDispatcher = Dispatchers.IO,
) {

    fun observeCharacter(agentId: String): Flow<CharacterEntity?> {
        return dao.observeCharacter(agentId)
    }

    suspend fun getCharacter(agentId: String): CharacterEntity? {
        return withContext(dispatcher) { dao.getCharacter(agentId) }
    }

    suspend fun syncCharacterSnapshot(agentInfo: AgentInfo, energyPoints: Int) {
        withContext(dispatcher) {
            val existing = dao.getCharacter(agentInfo.id)
            val sanitizedPoints = max(existing?.energyPoints ?: 0, energyPoints)
            val entity =
                CharacterEntity(
                    agentId = agentInfo.id,
                    name = agentInfo.name,
                    avatar = agentInfo.avatar,
                    intro = agentInfo.intro,
                    readableId = agentInfo.readableId,
                    category = agentInfo.category,
                    energyPoints = sanitizedPoints,
                    updatedAt = System.currentTimeMillis(),
                )
            dao.upsert(entity)
        }
    }

    suspend fun updateEnergy(agentId: String, energyPoints: Int) {
        val sanitizedPoints = max(0, energyPoints)
        withContext(dispatcher) {
            dao.updateEnergy(agentId, sanitizedPoints, System.currentTimeMillis())
        }
    }

    suspend fun searchCharactersByName(query: String, limit: Int = 100): List<AgentInfo> {
        return withContext(dispatcher) {
            val entities = dao.searchCharactersByName(query, limit)
            entities.map { it.toAgentInfo() }
        }
    }
}

/** 将 CharacterEntity 转换为 AgentInfo */
private fun CharacterEntity.toAgentInfo(): AgentInfo {
    return AgentInfo(
        id = this.agentId,
        name = this.name,
        avatar = this.avatar,
        intro = this.intro,
        readableId = this.readableId,
        category = this.category,
        // 其他字段使用默认值，因为数据库中没有存储
        background = "",
        backgroundAnimatedUrl = "",
        backgroundImages = emptyList(),
        gender = "",
        isFollowed = false,
        opening = "",
        opening_audio_url = "",
        voicePreview = "",
        createdAt = "",
        creator = null,
        tags = null,
        settings = null,
        visibility = "",
        prompt = "",
        followerCount = 0,
        connectorCount = 0,
        deletedAt = null,
    )
}
