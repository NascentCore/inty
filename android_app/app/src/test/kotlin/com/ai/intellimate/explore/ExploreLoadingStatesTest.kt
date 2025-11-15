package com.ai.intellimate.explore

import ai.sxwl.android.data.api.model.AgentInfo
import androidx.compose.ui.test.assertDoesNotExist
import androidx.compose.ui.test.assertExists
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.onNodeWithTag
import androidx.paging.CombinedLoadStates
import androidx.paging.LoadState
import androidx.paging.LoadStates
import androidx.paging.compose.LazyPagingItems
import io.mockk.every
import io.mockk.mockk
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class ExploreLoadingStatesTest {

    @get:Rule val composeTestRule = createComposeRule()

    @Test
    fun loadingIndicatorVisibleOnlyWhenAppendLoadingAndEligible() {
        val items =
            lazyPagingItems(
                append = LoadState.Loading,
                refresh = LoadState.NotLoading(endOfPaginationReached = false),
                prepend = LoadState.NotLoading(endOfPaginationReached = false),
                itemCount = 5,
            )

        composeTestRule.setContent {
            ExploreLoadingStates(
                lazyPagingItems = items,
                showLoadMoreLoading = true,
                isRefreshing = false,
            )
        }

        composeTestRule.onNodeWithTag(LOAD_MORE_INDICATOR_TAG).assertExists()

        composeTestRule.setContent {
            ExploreLoadingStates(
                lazyPagingItems = items,
                showLoadMoreLoading = true,
                isRefreshing = true,
            )
        }

        composeTestRule.onNodeWithTag(LOAD_MORE_INDICATOR_TAG).assertDoesNotExist()
    }

    @Test
    fun noMoreDataIndicatorAppearsWhenPaginationEnds() {
        val items =
            lazyPagingItems(
                append = LoadState.NotLoading(endOfPaginationReached = true),
                refresh = LoadState.NotLoading(endOfPaginationReached = false),
                prepend = LoadState.NotLoading(endOfPaginationReached = false),
                itemCount = 3,
            )

        composeTestRule.setContent {
            ExploreLoadingStates(
                lazyPagingItems = items,
                showLoadMoreLoading = false,
                isRefreshing = false,
            )
        }

        composeTestRule.onNodeWithTag(NO_MORE_DATA_TAG).assertExists()
    }

    @Test
    fun errorIndicatorAppearsWhenAppendFails() {
        val items =
            lazyPagingItems(
                append = LoadState.Error(Exception("boom")),
                refresh = LoadState.NotLoading(endOfPaginationReached = false),
                prepend = LoadState.NotLoading(endOfPaginationReached = false),
                itemCount = 3,
            )

        composeTestRule.setContent {
            ExploreLoadingStates(
                lazyPagingItems = items,
                showLoadMoreLoading = false,
                isRefreshing = false,
            )
        }

        composeTestRule.onNodeWithTag(LOAD_MORE_ERROR_TAG).assertExists()
    }

    private fun lazyPagingItems(
        append: LoadState,
        refresh: LoadState,
        prepend: LoadState,
        itemCount: Int,
    ): LazyPagingItems<AgentInfo> {
        val mockItems = mockk<LazyPagingItems<AgentInfo>>(relaxed = true)
        every { mockItems.itemCount } returns itemCount
        every { mockItems.loadState } returns
            CombinedLoadStates(
                refresh = refresh,
                prepend = prepend,
                append = append,
                source = LoadStates(refresh = refresh, prepend = prepend, append = append),
                mediator = null,
            )
        return mockItems
    }
}
