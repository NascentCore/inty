package ai.sxwl.android.data.http.services

import ai.sxwl.android.data.api.model.AppVersionRsp
import ai.sxwl.android.data.api.model.VersionReminderAction
import ai.sxwl.android.data.http.ApiResult
import ai.sxwl.android.data.http.IntyNetworkManager
import com.inty.api.models.api.v1.version.VersionCheckParams

/** 版本检查服务 封装版本检查相关的API调用 */
object VersionService {

    /**
     * 检查应用版本更新 替换: ICommonApi.checkAppUpgrade()
     *
     * @param appVersionCode 应用版本代码（必填）
     * @param appVersionName 应用版本名称（可选）
     * @return ApiResult<AppVersionRsp.AppVersionData> 版本检查结果
     */
    suspend fun checkAppUpgrade(
        appVersionCode: Long,
        appVersionName: String? = null,
    ): ApiResult<AppVersionRsp.AppVersionData> {
        return IntyNetworkManager.executeRequest("Check App Version") {
            val params =
                VersionCheckParams.builder()
                    .appVersionCode(appVersionCode)
                    .appVersionName(appVersionName)
                    .build()

            val response = IntyNetworkManager.getClient().api().v1().version().check(params)

            // 将 Inty SDK 的响应转换为 AppVersionRsp.AppVersionData
            val data = response.data()
            if (data == null) {
                throw IllegalStateException("Version check response data is null")
            }

            AppVersionRsp.AppVersionData(
                changelog = data.changelog(),
                current_version = data.currentVersion(),
                download_url = data.downloadUrl(),
                error = data.error(),
                force_update = data.forceUpdate() == true,
                force_update_reasons = data.forceUpdateReasons(),
                latest_version = data.latestVersion(),
                latest_version_code = data.latestVersionCode()?.toInt(),
                message = data.message(),
                minimum_version = data.minimumVersion(),
                update_required = data.updateRequired() == true,
                // TODO: 只需要保留这个字段，其他都可以删除，已经无用了。
                reminder_action = mapReminderAction(data.reminderAction()?.toString()),
            )
        }
    }

    private fun mapReminderAction(rawAction: String?): VersionReminderAction {
        return when (rawAction) {
            VersionReminderAction.BLOCK_ACCESS.name -> VersionReminderAction.BLOCK_ACCESS
            VersionReminderAction.POP_UP_REMINDER.name -> VersionReminderAction.POP_UP_REMINDER
            VersionReminderAction.SETTINGS_REMINDER.name -> VersionReminderAction.SETTINGS_REMINDER
            else -> VersionReminderAction.NONE
        }
    }
}
