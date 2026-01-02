/*
 * CREATED_BY_AGENT
 */
package ai.sxwl.android.data.character.repository

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.character.local.db.CharacterDao
import ai.sxwl.android.data.character.local.db.CharacterDatabase
import ai.sxwl.android.data.character.local.db.CharacterEntity
import ai.sxwl.android.data.character.local.db.getTagsWithVirtual
import ai.sxwl.android.data.character.local.db.isNewCharacter
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

    suspend fun cacheAgents(agents: List<AgentInfo>) {
        if (agents.isEmpty()) return

        val entities =
            agents.map { agentInfo ->
                CharacterEntity(
                    agentId = agentInfo.id,
                    name = agentInfo.name,
                    avatar = agentInfo.avatar,
                    intro = agentInfo.intro,
                    readableId = agentInfo.readableId,
                    category = agentInfo.category,
                    energyPoints = agentInfo.energyPoints,
                    updatedAt = System.currentTimeMillis(),
                    background = agentInfo.background,
                    backgroundAnimatedUrl = agentInfo.backgroundAnimatedUrl,
                    gender = agentInfo.gender,
                    isFollowed = agentInfo.isFollowed,
                    opening = agentInfo.opening,
                    openingAudioUrl = agentInfo.opening_audio_url,
                    voicePreview = agentInfo.voicePreview,
                    createdAt = agentInfo.createdAt,
                    creator = agentInfo.creator,
                    tags = agentInfo.tags?.filterNotNull(),
                    settings = agentInfo.settings,
                    visibility = agentInfo.visibility,
                    prompt = agentInfo.prompt,
                    followerCount = agentInfo.followerCount,
                    connectorCount = agentInfo.connectorCount,
                    deletedAt = agentInfo.deletedAt,
                    backgroundImages = agentInfo.backgroundImages.takeIf { it.isNotEmpty() },
                )
            }

        dao.upsertAll(entities)
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
                    background = agentInfo.background,
                    backgroundAnimatedUrl = agentInfo.backgroundAnimatedUrl,
                    gender = agentInfo.gender,
                    isFollowed = agentInfo.isFollowed,
                    opening = agentInfo.opening,
                    openingAudioUrl = agentInfo.opening_audio_url,
                    voicePreview = agentInfo.voicePreview,
                    createdAt = agentInfo.createdAt,
                    creator = agentInfo.creator,
                    tags = agentInfo.tags?.filterNotNull(),
                    settings = agentInfo.settings,
                    visibility = agentInfo.visibility,
                    prompt = agentInfo.prompt,
                    followerCount = agentInfo.followerCount,
                    connectorCount = agentInfo.connectorCount,
                    deletedAt = agentInfo.deletedAt,
                    backgroundImages = agentInfo.backgroundImages.takeIf { it.isNotEmpty() },
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

    suspend fun searchCharactersByTag(query: String, limit: Int = 100): List<AgentInfo> {
        return withContext(dispatcher) {
            val normalizedQuery = query.trim().lowercase()
            val isNewTagQuery = normalizedQuery == "#new" || normalizedQuery == "new"
            
            val entities = if (isNewTagQuery) {
                // 搜索虚拟 #New tag：查询所有角色，然后过滤出过去1周内创建的
                val allEntities = dao.getAllCharacters(limit * 2)
                allEntities.filter { it.isNewCharacter() }.take(limit)
            } else {
                // 普通 tag 搜索
                dao.searchCharactersByTag(query, limit)
            }
            
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
    // 获取包含虚拟 #New tag 的完整 tags 列表
    val tagsWithVirtual = this.getTagsWithVirtual()
    
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
            tags = tagsWithVirtual.map { it as String? },
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
