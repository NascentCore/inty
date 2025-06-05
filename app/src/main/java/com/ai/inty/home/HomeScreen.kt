package com.ai.inty.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.chat.ChatPage
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.viewmodels.ChatViewModel
import com.ai.inty.viewmodels.HomeTabIndex
import com.ai.inty.viewmodels.MainViewModel

data class TabInfo(
    val normalImage: Int,
    val selectedImage: Int,
)
val MAIN_TAB_LIST = listOf(
    TabInfo(R.drawable.tab_chat, R.drawable.tab_chat_selected),
    TabInfo(R.drawable.tab_msg, R.drawable.tab_msg_selected),
    TabInfo(R.drawable.tab_add, R.drawable.tab_add),
    TabInfo(R.drawable.tab_suggest, R.drawable.tab_suggest_selected),
    TabInfo(R.drawable.tab_my, R.drawable.tab_my_selected),
)


@Composable
fun HomeScreen(
    modifier: Modifier = Modifier,
    mainViewModel: MainViewModel,
    chatViewModel: ChatViewModel,
) {

    val selectedTab = mainViewModel.selectedTab.collectAsState()


    Scaffold(
        modifier = modifier.fillMaxSize().background(BackGround),
        containerColor = Color.Transparent,
        topBar = {
        },
        bottomBar = {
            BottomBar(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(BackGround)
                    .height(48.25.dp),
                selectedTab = selectedTab.value.ordinal,
                onSelectTab = {
                    if (it == HomeTabIndex.Add.ordinal) {
                        mainViewModel.showSnackbar("ADD")
                        return@BottomBar
                    }
                    mainViewModel.selectTab(it)
                }
            )
        }
    ) { innerPadding ->
        when (selectedTab.value) {
            HomeTabIndex.Chat -> {
                ChatPage(
                    modifier = Modifier.padding(0.dp, 0.dp, 0.dp, innerPadding.calculateBottomPadding()),
                    chatViewModel = chatViewModel,
                )
            }
            HomeTabIndex.Conversions -> {
                Box(modifier = Modifier.padding(innerPadding).background(Color.Yellow),) {
                    Text("会话列表")
                }
            }
            HomeTabIndex.Add -> {
            }
            HomeTabIndex.Suggest -> {
                Box(modifier = Modifier.padding(innerPadding).background(Color.Yellow),) {
                    Text("推荐")
                }
            }
            HomeTabIndex.My -> {
                Box(modifier = Modifier.padding(innerPadding).background(Color.Yellow),) {
                    Text("我的")
                }
            }
        }
    }

}

@Composable
fun BottomBar(
    modifier: Modifier,
    selectedTab: Int,
    onSelectTab: (Int) -> Unit
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        MAIN_TAB_LIST.forEachIndexed { index, tab ->
            BottomBarItem(
                modifier = Modifier.fillMaxHeight().weight(1f).noRippleClickable {
                    onSelectTab(index)
                },
                tabInfo = tab,
                selected = (index == selectedTab),
            )
        }
    }
}

@Composable
fun BottomBarItem(
    modifier: Modifier,
    tabInfo: TabInfo,
    selected: Boolean,
) {
    Box(modifier = modifier) {
        IntyImage(
            modifier = Modifier.size(42.dp).align(Alignment.Center),
            model = if (selected) tabInfo.selectedImage else tabInfo.normalImage
        )
    }
}

