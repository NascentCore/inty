package com.architecture.httplib.core

import ai.sxwl.android.utils.LogUtils
import com.architecture.httplib.error.BusinessException
import com.squareup.moshi.JsonAdapter
import com.squareup.moshi.JsonReader
import com.squareup.moshi.JsonWriter
import com.squareup.moshi.Moshi
import com.squareup.moshi.rawType
import java.lang.reflect.ParameterizedType
import java.lang.reflect.Type

/**
 *：Json闹钟。工厂决定将数据容量外包到T上面来。比如NewsChannelsBean
 *
 * 将 Java 值转换为 JSON，将 JSON 值转换为 Java。*
 * @GET("release/channel") 暂停 getNewsChannelsWithoutEnvelope() 的乐趣：
 * HttpResponse<NewsChannelsBean>
 *
 * 视频1：30约90分钟
 */
class MoshiResultTypeAdapterFactory(private val httpWrapper: HttpWrapper?) : JsonAdapter.Factory {

    /**
     * HttpResultWrapper
     *
     * 假设公司各个业务服务器返回的Http Json数据格式都差不多三个大字段（名称允许自定义不同）code[int] + msg[str] +data[T]
     * 这里我们统一约定含有三个类似的字段来包装数据包装数据，每个Http请求正常都会含有这三个字段，不同数据中的数据，很自然的我们使用范式T来表示。
     *
     * 根据项目自身的情况再次拓展以增强支撑性
     */
    interface HttpWrapper {
        fun getStatusCodeKey(): String

        fun getErrorMsgKey(): String

        fun getDataKey(): String // 一般会命名为result data
// 有些服务器是0代表成功，有些是200代表成功，我司的java和Python后台就没有统一过
// 这里的成功是指业务请求的成功，请和Http响应码区分
        fun isRequestSuccess(statusCode: Int): Boolean
    }

    override fun create(
        type: Type,
        annotations: MutableSet<out Annotation>,
        moshi: Moshi,
    ): JsonAdapter<*>? {

        val rawType = type.rawType

        if (rawType != HttpResult::class.java) return null

        val dataType: Type =
            (type as? ParameterizedType)?.actualTypeArguments?.firstOrNull() ?: return null

        val dataTypeAdapter = moshi.nextAdapter<Any>(this, dataType, annotations)
// Result<T> 范型解析出来
        return ResultTypeAdapter(dataTypeAdapter, httpWrapper)
    }

    /** 返回请求需求的那个T */
    class ResultTypeAdapter<T>(
        private val dataTypeAdapter: JsonAdapter<T>,
        val httpWrapper: HttpWrapper?,
    ) : JsonAdapter<T>() {

        /** 从给定的读取器中解码类型T的辅助空实例。*/
        override fun fromJson(reader: JsonReader): T? {
            if (httpWrapper != null) {
                var errcode: Int? = null
                var msg: String? = null
                var data: Any? = null
                var errcodeFound = false

                val peeked = reader.peekJson()
                peeked.beginObject()
                while (peeked.hasNext()) {
                    if (peeked.nextName() == httpWrapper.getStatusCodeKey()) {
                        errcodeFound = true
                        break
                    }
                    peeked.skipValue()
                }
                peeked.close()

                if (!errcodeFound) {
// 未找到“错误代码”，原始数据对象
                    return dataTypeAdapter.fromJson(reader)
                }

                reader.beginObject()
                while (reader.hasNext()) {
                    val nextName = reader.nextName()
                    when (nextName) {
// 根据不同服务器后台HTTP报文字段 解析映射出码 +msg + data
                        httpWrapper.getStatusCodeKey() -> {
                            val errorNum = reader.readJsonValue()
                            errcode =
                                when (errorNum) {
                                    is Number -> errorNum.toInt()
                                    is String -> errorNum.toIntOrNull()
                                    else -> -1
                                }
                        }

                        httpWrapper.getErrorMsgKey() -> msg = reader.nextString()
                        httpWrapper.getDataKey() -> {
// 处理返回 data = "" 的问题
// https://juejin.cn/post/6969841959082917901

                            try {
                                data = dataTypeAdapter.fromJson(reader)
                            } catch (e: Exception) {
                                LogUtils.e(e.message)
                                data = reader.nextString()
                                reader.skipValue()
                            }
// val readData = reader.读取JsonValue()
// if (readData 是字符串) {
// 数据 = 读取数据
// }另外{
// 数据 =
// dataTypeAdapter.fromJson(com.ata.utils.toJson(readData))
// }

                        }

                        else -> reader.skipValue()
                    }
                }

                reader.endObject()
//该字段要查看是否是服务器是否是必传字段
//否则请抛出异常
                if (errcode == null) {
// 抛出 JsonDataException("预期字段 [错误代码] 不是 present.”）
                    errcode = -1 // Assign a default error code if not present
                }

                if (httpWrapper.isRequestSuccess(errcode)) {
                    return data as T
                } else {
                    throw BusinessException(errcode, msg)
                }
            } else {
// 信封 == null 不是标准的Code + msg +data 也没关系
                return dataTypeAdapter.fromJson(reader) as T
            }
        }

        /** 使用给定的编写器对给定的值进行编码。后面吧*/
        override fun toJson(writer: JsonWriter, value: T?) {}
    }
}
