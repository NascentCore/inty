package ai.sxwl.android.common.base

import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineExceptionHandler
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import kotlin.coroutines.CoroutineContext

abstract class BaseVM : ViewModel() {
    // 后台任务作用域（独立于UI生命周期）
    private val backgroundScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    // UI相关任务列表
    private val uiJobs: MutableList<Job> = mutableListOf()

    // 后台任务列表
    private val backgroundJobs: MutableList<Job> = mutableListOf()

    // 异常处理器
    private val exceptionHandler =
        CoroutineExceptionHandler { _, throwable ->
            when (throwable) {
                is CancellationException -> {
                    // 正常的取消异常，只记录日志，不显示toast
                    LogUtils.d("协程正常取消: ${throwable.message}")
                }
                else -> {
                    // 其他异常需要记录
                    LogUtils.e("协程异常: ${throwable.message}", throwable)
                }
            }
        }

    /** 启动UI相关协程（随ViewModel生命周期） 适用于：状态更新、事件处理、UI交互 默认上下文：Main线程，适合UI操作 */
    protected fun launchUI(
        context: CoroutineContext = Dispatchers.Main,
        block: suspend CoroutineScope.() -> Unit,
    ): Job {
        return launchCoroutine(
            scope = viewModelScope,
            context = context,
            jobList = uiJobs,
            block = block,
        )
    }

    /** 启动后台协程（独立于UI生命周期） 适用于：数据同步、缓存清理、日志上传等 默认上下文：IO线程，适合后台任务 */
    protected fun launchBackground(
        context: CoroutineContext = Dispatchers.IO,
        block: suspend CoroutineScope.() -> Unit,
    ): Job {
        return launchCoroutine(
            scope = backgroundScope,
            context = context,
            jobList = backgroundJobs,
            block = block,
        )
    }

    /** 启动持久化协程（即使ViewModel销毁也继续执行） 适用于：重要的数据同步、上传任务等 默认上下文：IO线程，适合长时间运行的任务 */
    protected fun launchPersistent(
        context: CoroutineContext = Dispatchers.IO,
        block: suspend CoroutineScope.() -> Unit,
    ): Job {
        return CoroutineScope(SupervisorJob() + Dispatchers.IO + context + exceptionHandler)
            .launch { executeBlock(block, "持久化协程") }
    }

    /** 启动安全的协程（自动处理异常） 适用于：网络请求、数据库操作等 默认上下文：IO线程，适合网络和数据库操作 */
    protected fun launchSafe(
        context: CoroutineContext = Dispatchers.IO,
        onError: (Exception) -> Unit = {},
        block: suspend CoroutineScope.() -> Unit,
    ): Job {
        return launchCoroutine(
            scope = viewModelScope,
            context = context,
            jobList = uiJobs,
            onError = onError,
            block = block,
        )
    }

    /** 启动可取消的协程（优雅处理取消） 适用于：需要响应页面跳转的操作 默认上下文：IO线程 */
    protected fun launchCancellable(
        context: CoroutineContext = Dispatchers.IO,
        onCancelled: () -> Unit = {},
        onError: (Exception) -> Unit = {},
        block: suspend CoroutineScope.() -> Unit,
    ): Job {
        return viewModelScope
            .launch(context + exceptionHandler) {
                try {
                    block.invoke(this)
                } catch (e: CancellationException) {
                    // 协程被取消，只记录日志，不显示toast
                    LogUtils.d("协程被取消: ${e.message}")
                    onCancelled()
                    throw e
                } catch (e: Exception) {
                    LogUtils.e("可取消协程异常: ${e.message}", e)
                    onError(e)
                }
            }
            .apply {
                uiJobs.add(this)
                invokeOnCompletion { uiJobs.remove(this) }
            }
    }

    // region 私有辅助方法

    /** 统一的协程启动方法 */
    private fun launchCoroutine(
        scope: CoroutineScope,
        context: CoroutineContext,
        jobList: MutableList<Job>,
        onError: (Exception) -> Unit = {},
        block: suspend CoroutineScope.() -> Unit,
    ): Job {
        return scope
            .launch(context + exceptionHandler) { executeBlock(block, "协程", onError) }
            .apply {
                jobList.add(this)
                invokeOnCompletion { jobList.remove(this) }
            }
    }

    /** 统一的代码块执行方法 */
    private suspend fun CoroutineScope.executeBlock(
        block: suspend CoroutineScope.() -> Unit,
        contextName: String,
        onError: (Exception) -> Unit = {},
    ) {
        try {
            block.invoke(this)
        } catch (e: CancellationException) {
            // 正常取消，只记录日志，不显示toast
            LogUtils.d("${contextName}被取消: ${e.message}")
            throw e
        } catch (e: Exception) {
            LogUtils.e("${contextName}异常: ${e.message}", e)
            onError(e)
        }
    }

    // endregion

    /** 清理所有UI相关协程 */
    fun clearUIJobs() {
        uiJobs.forEach { job ->
            if (job.isActive) {
                job.cancel()
            }
        }
        uiJobs.clear()
    }

    /** 清理所有后台协程 */
    fun clearBackgroundJobs() {
        backgroundJobs.forEach { job ->
            if (job.isActive) {
                job.cancel()
            }
        }
        backgroundJobs.clear()
    }

    /** 清理所有协程 */
    fun clearAllJobs() {
        clearUIJobs()
        clearBackgroundJobs()
    }

    /** 获取活跃的协程数量 */
    fun getActiveJobsCount(): Int {
        return uiJobs.count { it.isActive } + backgroundJobs.count { it.isActive }
    }

    /** 等待所有UI协程完成 */
    suspend fun awaitAllUIJobs() {
        uiJobs.forEach { job ->
            if (job.isActive) {
                job.join()
            }
        }
    }

    /** 等待所有后台协程完成 */
    suspend fun awaitAllBackgroundJobs() {
        backgroundJobs.forEach { job ->
            if (job.isActive) {
                job.join()
            }
        }
    }

    override fun onCleared() {
        super.onCleared()
        // 只清理UI相关协程，后台协程继续执行
        clearUIJobs()
        LogUtils.d("ViewModel已清理，活跃协程数: ${getActiveJobsCount()}")
    }
}
