package ai.sxwl.android.common.event

import ai.sxwl.android.utils.LogUtils
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LifecycleOwner
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import java.lang.ref.WeakReference
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicLong
import kotlin.reflect.KClass

/** 事件总线核心接口 定义了事件总线的基本操作 */
interface IEventBus {
    /** 订阅事件 */
    fun <T : Any> subscribe(
        eventClass: KClass<T>,
        subscriber: EventSubscriber<T>,
        priority: Int = 0,
    )

    /** 取消订阅 */
    fun <T : Any> unsubscribe(
        eventClass: KClass<T>,
        subscriber: EventSubscriber<T>,
    )

    /** 发布事件 */
    fun <T : Any> post(event: T)

    /** 发布事件到主线程 */
    fun <T : Any> postOnMainThread(event: T)

    /** 发布事件到后台线程 */
    fun <T : Any> postOnBackgroundThread(event: T)

    /** 清理无效订阅者 */
    fun cleanup()

    /** 获取订阅者数量 */
    fun <T : Any> getSubscriberCount(eventClass: KClass<T>): Int

    /** 检查是否有订阅者 */
    fun <T : Any> hasSubscribers(eventClass: KClass<T>): Boolean
}

/** 事件订阅者接口 */
interface EventSubscriber<T : Any> {
    fun onEvent(event: T)
}

/** 事件包装器 */
data class EventWrapper(
    val id: Long,
    val event: Any,
    val eventClass: KClass<*>,
    val timestamp: Long = System.currentTimeMillis(),
)

/** 事件总线配置 */
data class EventBusConfig(
    val enableLogging: Boolean = false,
    val enablePerformanceMonitoring: Boolean = false,
    val maxSubscribersPerEvent: Int = 1000,
    val cleanupIntervalMs: Long = 30000, // 30秒
)

/** 事件总线统计信息 */
data class EventBusStats(
    val totalEventsPublished: Long = 0,
    val totalSubscribers: Int = 0,
    val activeEventTypes: Int = 0,
    val lastCleanupTime: Long = 0,
)

/** 事件总线管理器 负责管理事件订阅者和发布事件 */
internal class EventBusManager(
    private val config: EventBusConfig = EventBusConfig(),
) {
    private val subscribers = ConcurrentHashMap<KClass<*>, MutableSet<WeakEventSubscriber<*>>>()
    private val eventIdGenerator = AtomicLong(0)
    private val eventScope = CoroutineScope(SupervisorJob() + Dispatchers.Main.immediate)
    private val _eventFlow = MutableSharedFlow<EventWrapper>(replay = 0)
    val eventFlow: SharedFlow<EventWrapper> = _eventFlow.asSharedFlow()

    private var stats = EventBusStats()

    fun <T : Any> subscribe(
        eventClass: KClass<T>,
        subscriber: EventSubscriber<T>,
        priority: Int = 0,
    ) {
        val subscriberSet = subscribers.getOrPut(eventClass) { mutableSetOf() }

        if (subscriberSet.size >= config.maxSubscribersPerEvent) {
            logWarning("达到最大订阅者数量限制: ${config.maxSubscribersPerEvent}")
            return
        }

        val weakSubscriber = WeakEventSubscriber(WeakReference(subscriber), priority)
        subscriberSet.add(weakSubscriber)

        updateStats()
        logDebug("订阅事件: ${eventClass.simpleName}, 优先级: $priority")
    }

    fun <T : Any> unsubscribe(
        eventClass: KClass<T>,
        subscriber: EventSubscriber<T>,
    ) {
        subscribers[eventClass]?.removeIf { it.getSubscriber == subscriber }
        updateStats()
        logDebug("取消订阅事件: ${eventClass.simpleName}")
    }

    fun <T : Any> post(event: T) {
        val eventClass = event::class
        val eventId = eventIdGenerator.incrementAndGet()
        val eventWrapper = EventWrapper(eventId, event, eventClass)

        eventScope.launch {
            try {
                _eventFlow.emit(eventWrapper)
                notifySubscribers(eventWrapper)
                stats = stats.copy(totalEventsPublished = stats.totalEventsPublished + 1)
                logDebug("发布事件: ${eventClass.simpleName}")
            } catch (e: Exception) {
                logError("发布事件失败: ${e.message}")
            }
        }
    }

    fun <T : Any> postOnMainThread(event: T) {
        eventScope.launch(Dispatchers.Main) { post(event) }
    }

    fun <T : Any> postOnBackgroundThread(event: T) {
        eventScope.launch(Dispatchers.IO) { post(event) }
    }

    fun cleanup() {
        var removedCount = 0
        subscribers.forEach { (eventClass, subscriberSet) ->
            val beforeSize = subscriberSet.size
            subscriberSet.removeIf { it.getSubscriber == null }
            removedCount += beforeSize - subscriberSet.size

            if (subscriberSet.isEmpty()) {
                subscribers.remove(eventClass)
            }
        }

        stats =
            stats.copy(
                lastCleanupTime = System.currentTimeMillis(),
                totalSubscribers = subscribers.values.sumOf { it.size },
            )

        logDebug("清理完成，移除 $removedCount 个无效订阅者")
    }

    fun <T : Any> getSubscriberCount(eventClass: KClass<T>): Int {
        return subscribers[eventClass]?.size ?: 0
    }

    fun <T : Any> hasSubscribers(eventClass: KClass<T>): Boolean {
        return subscribers[eventClass]?.isNotEmpty() == true
    }

    fun getStats(): EventBusStats {
        return stats.copy(
            totalSubscribers = subscribers.values.sumOf { it.size },
            activeEventTypes = subscribers.size,
        )
    }

    private suspend fun notifySubscribers(eventWrapper: EventWrapper) {
        val eventClass = eventWrapper.eventClass
        val subscriberSet = subscribers[eventClass] ?: return

        val sortedSubscribers =
            subscriberSet.filter { it.getSubscriber != null }.sortedByDescending { it.priority }

        sortedSubscribers.forEach { weakSubscriber ->
            weakSubscriber.getSubscriber?.let { subscriber ->
                try {
                    @Suppress("UNCHECKED_CAST")
                    (subscriber as EventSubscriber<Any>).onEvent(eventWrapper.event)
                } catch (e: Exception) {
                    logError("订阅者处理事件失败: ${e.message}")
                }
            }
        }
    }

    private fun updateStats() {
        stats =
            stats.copy(
                totalSubscribers = subscribers.values.sumOf { it.size },
                activeEventTypes = subscribers.size,
            )
    }

    private fun logDebug(message: String) {
        if (config.enableLogging) {
            LogUtils.d("[EventBus] $message")
        }
    }

    private fun logWarning(message: String) {
        if (config.enableLogging) {
            LogUtils.w("[EventBus] WARNING: $message")
        }
    }

    private fun logError(message: String) {
        if (config.enableLogging) {
            LogUtils.e("[EventBus] ERROR: $message")
        }
    }
}

/** 弱引用事件订阅者 防止内存泄漏 */
private class WeakEventSubscriber<T : Any>(
    subscriberRef: WeakReference<EventSubscriber<T>>,
    val priority: Int,
) {
    private val weakRef: WeakReference<EventSubscriber<T>> = subscriberRef
    private val subscriberId: Int = weakRef.get()?.let { System.identityHashCode(it) } ?: 0

    val getSubscriber: EventSubscriber<T>?
        get() = weakRef.get()

    override fun equals(other: Any?): Boolean {
        if (this === other) return true
        if (other !is WeakEventSubscriber<*>) return false
        return subscriberId == other.subscriberId
    }

    override fun hashCode(): Int = subscriberId
}

/** 事件总线单例实现 提供全局事件总线功能 */
object EventBus : IEventBus {
    private val manager = EventBusManager()

    override fun <T : Any> subscribe(
        eventClass: KClass<T>,
        subscriber: EventSubscriber<T>,
        priority: Int,
    ) {
        manager.subscribe(eventClass, subscriber, priority)
    }

    override fun <T : Any> unsubscribe(
        eventClass: KClass<T>,
        subscriber: EventSubscriber<T>,
    ) {
        manager.unsubscribe(eventClass, subscriber)
    }

    override fun <T : Any> post(event: T) {
        manager.post(event)
    }

    override fun <T : Any> postOnMainThread(event: T) {
        manager.postOnMainThread(event)
    }

    override fun <T : Any> postOnBackgroundThread(event: T) {
        manager.postOnBackgroundThread(event)
    }

    override fun cleanup() {
        manager.cleanup()
    }

    override fun <T : Any> getSubscriberCount(eventClass: KClass<T>): Int {
        return manager.getSubscriberCount(eventClass)
    }

    override fun <T : Any> hasSubscribers(eventClass: KClass<T>): Boolean {
        return manager.hasSubscribers(eventClass)
    }

    /** 获取事件流 */
    val eventFlow: SharedFlow<EventWrapper> = manager.eventFlow

    /** 获取统计信息 */
    fun getStats(): EventBusStats = manager.getStats()
}

/** EventBus扩展函数，提供更便捷的API */
object EventBusExtensions {
    /** 使用lambda表达式订阅事件 */
    inline fun <reified T : Any> IEventBus.subscribe(
        priority: Int = 0,
        crossinline onEvent: (T) -> Unit,
    ) {
        subscribe(
            T::class,
            object : EventSubscriber<T> {
                override fun onEvent(event: T) {
                    onEvent(event)
                }
            },
            priority,
        )
    }

    /** 使用lambda表达式订阅事件（带生命周期管理） */
    inline fun <reified T : Any> IEventBus.subscribeWithLifecycle(
        lifecycleOwner: LifecycleOwner,
        priority: Int = 0,
        crossinline onEvent: (T) -> Unit,
    ) {
        val subscriber =
            object : EventSubscriber<T> {
                override fun onEvent(event: T) {
                    onEvent(event)
                }
            }

        subscribe(T::class, subscriber, priority)

        lifecycleOwner.lifecycle.addObserver(
            object : LifecycleEventObserver {
                override fun onStateChanged(
                    source: LifecycleOwner,
                    event: Lifecycle.Event,
                ) {
                    if (event == Lifecycle.Event.ON_DESTROY) {
                        unsubscribe(T::class, subscriber)
                    }
                }
            },
        )
    }

    /** 批量订阅事件 */
    inline fun IEventBus.subscribeBatch(
        events: List<KClass<*>>,
        priority: Int = 0,
        crossinline onEvent: (Any) -> Unit,
    ) {
        events.forEach { eventClass ->
            // 为每种事件类型创建订阅者
            val subscriber =
                object : EventSubscriber<Any> {
                    override fun onEvent(event: Any) {
                        onEvent(event)
                    }
                }

            // 直接调用EventBus的subscribe方法
            when (this) {
                is EventBus -> {
                    // 使用类型擦除的方式调用
                    @Suppress("UNCHECKED_CAST")
                    subscribe(eventClass as KClass<Any>, subscriber, priority)
                }
                else -> {
                    LogUtils.w("不支持的EventBus类型")
                }
            }
        }
    }
}
