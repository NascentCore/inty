package com.ai.intellimate.explore

import org.junit.Assert.assertEquals
import org.junit.Test

class ExploreLazyGridIndicesTest {

    @Test
    fun `max index without paging is spacer tail`() {
        assertEquals(1, exploreLazyGridMaxItemIndex(themeItemCount = 0, pagingItemCount = null))
        assertEquals(1, exploreLazyGridMaxItemIndex(themeItemCount = 3, pagingItemCount = null))
    }

    @Test
    fun `max index with paging adds themes agents loading and spacer`() {
        // 0 theme, 0 agents -> loading + spacer -> indices 0,1 -> max 1
        assertEquals(1, exploreLazyGridMaxItemIndex(0, 0))
        // 2 themes, 5 agents -> 2 + 5 + 2 - 1 = 8
        assertEquals(8, exploreLazyGridMaxItemIndex(2, 5))
    }
}
