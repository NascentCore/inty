package com.ai.intellimate.xb.helper

import ai.sxwl.android.data.api.model.UserProfile
import java.util.concurrent.atomic.AtomicReference

object UserProfileStore {
    // 缓存页面跳转时保存的userProfile（编辑资料页面）
    @Volatile private var userProfile = AtomicReference<UserProfile?>(null) // 缓存跨页面用的草稿

    fun setUserProfile(profile: UserProfile?) {
        userProfile.set(profile)
    }

    fun getUserProfile(): UserProfile? {
        return userProfile.getAndSet(null)
    }
}
