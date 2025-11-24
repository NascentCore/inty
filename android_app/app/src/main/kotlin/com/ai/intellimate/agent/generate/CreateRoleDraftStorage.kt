package com.ai.intellimate.agent.generate

import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

/**
 * CREATED_BY_AGENT
 *
 * 管理创建 IntelliMate 过程中填写的草稿数据，负责序列化到本地和从本地恢复。
 */
object CreateRoleDraftStorage {

    private const val KEY_CREATE_ROLE_DRAFT = "create_role_draft_v1"

    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val adapter = moshi.adapter(CreateRoleDraft::class.java)

    fun saveDraft(draft: CreateRoleDraft) {
        if (draft.isEmpty()) {
            clearDraft()
            return
        }
        runCatching { adapter.toJson(draft) }
            .onSuccess { json ->
                IntySetting.setUserProfileData(KEY_CREATE_ROLE_DRAFT, json)
                LogUtils.d("CreateRoleDraftStorage - draft saved")
            }
            .onFailure { throwable ->
                LogUtils.e("CreateRoleDraftStorage - save failed: ${throwable.message}")
            }
    }

    fun loadDraft(): CreateRoleDraft? {
        val json = IntySetting.getUserProfileData(KEY_CREATE_ROLE_DRAFT) ?: return null
        return runCatching { adapter.fromJson(json) }
            .onFailure { throwable ->
                LogUtils.e("CreateRoleDraftStorage - load failed: ${throwable.message}")
                clearDraft()
            }
            .getOrNull()
    }

    fun clearDraft() {
        IntySetting.clearUserProfileData(KEY_CREATE_ROLE_DRAFT)
    }
}

data class CreateRoleDraft(
    val name: String = "",
    val gender: String = DEFAULT_GENDER,
    val settings: String = "",
    val intro: String = "",
    val opening: String = "",
    val visibility: String = DEFAULT_VISIBILITY,
    val avatarUrl: String? = null,
    val avatarUrls: List<String> = emptyList(),
    val selectedImageIndex: Int = 0,
    val croppedAvatarUrl: String? = null,
    val avatarPrompt: String = "",
) {
    fun isEmpty(): Boolean {
        val hasTextFields =
            name.isNotBlank() || settings.isNotBlank() || intro.isNotBlank() || opening.isNotBlank()
        val hasAvatars =
            !avatarUrl.isNullOrBlank() ||
                avatarUrls.isNotEmpty() ||
                !croppedAvatarUrl.isNullOrBlank()
        val hasMeta = gender != DEFAULT_GENDER || visibility != DEFAULT_VISIBILITY
        val hasAvatarPrompt = avatarPrompt.isNotBlank()
        return !(hasTextFields || hasAvatars || hasMeta || hasAvatarPrompt)
    }

    companion object {
        const val DEFAULT_GENDER = "FEMALE"
        const val DEFAULT_VISIBILITY = "PRIVATE"
    }
}
