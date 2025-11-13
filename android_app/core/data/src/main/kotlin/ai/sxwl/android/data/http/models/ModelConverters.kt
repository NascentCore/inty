package ai.sxwl.android.data.http.models

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.ConversationItem
import ai.sxwl.android.data.api.model.CreatorInfo
import ai.sxwl.android.data.api.model.MsgInfo
import ai.sxwl.android.data.api.model.UserProfile
import com.inty.api.models.v2.chat.ChatSendMessageResponse
import com.inty.api.models.api.v1.ai.agents.Agent as IntyAgent
import com.inty.api.models.api.v1.chats.Chat as IntyChat
import com.inty.api.models.api.v1.users.profile.User as IntyUser

/** 数据模型转换工具 将Inty SDK的模型转换为业务层模型 */

/** 将Inty SDK的User对象转换为UserProfile对象 */
fun IntyUser.toUserProfile(): UserProfile {
    return UserProfile(
        id = this.id(),
        nickname = this.nickname() ?: "",
        avatar = this.avatar(),
        description = this.description(),
        email = this.email(),
        gender = this.gender()?.toString(),
        authType = this.authType(),
        createdAt = this.createdAt().toString(),
        updatedAt = this.updatedAt()?.toString(),
        systemLanguage = this.systemLanguage() ?: "",
        isActive = this.isActive(),
        isSuperuser = this.isSuperuser() ?: false,
        phone = this.phone(),
        ageGroup = this.ageGroup(),
        readableId = this.readableId(),
        publicAgentsCount = this.publicAgentsCount()?.toInt() ?: 0,
        totalAgentsFollows = this.totalPublicAgentsFollows()?.toInt() ?: 0,
        followerCount = this.followersCount()?.toInt() ?: 0,
        connectorCount = this.connectorCount()?.toInt() ?: 0,
    )
}

/** 将Inty SDK的Agent对象转换为AgentInfo对象 */
fun IntyAgent.toAgentInfo(): AgentInfo {
    val creator = this.creator()?.let {
        CreatorInfo(
            ageGroup = it.ageGroup(),
            authType = it.authType(),
            avatar = it.avatar(),
            createdAt = it.createdAt().toString(),
            description = it.description(),
            email = it.email(),
            gender = it.gender()?.toString(),
            id = it.id(),
            isActive = it.isActive(),
            isSuperuser = it.isSuperuser() ?: false,
            nickname = it.nickname() ?: "",
            phone = it.phone(),
            systemLanguage = it.systemLanguage() ?: "",
            updatedAt = it.updatedAt()?.toString(),
            publicAgentsCount = it.publicAgentsCount()?.toInt() ?: 0,
            totalPublicAgentsFollows = it.totalPublicAgentsFollows()?.toInt() ?: 0,
        )
    }

    return AgentInfo(
        avatar = this.avatar() ?: "",
        background = this.background() ?: "",
        backgroundAnimatedUrl = "", // SDK中没有此字段，需要从extensions中获取
        backgroundImages = this.backgroundImages() ?: emptyList(),
        category = this.category() ?: "",
        gender = this.gender(),
        id = this.id(),
        readableId = this.readableId(),
        isFollowed = this.isFollowed() ?: false,
        name = this.name(),
        opening = this.opening() ?: "",
        opening_audio_url = this.openingAudioUrl() ?: "",
        voicePreview = "", // SDK中没有此字段
        createdAt = this.createdAt().toString(),
        creator = creator,
        intro = this.intro() ?: "",
        tags = this.tags()?.map { it },
        settings = null, // SDK中settings是Settings对象，需要转换为Map
        visibility = this.visibility()?.toString() ?: "",
        prompt = this.prompt() ?: "",
        followerCount = this.followerCount()?.toInt() ?: 0,
        connectorCount = this.connectorCount()?.toInt() ?: 0,
        deletedAt = this.deletedAt(),
    ).also { info ->
        info.isDeleted = this.deletedAt() != null
    }
}

/** 将Inty SDK的Chat对象转换为ConversationItem对象 */
fun IntyChat.toConversationItem(): ConversationItem {
    return ConversationItem(
        agentId = this.agentId(),
        agentName = this.agentName() ?: "",
        agentAvatar = this.agentAvatar() ?: "",
        agentBackground = this.agentBackground() ?: "",
        agentBackgroundAnimated = "", // SDK中没有此字段
        agentIntro = this.agentIntro() ?: "",
        agentOpening = this.agentOpening() ?: "",
        agentOpeningAudioUrl = this.agentOpeningAudioUrl() ?: "",
        createdAt = this.createdAt().toString(),
        id = this.id(),
        lastMessage = this.lastMessage() ?: "",
        lastMessageTime = this.lastMessageTime()?.toString() ?: "",
        settings = null, // SDK中settings是ChatSettings对象
        updatedAt = this.updatedAt()?.toString(),
        userId = this.userId(),
        isDeleted = this.agentIsDeleted() ?: false,
    )
}

/** 将Inty SDK的ChatSendMessageResponse中的Message转换为MsgInfo对象 */
fun ChatSendMessageResponse.Data.Choice.Message.toMsgInfo(agentId: String? = null): MsgInfo {
    val metaData = MsgInfo.MsgMetaData(
        agentId = agentId,
        isOpening = false,
        generatedImage = null, // 需要从其他地方获取
    )

    return MsgInfo(
        id = this.id()?.toString() ?: "",
        content = this.content(), // content() 是必需的，不是可空的
        role = this.role(), // role() 是必需的，不是可空的
        meta_data = metaData,
        audio_url = this.audioUrl(),
        timestamp = this.timestamp(),
    )
}

/** 将字典格式的消息转换为MsgInfo对象 */
fun Map<String, Any>.toMsgInfo(agentId: String? = null): MsgInfo {
    val id = (this["id"] as? Number)?.toString() ?: (this["id"] as? String) ?: ""
    val content = (this["content"] as? String) ?: ""
    val role = (this["type"] as? String) ?: (this["role"] as? String) ?: ""
    val timestamp = (this["timestamp"] as? String) ?: null
    val audioUrl = (this["audio_url"] as? String) ?: null

    val metaData = MsgInfo.MsgMetaData(
        agentId = agentId,
        isOpening = (this["is_opening"] as? Boolean) ?: false,
        generatedImage = null,
    )

    return MsgInfo(
        id = id,
        content = content,
        role = role,
        meta_data = metaData,
        audio_url = audioUrl,
        timestamp = timestamp,
    )
}
