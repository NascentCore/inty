package com.ai.inty.net

import com.ai.inty.beans.AppVersionRsp
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.POST

@Singleton
interface ICommonApi {
    @POST("api/v1/version/check")
    suspend fun checkAppUpgrade(): HttpResult<AppVersionRsp.AppVersionData>
}
