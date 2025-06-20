package com.ai.inty.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.IntyImage
import com.ai.inty.base.RedDot
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.ConversationItem
import com.ai.inty.beans.SysMsgItem


enum class ConversionsPageTab {
    TabMessage,
    TabFollowing
}

@Composable
fun ConversionsPage(
    modifier: Modifier,
    selectedTab: ConversionsPageTab,
    conversions: List<ConversationItem>,
    lastSysMsg: SysMsgItem?,
    onSelectTab: (ConversionsPageTab) -> Unit,
    onClickConversionItem: (ConversationItem) -> Unit,
    onClickSysMsg: () -> Unit,
) {
    Box(
        modifier = modifier
    ) {
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )
        Scaffold(
            modifier = Modifier
                .fillMaxSize()
                .background(Color.Transparent),
            containerColor = Color.Transparent
        ) { innerPadding ->

            Column {
                Spacer(Modifier.height(innerPadding.calculateTopPadding() + 28.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                ) {

                    ConversionsPageTabItem(
                        Modifier.noRippleClickable {
                            onSelectTab(ConversionsPageTab.TabMessage)
                        },
                        stringResource(R.string.tab_message), selectedTab==ConversionsPageTab.TabMessage
                    )
//                    Spacer(Modifier.width(15.dp))
//                    ConversionsPageTabItem(
//                        Modifier.noRippleClickable {
//                            onSelectTab(ConversionsPageTab.TabFollowing)
//                        },
//                        stringResource(R.string.tab_following), selectedTab==ConversionsPageTab.TabFollowing
//                    )
                }

                Spacer(Modifier.height(22.dp))

                ConversionsPage(
                    modifier = Modifier.fillMaxWidth(),
                    conversions = conversions,
                    onClickConversionItem = {
                        onClickConversionItem(it)
                    },
                    lastSysMsg = lastSysMsg,
                    onClickSysMsg = onClickSysMsg
                )
            }
        }
    }
}

@Composable
fun ConversionsPageTabItem(
    modifier: Modifier,
    text: String,
    isSelected: Boolean,
) {
    Column(
        modifier = modifier.size(120.dp, 38.dp)
    ) {
        if (isSelected) {
            val colorStops = arrayOf(
                0.0f to Color(0xFFFF905D),
                1.0f to Color(0xFFC122FF)
            )
            val brush = Brush.horizontalGradient(colorStops = colorStops)

            Text(
                modifier = Modifier.align(Alignment.CenterHorizontally),
                text = text,
                style = TextStyle(
                    brush = brush,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,

                ),
            )
            IntyImage(
                modifier = Modifier.fillMaxWidth(),
                model = R.drawable.group43027
            )
        } else {
            Text(
                modifier = Modifier.align(Alignment.CenterHorizontally),
                text = text,
                style = TextStyle(
                    color = Color.White,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                )
            )
        }
    }
}




@Composable
fun ConversionsPage(
    modifier: Modifier,
    conversions: List<ConversationItem>,
    onClickConversionItem: (ConversationItem) -> Unit,
    lastSysMsg: SysMsgItem?,
    onClickSysMsg: () -> Unit,

    ) {
    val context = LocalContext.current
    LazyColumn(
        modifier = modifier,
    ) {

        lastSysMsg?.let { sysMsg ->
            item {
                ConversationItem(
                    modifier = Modifier
                        .fillMaxWidth()
                        .background(color = Color(0x3378599A))
                        .noRippleClickable {
                            onClickSysMsg()
                        },
                    conversation = ConversationItem(
                        agentId = Constant.SYS_NOTIFICATION_ID,
                        agentName = "System Notification",
                        lastMessage = sysMsg.content,
                        createdAt = sysMsg.createdAt
                    ),
                    placeholderID = R.drawable.icon_sys_notify
                )
            }
        }

        items(conversions) { conversion ->
            ConversationItem(
                modifier = Modifier.fillMaxWidth().noRippleClickable {
                    onClickConversionItem(conversion)
                },
                conversation = conversion
            )
        }
    }

}

@Composable
fun ConversationItem(
    modifier: Modifier,
    conversation: ConversationItem,
    placeholderID: Int = R.drawable.app_2
) {
    Row(
        modifier = modifier.height(88.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Spacer(Modifier.width(16.dp))

        IntyImage(
            modifier = Modifier.size(56.dp),
            model = conversation.agentAvatar,
            placeholder = painterResource(placeholderID)
        )

        Spacer(Modifier.width(14.dp))

        Column(
            modifier = Modifier.weight(1f)
        ) {
            Text(
                modifier = Modifier.height(22.dp),
                text = conversation.agentName,
                fontSize = 15.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            Spacer(Modifier.height(4.dp))
            Text(
                modifier = Modifier.height(22.dp),
                text = conversation.lastMessage,
                fontSize = 14.sp,
                color = Color.White.copy(0.55f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
        }
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = conversation.getShowTime(),
                fontSize = 12.sp,
                color = Color.White.copy(0.55f),
            )
            Spacer(Modifier.height(4.dp))
            Box(
                modifier = Modifier.height(22.dp),
                contentAlignment = Alignment.Center,
            ) {
                if (conversation.isNew) {
                    RedDot()
                }
            }
        }
        Spacer(Modifier.width(13.dp))
    }
}
