package com.ai.intellimate.agent.generate

import ai.sxwl.android.common.base.BaseVM
import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.NetServiceMgr
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.utils.LogUtils
import ai.sxwl.android.utils.ToastUtils
import ai.sxwl.android.utils.Utils
import com.ai.intellimate.R
import com.ai.intellimate.utils.HttpErrorHandler
import com.architecture.httplib.core.HttpResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException

/** CreateRoleActivity 的 ViewModel 负责管理 Agent 的创建和更新逻辑 */
class CreateRoleViewModel : BaseVM() {

    private val agentApi: IAgentApi by lazy { NetServiceMgr.getAgentApi() }

    /**
     * 创建 Agent
     *
     * @param request 创建请求
     * @param onSuccess 成功回调
     * @param onError 失败回调
     */
    fun createAgent(
        request: CreateAgentRequest,
        onSuccess: (AgentInfo) -> Unit,
        onError: (String) -> Unit,
    ) {
        launchBackground {
            try {
                val result = agentApi.createAgent(request)

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            LogUtils.i(
                                "CreateRoleViewModel - createAgent success: ${result.data.id}"
                            )
                            onSuccess(result.data)
                        }

                        is HttpResult.Failure -> {
                            LogUtils.e("CreateRoleViewModel - createAgent error: ${result.message}")
                            val errorMessage =
                                result.message.ifBlank {
                                    "Creation failed, please check network connection"
                                }
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: HttpException) {
                LogUtils.e(
                    "CreateRoleViewModel - createAgent HTTP Exception: ${e.code()} - ${e.message()}"
                )
                val errorMessage = HttpErrorHandler.handleHttpException(e, "create")
                withContext(Dispatchers.Main) { onError(errorMessage) }
            } catch (e: Exception) {
                LogUtils.e("CreateRoleViewModel - createAgent exception: ${e.message}")
                val errorMessage = HttpErrorHandler.handleGeneralException(e, "create")
                withContext(Dispatchers.Main) { onError(errorMessage) }
            }
        }
    }

    /**
     * 更新 Agent
     *
     * @param agentId Agent ID
     * @param request 更新请求
     * @param onSuccess 成功回调
     * @param onError 失败回调
     */
    fun updateAgent(
        agentId: String,
        request: CreateAgentRequest,
        onSuccess: (AgentInfo) -> Unit,
        onError: (String) -> Unit,
    ) {
        LogUtils.i("CreateRoleViewModel - updateAgent: $agentId")
        launchBackground {
            try {
                val result = agentApi.updateAgent(agentId, request)

                withContext(Dispatchers.Main) {
                    when (result) {
                        is HttpResult.Success -> {
                            LogUtils.i("CreateRoleViewModel - updateAgent success: ${agentId}")
                            onSuccess(result.data)
                        }

                        is HttpResult.Failure -> {
                            LogUtils.e("CreateRoleViewModel - updateAgent error: ${result.message}")
                            val errorMessage =
                                result.message.ifBlank {
                                    Utils.getApp()
                                        .getString(
                                            R.string.operation_failed_check_network,
                                            Utils.getApp().getString(R.string.update_failed),
                                            Utils.getApp()
                                                .getString(R.string.check_network_connection),
                                        )
                                }
                            ToastUtils.showShort(
                                Utils.getApp()
                                    .getString(R.string.update_failed_with_reason, errorMessage)
                            )
                            onError(errorMessage)
                        }
                    }
                }
            } catch (e: HttpException) {
                LogUtils.e(
                    "CreateRoleViewModel - updateAgent HTTP Exception: ${e.code()} - ${e.message()}"
                )
                val errorMessage = HttpErrorHandler.handleHttpException(e, "update")
                withContext(Dispatchers.Main) {
                    ToastUtils.showShort(errorMessage)
                    onError(errorMessage)
                }
            } catch (e: Exception) {
                LogUtils.e("CreateRoleViewModel - updateAgent exception: ${e.message}")
                val errorMessage = HttpErrorHandler.handleGeneralException(e, "update")
                withContext(Dispatchers.Main) {
                    ToastUtils.showShort(errorMessage)
                    onError(errorMessage)
                }
            }
        }
    }
}
