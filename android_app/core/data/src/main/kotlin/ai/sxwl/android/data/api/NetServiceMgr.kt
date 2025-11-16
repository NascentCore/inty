package ai.sxwl.android.data.api

import ai.sxwl.android.data.http.UnifiedOkHttpClient
import ai.sxwl.android.data.http.config.NetworkConfig
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

/** 获取基础URL 根据运行时配置返回对应的API基础URL */
private fun getBaseUrl(): String {
    return NetworkConfig.getBaseUrl()
}

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

    fun baseUrl(): String {
        return getBaseUrl()
    }

    private val retrofitNormal: Retrofit
        get() {

            val retrofitUser =
                Retrofit.Builder()
                    .baseUrl(baseUrl())
                    .client(okHttpClient)
                    .addConverterFactory(MoshiConverterFactory.create(moshi))
                    .addCallAdapterFactory(CoroutineCallAdapterFactory())
                    .addCallAdapterFactory(
                        HttpResponseCallAdapterFactory(globalErrorHandler) // 全局的错误处理器
                    )
                    .build()

            return retrofitUser
        }

    private val retrofitNoWrapper: Retrofit
        get() {
            val retrofitUser =
                Retrofit.Builder()
                    .baseUrl(baseUrl())
                    .client(okHttpClient)
                    .addConverterFactory(MoshiConverterFactory.create(moshiNoWrapper))
                    .addCallAdapterFactory(CoroutineCallAdapterFactory())
                    .addCallAdapterFactory(
                        HttpResponseCallAdapterFactory(globalErrorHandler) // 全局的错误处理器
                    )
                    .build()

            return retrofitUser
        }

    fun getUserApi(): IUserApi {
        return retrofitNormal.create(IUserApi::class.java)
    }

    fun getAgentApi(): IAgentApi {
        return retrofitNormal.create(IAgentApi::class.java)
    }

    fun getChatApi(): IChatApi {
        return retrofitNoWrapper.create(IChatApi::class.java)
    }

    fun getSubscriptionApi(): ISubscriptionApi {
        return retrofitNormal.create(ISubscriptionApi::class.java)
    }

    fun getCommonApi(): ICommonApi {
        return retrofitNormal.create(ICommonApi::class.java)
    }
}
