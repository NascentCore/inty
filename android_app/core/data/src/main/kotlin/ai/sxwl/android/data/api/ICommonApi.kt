package ai.sxwl.android.data.api

import ai.sxwl.android.data.api.model.AppVersionRsp
import com.architecture.httplib.core.HttpResult
import retrofit2.http.POST

interface ICommonApi {
    @POST("api/v1/version/check")
    suspend fun checkAppUpgrade(): HttpResult<AppVersionRsp.AppVersionData>
}
