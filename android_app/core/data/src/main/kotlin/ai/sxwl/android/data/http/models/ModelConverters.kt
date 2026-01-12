package ai.sxwl.android.data.http.models

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CreatorInfo
import ai.sxwl.android.data.api.model.UserProfile
import com.inty.api.models.api.v1.ai.agents.Agent as IntyAgent
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
        userPhoto = this.userPhoto()
    )
}

/** 将Inty SDK的Agent对象转换为AgentInfo对象 */
fun IntyAgent.toAgentInfo(): AgentInfo {
    val creator =
        this.creator()?.let {
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
            energyPoints = this.energyPoints()?.toInt() ?: 0,
            followerCount = this.followerCount()?.toInt() ?: 0,
            connectorCount = this.connectorCount()?.toInt() ?: 0,
            deletedAt = this.deletedAt(),
        )
        .also { info -> info.isDeleted = this.deletedAt() != null }
}
