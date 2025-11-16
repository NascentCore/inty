package ai.sxwl.android.data.api

import ai.sxwl.android.data.http.UnifiedOkHttpClient
import ai.sxwl.android.data.http.config.Constant
import ai.sxwl.android.data.http.config.NetworkConfig
import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.core.HttpResponseCallAdapterFactory
import com.architecture.httplib.core.MoshiResultTypeAdapterFactory
import com.architecture.httplib.error.GlobalErrorHandler
import com.jakewharton.retrofit2.adapter.kotlin.coroutines.CoroutineCallAdapterFactory
import com.squareup.moshi.DefaultIfNullFactory
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.moshi.MoshiConverterFactory
import java.util.concurrent.ConcurrentHashMap

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

    // Retrofit 实例缓存，基于 baseUrl 进行缓存
    private val retrofitCache = ConcurrentHashMap<String, Retrofit>()
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

    /** 获取 Retrofit 实例（带 wrapper） */
    private fun getRetrofitNormal(): Retrofit {
        val currentBaseUrl = baseUrl()
        return retrofitCache.getOrPut(currentBaseUrl) {
            LogUtils.d("NetServiceMgr", "Creating new Retrofit instance with baseUrl: $currentBaseUrl")
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

    /** 获取 Retrofit 实例（不带 wrapper） */
    private fun getRetrofitNoWrapper(): Retrofit {
        val currentBaseUrl = baseUrl()
        val cacheKey = "${currentBaseUrl}_no_wrapper"
        return retrofitCache.getOrPut(cacheKey) {
            LogUtils.d("NetServiceMgr", "Creating new Retrofit instance (no wrapper) with baseUrl: $currentBaseUrl")
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

    /** 清除 Retrofit 和 API 实例缓存，用于 baseUrl 切换时 */
    fun clearCache() {
        retrofitCache.clear()
        apiCache.clear()
        LogUtils.i("NetServiceMgr", "Cleared Retrofit and API instance cache")
    }

    fun getUserApi(): IUserApi {
        val cacheKey = "${baseUrl()}_IUserApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) {
            getRetrofitNormal().create(IUserApi::class.java)
        } as IUserApi
    }

    fun getAgentApi(): IAgentApi {
        val cacheKey = "${baseUrl()}_IAgentApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) {
            getRetrofitNormal().create(IAgentApi::class.java)
        } as IAgentApi
    }

    fun getChatApi(): IChatApi {
        val cacheKey = "${baseUrl()}_IChatApi"
        @Suppress("UNCHECKED_CAST")
        return apiCache.getOrPut(cacheKey) {
            getRetrofitNoWrapper().create(IChatApi::class.java)
        } as IChatApi
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
        return apiCache.getOrPut(cacheKey) {
            getRetrofitNormal().create(ICommonApi::class.java)
        } as ICommonApi
    }
}
