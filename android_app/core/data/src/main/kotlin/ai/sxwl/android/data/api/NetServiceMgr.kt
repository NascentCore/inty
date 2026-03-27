package ai.sxwl.android.data.api

import ai.sxwl.android.data.http.UnifiedOkHttpClient
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResponseCallAdapterFactory
import com.architecture.httplib.core.MoshiResultTypeAdapterFactory
import com.architecture.httplib.error.GlobalErrorHandler
import com.jakewharton.retrofit2.adapter.kotlin.coroutines.CoroutineCallAdapterFactory
import com.squareup.moshi.DefaultIfNullFactory
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import java.util.concurrent.ConcurrentHashMap
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory

/**
 * Retrofit/Moshi 网络管理器。
 *
 * ## 用途
 * 管理基于 Retrofit + Moshi 的网络请求。
 *
 * ## 共享基础设施
 * - `UnifiedOkHttpClient`: 统一的 OkHttpClient 实例
 * - `NetworkConfig`: 统一的环境配置和 baseUrl 管理
 * - `DebugBackendEndpointStore`: 运行时 URL 切换支持
 *
 * ## 缓存机制
 * - Retrofit 实例缓存: 基于 `baseUrl` (key: `baseUrl`)
 * - API 接口实例缓存: 基于 `baseUrl + API 类型` (key: `"${baseUrl}_${ApiType}"`)
 *
 * ## 响应格式
 * 返回 `HttpResult<T>` 包装：
 * - `HttpResult.Success<T>`: 请求成功
 * - `HttpResult.Failure`: 请求失败（包含错误信息）
 */
object NetServiceMgr {

    /** 使用统一的 OkHttpClient，包含所有必要的拦截器和配置 */
    private val okHttpClient: OkHttpClient
        get() = UnifiedOkHttpClient.create()

    private val moshi: Moshi
        get() {
            return Moshi.Builder()
                // 添加返回的json 数据自定义解析器
                .add(DefaultIfNullFactory())
                .add(MoshiResultTypeAdapterFactory(getHttpWrapperHandler()))
                .addLast(KotlinJsonAdapterFactory()) //
                .build()
        }

    private val moshiNoWrapper: Moshi
        get() {
            return Moshi.Builder()
                // 添加返回的json 数据自定义解析器
                .add(DefaultIfNullFactory())
                .add(MoshiResultTypeAdapterFactory(null))
                .addLast(KotlinJsonAdapterFactory()) //
                .build()
        }

    private val globalErrorHandler = GlobalErrorHandler()

    /**
     * Retrofit 实例缓存，基于 baseUrl 进行缓存 缓存 key 格式: `baseUrl` 或 `"${baseUrl}_no_wrapper"`
     */
    private val retrofitCache = ConcurrentHashMap<String, Retrofit>()

    /**
     * API 接口实例缓存，基于 baseUrl + API 类型进行缓存 缓存 key 格式: `"${baseUrl()}_${ApiType}"` 例如:
     * `"https://dev.inty.sxwl.ai/_IUserApi"`
     */
    private val apiCache = ConcurrentHashMap<String, Any>()

    // todo 这里使用wrapper来区分 是否带有外部code，message，data格式的响应数据体
    private fun getHttpWrapperHandler(): MoshiResultTypeAdapterFactory.HttpWrapper {

        return object : MoshiResultTypeAdapterFactory.HttpWrapper {
            override fun getStatusCodeKey(): String {
                return "code"
            }

            override fun getErrorMsgKey(): String {
                return "message"
            }

            override fun getDataKey(): String {
                return "data"
            }

            override fun isRequestSuccess(statusCode: Int): Boolean {
                return statusCode == 200 // 200 表示业务上是正确返回了数据
            }
        }
    }

    /** 获取基础URL，使用 NetworkConfig 以支持运行时覆盖 */
    fun baseUrl(): String {
        return NetworkConfig.getBaseUrl()
    }

    /*
     * 获取 Retrofit 实例（带 wrapper）
     * 后端不返回错误信息时，这个 wrapper 才能使用。
     */
    private fun getRetrofitNormal(): Retrofit {
        val currentBaseUrl = baseUrl()
        return retrofitCache.getOrPut(currentBaseUrl) {
            LogUtils.d(
                "NetServiceMgr",
                "Creating new Retrofit instance with baseUrl: $currentBaseUrl",
            )
            Retrofit.Builder()
                .baseUrl(currentBaseUrl)
                .client(okHttpClient)
                .addConverterFactory(MoshiConverterFactory.create(moshi))
                .addCallAdapterFactory(CoroutineCallAdapterFactory())
                .addCallAdapterFactory(
                    HttpResponseCallAdapterFactory(globalErrorHandler) // 全局的错误处理器
                )
                .build()
        }
    }

    /*
     * 获取 Retrofit 实例（不带 wrapper，wrapper 用于处理业务错误码和成功状态判断）
     * 后端不返回错误信息时，这个 wrapper 不能使用。
     */
    private fun getRetrofitNoWrapper(): Retrofit {
        val currentBaseUrl = baseUrl()
        val cacheKey = "${currentBaseUrl}_no_wrapper"
        return retrofitCache.getOrPut(cacheKey) {
            LogUtils.d(
                "NetServiceMgr",
                "Creating new Retrofit instance (no wrapper) with baseUrl: $currentBaseUrl",
            )
            Retrofit.Builder()
                .baseUrl(currentBaseUrl)
                .client(okHttpClient)
                .addConverterFactory(MoshiConverterFactory.create(moshiNoWrapper))
                .addCallAdapterFactory(CoroutineCallAdapterFactory())
                .addCallAdapterFactory(
                    HttpResponseCallAdapterFactory(globalErrorHandler) // 全局的错误处理器
                )
                .build()
        }
    }

    /**
     * 清除 Retrofit 和 API 实例缓存。
     *
     * ## 调用时机
     * 1. Debug build 专用：当用户需要切换后端地址时调用
     * 2. 当用户登录状态发生变化时调用
     */
    fun clearCache() {
        retrofitCache.clear()
        apiCache.clear()
        LogUtils.i("NetServiceMgr", "Cleared Retrofit and API instance cache")
    }

    /**
     * 获取用户相关 API 接口实例
     *
     * 缓存 key: `"${baseUrl()}_IUserApi"` 当 baseUrl 变化时，会自动创建新的 Retrofit 和 API 实例
     */
    fun getUserApi(): IUserApi {
        val cacheKey = "${baseUrl()}_IUserApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) { getRetrofitNormal().create(IUserApi::class.java) }
            as IUserApi
    }

    fun getAgentApi(): IAgentApi {
        val cacheKey = "${baseUrl()}_IAgentApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) { getRetrofitNormal().create(IAgentApi::class.java) }
            as IAgentApi
    }

    fun getChatApi(): IChatApi {
        val cacheKey = "${baseUrl()}_IChatApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) { getRetrofitNoWrapper().create(IChatApi::class.java) }
            as IChatApi
    }

    fun getReportApi(): IReportApi {
        val cacheKey = "${baseUrl()}_IReportApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) { getRetrofitNoWrapper().create(IReportApi::class.java) }
            as IReportApi
    }

    fun getSubscriptionApi(): ISubscriptionApi {
        val cacheKey = "${baseUrl()}_ISubscriptionApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) {
            getRetrofitNormal().create(ISubscriptionApi::class.java)
        } as ISubscriptionApi
    }

    fun getCommonApi(): ICommonApi {
        val cacheKey = "${baseUrl()}_ICommonApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) { getRetrofitNormal().create(ICommonApi::class.java) }
            as ICommonApi
    }

    fun getTextToSpeechApi(): ITextToSpeechApi {
        val cacheKey = "${baseUrl()}_ITextToSpeechApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) {
            getRetrofitNoWrapper().create(ITextToSpeechApi::class.java)
        } as ITextToSpeechApi
    }
}
