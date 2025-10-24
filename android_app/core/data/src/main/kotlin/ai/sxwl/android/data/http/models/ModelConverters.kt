package ai.sxwl.android.data.http.models

import ai.sxwl.android.data.api.model.UserProfile
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
