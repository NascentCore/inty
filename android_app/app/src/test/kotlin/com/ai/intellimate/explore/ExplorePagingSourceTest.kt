// CREATED_BY_AGENT
package com.ai.intellimate.explore

import ai.sxwl.android.data.api.IAgentApi
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.api.model.AgentInfoResponse
import ai.sxwl.android.data.api.model.CreateAgentRequest
import ai.sxwl.android.data.api.model.GenerateBackgroundRequest
import ai.sxwl.android.data.api.model.GenerateBackgroundResponse
import ai.sxwl.android.data.api.model.UploadAvatarResponse
import ai.sxwl.android.data.cache.RecommendedAgentCacheProvider
import androidx.paging.PagingSource
import com.architecture.httplib.core.HttpResult
import kotlin.test.assertEquals
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.runTest
import okhttp3.MultipartBody
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config

@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(RobolectricTestRunner::class)
@Config(manifest = Config.NONE)
class ExplorePagingSourceTest {

    @Test
    fun `deduplicates cache and network agents`() = runTest {
        val duplicateId = "agent-1"
        val cachedAgents =
            listOf(
                agent(id = duplicateId, name = "Alpha"),
                agent(id = duplicateId, name = "Alpha Clone"),
                agent(id = "agent-2", name = "Beta"),
            )
        val networkAgents =
            listOf(
                agent(id = duplicateId, name = "Alpha From Network"),
                agent(id = "agent-3", name = "Gamma"),
            )

        val cacheProvider = FakeCacheProvider(cachedAgents)
        val pagingSource =
            ExplorePagingSource(
                useCache = true,
                cacheProvider = cacheProvider,
                agentApiProvider = { FakeAgentApi(mapOf(2 to networkAgents)) },
            )

        val refreshResult =
            pagingSource.load(
                PagingSource.LoadParams.Refresh(
                    key = null,
                    loadSize = PAGE_SIZE_FOR_TEST,
                    placeholdersEnabled = false,
                )
            ) as PagingSource.LoadResult.Page<Int, AgentInfo>
        assertEquals(listOf("agent-1", "agent-2"), refreshResult.data.map { it.id })

        val appendResult =
            pagingSource.load(
                PagingSource.LoadParams.Append(
                    key = 2,
                    loadSize = PAGE_SIZE_FOR_TEST,
                    placeholdersEnabled = false,
                )
            ) as PagingSource.LoadResult.Page<Int, AgentInfo>
        assertEquals(listOf("agent-3"), appendResult.data.map { it.id })
    }

    private fun agent(id: String, name: String) = AgentInfo(id = id, name = name)

    private class FakeCacheProvider(
        private var cachedAgents: List<AgentInfo>,
        private val shouldUpdate: Boolean = false,
    ) : RecommendedAgentCacheProvider {
        override suspend fun getCachedRecommendedAgents(): List<AgentInfo> = cachedAgents

        override suspend fun cacheRecommendedAgents(agents: List<AgentInfo>) {
            cachedAgents = agents
        }

        override suspend fun shouldUpdateFromNetwork(): Boolean = shouldUpdate

        override suspend fun refreshRecommendedAgents() = Unit
    }

    private class FakeAgentApi(
        private val pageResponses: Map<Int, List<AgentInfo>>,
        private val totalPages: Int = 2,
    ) : IAgentApi {
        override suspend fun exploreAgents(
            page: Int,
            pageSize: Int,
            sort_seed: String,
            sort: String,
        ): HttpResult<AgentInfoResponse> {
            val list = pageResponses[page] ?: emptyList()
            return HttpResult.Success(
                AgentInfoResponse(
                    list = list,
                    total = pageResponses.values.sumOf { it.size },
                    page = page,
                    pageSize = pageSize,
                    totalPages = totalPages,
                )
            )
        }

        override suspend fun chatAgents(
            page: Int,
            pageSize: Int,
            sort_seed: String,
            sort: String,
        ): HttpResult<AgentInfoResponse> = error("Unused in tests")

        override suspend fun createAgent(request: CreateAgentRequest): HttpResult<AgentInfo> =
            error("Unused in tests")

        override suspend fun getUserCreatedAgents(
            skip: Int,
            limit: Int,
        ): HttpResult<List<AgentInfo>> = error("Unused in tests")

        override suspend fun generateBackground(
            request: GenerateBackgroundRequest
        ): HttpResult<GenerateBackgroundResponse> = error("Unused in tests")

        override suspend fun getAgentDetail(agentId: String): HttpResult<AgentInfo> =
            error("Unused in tests")

        override suspend fun updateAgent(
            agentId: String,
            request: CreateAgentRequest,
        ): HttpResult<AgentInfo> = error("Unused in tests")

        override suspend fun deleteAgent(agentId: String): HttpResult<AgentInfo> =
            error("Unused in tests")

        override suspend fun uploadAvatar(
            file: MultipartBody.Part
        ): HttpResult<UploadAvatarResponse> = error("Unused in tests")
    }

    companion object {
        private const val PAGE_SIZE_FOR_TEST = 8
    }
}
