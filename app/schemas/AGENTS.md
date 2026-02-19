# Pydantic models for API endpoints

- 不要使用 model_config 在 Pydantic Model 对象中：否则会与内置变量冲突：<https://docs.pydantic.dev/2.0/usage/model_config/>
- 更改 HTTP API request response 数据类型之后，要更新 [kotlin 数据类型定义](../../android_app/library/inty)
- 修改 [response.py](response.py)（如业务错误码、API 响应规则、HTTP 状态码/body code/data.error_code 约定）时，需同步更新 [BusinessErrorCodes.kt](../../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/BusinessErrorCodes.kt)

## app/schemas 与 Kotlin 对应关系

以下 Kotlin 文件在概念或数值上均对应 [response.py](response.py)，修改 response.py 时需检查并同步这些文件：

| Kotlin 文件 | 对应 app/schemas | 说明 |
|-------------|------------------|------|
| [Response.kt](../../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/Response.kt) | response.py | 无一一对应类型。服务端返回 [APIResponse](response.py)（code, message, data），Kotlin 用 ApiResult.Success / ApiResult.Error 表示一次调用的成功/失败；与响应结构和错误码约定均来自 response.py。 |
| [BusinessErrorCodes.kt](../../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/BusinessErrorCodes.kt) | response.py | 与 BusinessErrorCode 的 8 个错误字典、BusinessErrorCodeEnum 的 code/error_code/message 一一对应。 |
| [IntyErrorCode.kt](../../android_app/core/data/src/main/kotlin/ai/sxwl/android/data/http/IntyErrorCode.kt) | response.py | 业务错误数字码与 BusinessErrorCode / BusinessErrorCodeEnum 的 code 一致；枚举为 Kotlin 独有。SESSION_ERROR、UNKNOWN 为客户端自用，后端无对应定义。 |
