package ai.sxwl.android.data.api

import ai.sxwl.android.data.api.model.TextToSpeechVoiceOption
import com.architecture.httplib.core.HttpResult
import retrofit2.http.GET
import retrofit2.http.Query

interface ITextToSpeechApi {
    @GET("/api/v1/text-to-speech/list-voices")
    suspend fun listVoices(
        @Query("provider") provider: String? = null,
        @Query("page_size") pageSize: Int? = null,
    ): HttpResult<List<TextToSpeechVoiceOption>>
}
