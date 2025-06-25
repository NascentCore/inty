package com.ai.inty.net

import com.ai.inty.beans.UserProfile
import com.architecture.httplib.core.HttpResult
import com.therouter.inject.Singleton
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.PUT


@Singleton
interface IUserApi2 {
    @GET("/api/v1/users/profile")
    suspend fun getUserProfile(): HttpResult<UserProfile>

    @PUT("/api/v1/users/profile")
    suspend fun setUserProfile(@Body userProfile: UserProfile): HttpResult<UserProfile>
}