package ai.sxwl.android.common.task

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.channels.Channel
import kotlinx.coroutines.channels.consumeEach
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.withContext

/**
 * 定义一个可执行的任务task的抽象类
 */
abstract class AbsMateTask {

    /**
     * 任务执行的时间，为0表示执行完成的时间不固定
     */
    abstract val durationTimeMillis: Long

    abstract val callInMainThread: Boolean

    /**
     * 用于执行task时，挂起当前coroutine
     */
    private var mutex: Mutex? = null

    fun setMutexLock(mutex: Mutex) {
        this.mutex = mutex
    }

    /**
     * 执行任务
     */
    abstract fun doTask()

    /**
     * 恢复当前coroutine，执行下一个task
     */
    fun doNextTask() {
        if (mutex?.isLocked == true) {
            mutex?.unlock()
        }
        mutex = null
    }
}

/**
 * 默认的一个AbsMateTask的实现类
 */
class MateTask(
    override val durationTimeMillis: Long = 0,
    override val callInMainThread: Boolean = true,
    private val block: MateTask.() -> Unit
) : AbsMateTask() {

    /**
     * 执行任务
     */
    override fun doTask() {
        block.invoke(this)
    }
}


/**
 * 任务管理类，用于管理task的执行
 */
class MateTaskQueueManager {

    private var mChannel: Channel<AbsMateTask>? = null
    private var mCoroutineScope: CoroutineScope? = null
    private var mLock = Mutex()

    init {
        initLoop()
    }

    private fun initLoop() {
        mChannel = Channel()
        mCoroutineScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        mCoroutineScope?.launch {
            mChannel?.consumeEach {
                tryHandleTask(it)
            }
        }
    }

    private suspend fun tryHandleTask(task: AbsMateTask) {
        //防止有task抛出异常，用CoroutineExceptionHandler捕获异常之后父coroutine关闭了，之后的send的Task不执行了
        try {
            task.setMutexLock(mLock)
            mLock.lock()
            if (task.callInMainThread) {
                withContext(Dispatchers.Main) {
                    task.doTask()
                }
            } else {
                task.doTask()
            }
            //固定时间的任务，由管理类解除阻塞，调用下个task，不固定时间的耗时任务，需要在任务介绍时手动调用doNextTask()
            if (task.durationTimeMillis != 0L) {
                delay(task.durationTimeMillis)
                task.doNextTask()
            }
        } catch (e: Exception) {
            e.printStackTrace()
            task.doNextTask()
        }
    }

    /**
     * 开始任务
     * @param task ITask
     */
    fun sendTask(task: AbsMateTask) {
        if (mCoroutineScope == null && mChannel == null) {
            initLoop()
        }
        mCoroutineScope?.launch {
            mChannel?.send(task)
        }
    }

    /**
     * 关闭并释放资源
     */
    fun clear() {
        mChannel?.close()
        mChannel = null
        mCoroutineScope?.cancel()
        mCoroutineScope = null
    }

    /**
     * 需要全局单例时使用,局部单例时，直接new
     */
    companion object {
        /**
         * 用于全局单例模式的对象
         */
        val instance: MateTaskQueueManager by lazy {
            MateTaskQueueManager()
        }
    }

}
