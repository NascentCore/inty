/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.repository

import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.character.local.db.CharacterDao
import ai.sxwl.android.data.character.local.db.CharacterDatabase
import ai.sxwl.android.data.character.local.db.CharacterEntity
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResult
import java.time.LocalDate
import kotlin.math.max
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.filterNotNull
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

    suspend fun unlockAgentByCredits(agentId: String) {
        withContext(Dispatchers.IO) {
            dao.unlockAgentByCredits(agentId, LocalDate.now().toString())
        }
    }

    fun getCharacterFlow(agentId: String): Flow<CharacterEntity?> {
        return dao.observeCharacter(agentId).filterNotNull()
    }

    suspend fun updateLocalAgent(agentId: String, update: (AgentInfo) -> AgentInfo) {
        withContext(dispatcher) {
            val entity = dao.getCharacter(agentId)
            val agent = entity?.toAgentInfo() ?: AgentInfo(id = agentId)

            dao.upsert(update(agent).toCharacterEntity(entity))
        }
    }

    suspend fun refreshAgent(agentId: String): HttpResult<AgentInfo> {
        return runCatching { NetServiceMgr.getChatApi().getAgentInfo(agentId) }
            .onSuccess {
                val existing = dao.getCharacter(agentId)
                if (it is HttpResult.Success) {
                    dao.upsert(it.data.toCharacterEntity(existing))
                }
            }
            .onFailure { error -> LogUtils.e("setAgentID exception: ${error.message}") }
            .getOrThrow()
    }

    suspend fun cacheAgents(agents: List<AgentInfo>) {
        if (agents.isEmpty()) return

        val entities =
            agents.map { agentInfo ->
                val existing = dao.getCharacter(agentInfo.id)

                agentInfo.toCharacterEntity(existing?.copy(energyPoints = agentInfo.energyPoints))
            }

        dao.upsertAll(entities)
    }

    @Deprecated("不完整的AgentInfo会删除数据库中已有记录")
    suspend fun syncCharacterSnapshot(agentInfo: AgentInfo, energyPoints: Int) {
        withContext(dispatcher) {
            val existing = dao.getCharacter(agentInfo.id)
            val sanitizedPoints = max(existing?.energyPoints ?: 0, energyPoints)
            val entity = agentInfo.toCharacterEntity(existing?.copy(energyPoints = sanitizedPoints))

            dao.upsert(entity)
        }
    }

    suspend fun updateEnergy(agentId: String, energyPoints: Int) {
        withContext(dispatcher) {
            val existing = dao.getCharacter(agentId)
            val sanitizedPoints = max(existing?.energyPoints ?: 0, energyPoints)
            dao.updateEnergy(agentId, sanitizedPoints, System.currentTimeMillis())
        }
    }

    suspend fun searchCharactersByName(query: String, limit: Int = 100): List<AgentInfo> {
        return withContext(dispatcher) {
            val entities = dao.searchCharactersByName(query, limit)
            entities.map { it.toAgentInfo() }
        }
    }

    suspend fun searchCharactersByTag(query: String, limit: Int = 100): List<AgentInfo> {
        return withContext(dispatcher) {
            val entities = dao.searchCharactersByTag(query, limit)
            entities.map { it.toAgentInfo() }
        }
    }

    suspend fun getAgentsByIds(agentIds: List<String>): List<AgentInfo> {
        if (agentIds.isEmpty()) return emptyList()
        return withContext(dispatcher) {
            val entities = dao.getCharacters(agentIds)
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
            background = this.background,
            backgroundAnimatedUrl = this.backgroundAnimatedUrl,
            backgroundImages = this.backgroundImages ?: emptyList(),
            gender = this.gender,
            isFollowed = this.isFollowed,
            opening = this.opening,
            opening_audio_url = this.openingAudioUrl,
            voicePreview = this.voicePreview,
            createdAt = this.createdAt,
            creator = this.creator,
            tags = this.tags?.map { it as String? },
            settings = this.settings,
            visibility = this.visibility,
            prompt = this.prompt,
            energyPoints = this.energyPoints,
            followerCount = this.followerCount,
            connectorCount = this.connectorCount,
            deletedAt = this.deletedAt,
        )
        .also { info -> info.isDeleted = this.deletedAt != null }
}

private fun AgentInfo.toCharacterEntity(existing: CharacterEntity?): CharacterEntity {

    return existing?.copy(
        agentId = id,
        name = name,
        avatar = avatar,
        intro = intro,
        readableId = readableId,
        category = category,
        updatedAt = System.currentTimeMillis(),
        background = background,
        backgroundAnimatedUrl = backgroundAnimatedUrl,
        gender = gender,
        isFollowed = isFollowed,
        opening = opening,
        openingAudioUrl = opening_audio_url,
        voicePreview = voicePreview,
        createdAt = createdAt,
        creator = creator,
        tags = tags?.filterNotNull(),
        settings = settings,
        visibility = visibility,
        prompt = prompt,
        followerCount = followerCount,
        connectorCount = connectorCount,
        deletedAt = deletedAt,
        backgroundImages = backgroundImages.takeIf { it.isNotEmpty() },
    )
        ?: CharacterEntity(
            agentId = id,
            name = name,
            avatar = avatar,
            intro = intro,
            readableId = readableId,
            energyPoints = energyPoints,
            category = category,
            updatedAt = System.currentTimeMillis(),
            background = background,
            backgroundAnimatedUrl = backgroundAnimatedUrl,
            gender = gender,
            isFollowed = isFollowed,
            opening = opening,
            openingAudioUrl = opening_audio_url,
            voicePreview = voicePreview,
            createdAt = createdAt,
            creator = creator,
            tags = tags?.filterNotNull(),
            settings = settings,
            visibility = visibility,
            prompt = prompt,
            followerCount = followerCount,
            connectorCount = connectorCount,
            deletedAt = deletedAt,
            backgroundImages = backgroundImages.takeIf { it.isNotEmpty() },
        )
}
