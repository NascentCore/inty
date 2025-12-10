package com.ai.intellimate.agent.generate

import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.utils.LogUtils
import com.squareup.moshi.Moshi
import com.squareup.moshi.Types
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.lang.reflect.Type
import java.util.UUID

/**
 * CREATED_BY_AGENT
 *
 * 管理创建 IntelliMate 过程中填写的草稿数据，负责序列化到本地和从本地恢复。 支持多个草稿的保存和管理。
 */
object CreateRoleDraftStorage {

    private const val KEY_CREATE_ROLE_DRAFT = "create_role_draft_v1" // 保留用于向后兼容
    private const val KEY_CREATE_ROLE_DRAFTS_LIST = "create_role_drafts_list_v1"
    private const val KEY_CREATE_ROLE_DRAFT_CURRENT = "create_role_draft_current_v1"

    private val moshi = Moshi.Builder().addLast(KotlinJsonAdapterFactory()).build()
    private val adapter = moshi.adapter(CreateRoleDraft::class.java)
    private val draftsListType: Type =
        Types.newParameterizedType(List::class.java, CreateRoleDraft::class.java)
    private val draftsListAdapter = moshi.adapter<List<CreateRoleDraft>>(draftsListType)

    // ========== 草稿列表相关方法 ==========

    /** 保存草稿到列表（如果已存在则更新，否则添加） */
    fun saveDraftToList(draft: CreateRoleDraft) {
        if (draft.isEmpty()) {
            deleteDraft(draft.id)
            return
        }
        val updatedDraft = draft.withUpdatedTimestamp()
        runCatching {
                val allDrafts = getAllDrafts().toMutableList()
                val existingIndex = allDrafts.indexOfFirst { it.id == updatedDraft.id }
                if (existingIndex >= 0) {
                    allDrafts[existingIndex] = updatedDraft
                } else {
                    allDrafts.add(updatedDraft)
                }
                val json = draftsListAdapter.toJson(allDrafts)
                IntySetting.setUserProfileData(KEY_CREATE_ROLE_DRAFTS_LIST, json)
                LogUtils.d("CreateRoleDraftStorage - draft saved to list: ${updatedDraft.id}")
            }
            .onFailure { throwable ->
                LogUtils.e(
                    "CreateRoleDraftStorage - save draft to list failed: ${throwable.message}"
                )
            }
    }

    /** 获取所有草稿列表 */
    fun getAllDrafts(): List<CreateRoleDraft> {
        val json = IntySetting.getUserProfileData(KEY_CREATE_ROLE_DRAFTS_LIST) ?: return emptyList()
        return runCatching { draftsListAdapter.fromJson(json) }
            .onFailure { throwable ->
                LogUtils.e("CreateRoleDraftStorage - load drafts list failed: ${throwable.message}")
                clearAllDrafts()
            }
            .getOrNull() ?: emptyList()
    }

    /** 根据ID获取特定草稿，ID 为 UUID 字符串 */
    fun getDraftById(id: String): CreateRoleDraft? {
        return getAllDrafts().firstOrNull { it.id == id }
    }

    /** 删除特定草稿，ID 为 UUID 字符串 */
    fun deleteDraft(id: String) {
        runCatching {
                val allDrafts = getAllDrafts().toMutableList()
                allDrafts.removeAll { it.id == id }
                val json = draftsListAdapter.toJson(allDrafts)
                IntySetting.setUserProfileData(KEY_CREATE_ROLE_DRAFTS_LIST, json)
                LogUtils.d("CreateRoleDraftStorage - draft deleted: $id")
            }
            .onFailure { throwable ->
                LogUtils.e("CreateRoleDraftStorage - delete draft failed: ${throwable.message}")
            }
    }

    /** 清除所有草稿。 */
    fun clearAllDrafts() {
        IntySetting.clearUserProfileData(KEY_CREATE_ROLE_DRAFTS_LIST)
    }

    // ========== 临时草稿相关方法（用于自动保存当前编辑状态） ==========

    /** 保存当前编辑的临时草稿（用于自动保存） */
    fun saveCurrentDraft(draft: CreateRoleDraft) {
        if (draft.isEmpty()) {
            clearCurrentDraft()
            return
        }
        runCatching { adapter.toJson(draft) }
            .onSuccess { json ->
                IntySetting.setUserProfileData(KEY_CREATE_ROLE_DRAFT_CURRENT, json)
                LogUtils.d("CreateRoleDraftStorage - current draft saved")
            }
            .onFailure { throwable ->
                LogUtils.e(
                    "CreateRoleDraftStorage - save current draft failed: ${throwable.message}"
                )
            }
    }

    /** 加载当前编辑的临时草稿 */
    fun loadCurrentDraft(): CreateRoleDraft? {
        val json = IntySetting.getUserProfileData(KEY_CREATE_ROLE_DRAFT_CURRENT) ?: return null
        return runCatching { adapter.fromJson(json) }
            .onFailure { throwable ->
                LogUtils.e(
                    "CreateRoleDraftStorage - load current draft failed: ${throwable.message}"
                )
                clearCurrentDraft()
            }
            .getOrNull()
    }

    /** 清除当前编辑的临时草稿 */
    fun clearCurrentDraft() {
        IntySetting.clearUserProfileData(KEY_CREATE_ROLE_DRAFT_CURRENT)
    }

    // ========== 向后兼容的旧方法（保留但标记为废弃） ==========

    /** @deprecated 使用 saveDraftToList 或 saveCurrentDraft 替代 */
    @Deprecated("Use saveDraftToList or saveCurrentDraft instead")
    fun saveDraft(draft: CreateRoleDraft) {
        saveCurrentDraft(draft)
    }

    /** @deprecated 使用 loadCurrentDraft 替代 */
    @Deprecated("Use loadCurrentDraft instead")
    fun loadDraft(): CreateRoleDraft? {
        return loadCurrentDraft()
    }

    /** @deprecated 使用 clearCurrentDraft 替代 */
    @Deprecated("Use clearCurrentDraft instead")
    fun clearDraft() {
        clearCurrentDraft()
    }
}

data class CreateRoleDraft(
    val id: String = UUID.randomUUID().toString(),
    val createdAt: Long = System.currentTimeMillis(),
    val lastModifiedAt: Long = System.currentTimeMillis(),
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

    /** 更新 lastModifiedAt 时间戳 */
    fun withUpdatedTimestamp(): CreateRoleDraft {
        return copy(lastModifiedAt = System.currentTimeMillis())
    }

    companion object {
        const val DEFAULT_GENDER = "FEMALE"
        const val DEFAULT_VISIBILITY = "PRIVATE"
    }
}
