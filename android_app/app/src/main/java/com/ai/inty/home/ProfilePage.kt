package com.ai.inty.home

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.itemsIndexed
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.BiasAlignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.AntiClick
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.UserProfile
import com.ai.inty.billing.BillingRepository
import com.ai.inty.billing.VipStatus
import com.ai.inty.utils.AuthClickable
import com.inty.utils.formatTimestampToString
import com.therouter.TheRouter

/**
 * “我的”页面
 */
@Composable
internal fun ProfilePage(
    modifier: Modifier,
    userProfile: UserProfile,
    agents: List<AgentInfo>,
    onClickAgent: (AgentInfo) -> Unit,
    onEditAgent: ((AgentInfo) -> Unit)? = null,
    onDeleteAgent: ((AgentInfo) -> Unit)? = null,
    isLoading: Boolean = false,
    onLoadMore: () -> Unit = {},
) {
    val context = LocalContext.current
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

            Column(Modifier.fillMaxWidth()) {
                Spacer(Modifier.height(innerPadding.calculateTopPadding() + 28.dp))

                Row {
                    Spacer(Modifier.weight(1f))
                    AuthClickable(
                        onClick = {
                            TheRouter.build(Constant.ROUTE_SETTING)
                                .navigation(context)
                        }
                    ) { authModifier ->
                        IntyImage(
                            modifier = authModifier.size(24.dp),
                            model = R.drawable.icon_setting
                        )
                    }
                    Spacer(Modifier.width(16.dp))
                }

                Spacer(Modifier.height(24.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Spacer(Modifier.width(16.dp))
                    Box(
                        modifier = Modifier
                            .size(120.dp)
                            .background(color = Color.White, shape = CircleShape)
                            .padding(4.dp)
                    ) {
                        IntyCircleImage(
                            modifier = Modifier.fillMaxSize(),
                            url = userProfile.avatar,
                            placeholderResID = R.drawable.app_icon
                        )
                    }
                    Spacer(Modifier.width(19.dp))

                    Column(
                        modifier = Modifier.weight(1f),
                    ) {
                        Text(
                            text = userProfile.nickname,
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Spacer(Modifier.height(6.dp))
                        Text(
                            text = stringResource(R.string.ID, userProfile.readableId),
                            color = Color.White.copy(0.55f),
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Light,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }

                    Spacer(Modifier.width(16.dp))
                }

                Spacer(Modifier.height(24.dp))

                Row(
                    modifier = Modifier.padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {

                    Text(
                        modifier = Modifier.weight(1f),
                        text = userProfile.description
                            ?: stringResource(R.string.persona_placeholder),
                        color = Color.White,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Medium,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis
                    )

                    Spacer(Modifier.width(8.dp))

                    AuthClickable(
                        onClick = {
                            TheRouter.build(Constant.ROUTE_SETTING_MY)
                                .withObject("userProfile", userProfile)
                                .navigation(context)
                        }
                    ) { authModifier ->
                        IntyImage(
                            modifier = authModifier.size(40.dp),
                            model = R.drawable.icon_edit
                        )
                    }
                }

                Spacer(Modifier.height(24.dp))

                // IntelliMate Premium 会员入口按钮
                // VIP状态
                val vipStatus by BillingRepository.vipStatusFlow.collectAsState()
                PremiumBanner(
                    status = vipStatus.subscriptionStatus,
                    purchaseTime = formatTimestampToString(vipStatus.purchaseTime),
                    expireTime = formatTimestampToString(vipStatus.expiryTime),
                    onClick = { TheRouter.build(Constant.ROUTE_VIP_CENTER).navigation(context) })

                Spacer(Modifier.height(8.dp))

                if (agents.isEmpty()) {
                    Spacer(Modifier.height(48.dp))

                    IntyImage(
                        modifier = Modifier.align(Alignment.CenterHorizontally),
                        model = R.drawable.img_content_empty
                    )

                    Spacer(Modifier.height(16.dp))

                    Text(
                        modifier = Modifier
                            .padding(horizontal = 16.dp)
                            .align(Alignment.CenterHorizontally),
                        text = stringResource(R.string.no_agent),
                        color = Color.White.copy(0.55f),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Normal,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                } else {
                    Spacer(Modifier.height(10.dp))

                    val listState = rememberLazyGridState()

                    // Detect when user scrolls to bottom
                    LaunchedEffect(listState) {
                        snapshotFlow { listState.layoutInfo.visibleItemsInfo }
                            .collect { visibleItems ->
                                val lastVisibleItem = visibleItems.lastOrNull()
                                val totalItems = listState.layoutInfo.totalItemsCount

                                if (lastVisibleItem != null &&
                                    lastVisibleItem.index >= totalItems - 3 && // Trigger 3 items before end
                                    !isLoading &&
                                    agents.isNotEmpty()
                                ) {
                                    onLoadMore()
                                }
                            }
                    }

                    LazyVerticalGrid(
                        state = listState,
                        modifier = Modifier.padding(horizontal = 16.dp),
                        columns = GridCells.Fixed(2),
                        horizontalArrangement = Arrangement.spacedBy(13.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        runCatching {
                            if (agents.isNotEmpty()) {
                                itemsIndexed(
                                    items = agents,
                                    key = { index, agent -> "${agent.id}_$index" }
                                ) { index, agent ->
                                    MyAgentCard(
                                        modifier = Modifier.noRippleClickable {
                                            onClickAgent(agent)
                                        },
                                        agentInfo = agent,
                                        onEditAgent = onEditAgent,
                                        onDeleteAgent = onDeleteAgent
                                    )
                                }
                                //添加一个底部空白，便于更好操作交互
                                item { Spacer(Modifier.height(80.dp)) }
                            }
                        }.onFailure { it.printStackTrace() }

                        // Loading indicator when loading more
                        if (isLoading) {
                            item {
                                Box(
                                    modifier = Modifier
                                        .padding(16.dp),
                                    contentAlignment = Alignment.Center
                                ) {
                                    CircularProgressIndicator(
                                        color = Color.White,
                                        modifier = Modifier.size(24.dp)
                                    )
                                }
                            }
                        }

                        item {
                            Spacer(Modifier.height(16.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun MyAgentCard(
    modifier: Modifier,
    agentInfo: AgentInfo,
    onEditAgent: ((AgentInfo) -> Unit)? = null,
    onDeleteAgent: ((AgentInfo) -> Unit)? = null,
) {
    var showMenu by remember { mutableStateOf(false) }
    var showDeleteDialog by remember { mutableStateOf(false) }
    var lastClickTime by remember { mutableLongStateOf(0L) }

    Box(
        modifier = modifier
            .size(165.dp, 220.dp)
            .clip(RoundedCornerShape(12.dp))
    ) {
        IntyImage(
            modifier = Modifier.fillMaxSize(),
            model = agentInfo.avatar,
            placeholder = painterResource(R.drawable.app_icon),
            error = painterResource(R.drawable.app_icon),
        )

        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color.Transparent,
                            Color.Black.copy(.2f),
                            Color.Black.copy(.7f),
                            Color.Black,
                        ),
                    )
                )
                .padding(8.dp)
                .align(Alignment.BottomCenter),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IntyCircleImage(
                    modifier = Modifier.size(18.dp),
                    url = agentInfo.avatar,
                    placeholderResID = R.drawable.app_icon
                )
                Spacer(Modifier.width(4.dp))
                Text(
                    modifier = Modifier,
                    text = agentInfo.name,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )
            }
            Text(
                modifier = Modifier,
                text = agentInfo.intro,
                fontSize = 12.sp,
                lineHeight = 12.sp,
                color = Color.White.copy(.7f),
                maxLines = 3,
                overflow = TextOverflow.Ellipsis
            )
        }

        // 右下角的菜单按钮
        if (onEditAgent != null || onDeleteAgent != null) {
            Box(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(4.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(28.dp)
                        .background(
                            Color.Black.copy(alpha = 0.5f),
                            RoundedCornerShape(4.dp)
                        )
                        .noRippleClickable(onClick = {
                            val currentTime = System.currentTimeMillis()
                            if (AntiClick.isValidClick(lastClickTime)) {
                                lastClickTime = currentTime
                                showMenu = true
                            }
                        }), contentAlignment = Alignment.Center
                ) {
                    IntyImage(
                        modifier = Modifier.size(20.dp),
                        model = R.drawable.icon_more2
                    )
                }

                DropdownMenu(
                    expanded = showMenu,
                    onDismissRequest = { showMenu = false }
                ) {
                    onEditAgent?.let { editCallback ->
                        DropdownMenuItem(
                            text = {
                                Text(
                                    text = stringResource(R.string.edit_button),
                                    color = Color.White,
                                    fontSize = 14.sp
                                )
                            },
                            onClick = {
                                showMenu = false
                                editCallback(agentInfo)
                            }
                        )
                    }

                    onDeleteAgent?.let { deleteCallback ->
                        DropdownMenuItem(
                            text = {
                                Text(
                                    text = stringResource(R.string.delete_button),
                                    color = Color.Red,
                                    fontSize = 14.sp
                                )
                            },
                            onClick = {
                                showMenu = false
                                showDeleteDialog = true
                            }
                        )
                    }
                }
            }
        }

        // Delete confirmation dialog
        if (showDeleteDialog) {
            AlertDialog(
                onDismissRequest = { showDeleteDialog = false },
                title = {
                    Text(
                        text = stringResource(R.string.delete_character_full),
                        color = Color.White,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                },
                text = {
                    Text(
                        text = stringResource(
                            R.string.delete_character_confirm_full,
                            agentInfo.name
                        ),
                        color = Color.White,
                        fontSize = 14.sp
                    )
                },
                confirmButton = {
                    Button(
                        onClick = {
                            showDeleteDialog = false
                            onDeleteAgent?.invoke(agentInfo)
                        },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color.Red
                        )
                    ) {
                        Text(
                            text = stringResource(R.string.delete_button),
                            color = Color.White,
                            fontSize = 14.sp
                        )
                    }
                },
                dismissButton = {
                    Button(
                        onClick = { showDeleteDialog = false },
                        colors = ButtonDefaults.buttonColors(
                            containerColor = Color.Gray
                        )
                    ) {
                        Text(
                            text = stringResource(R.string.cancel_button_full),
                            color = Color.White,
                            fontSize = 14.sp
                        )
                    }
                },
                containerColor = Color(0xFF2A2A2A),
                titleContentColor = Color.White,
                textContentColor = Color.White
            )
        }
    }
}

/**
 * Premium Banner 组件
 */
@Preview
@Composable
private fun PremiumBanner(
    status: String? = "Activate Now",
    purchaseTime: String? = null,//购买日期
    expireTime: String? = null,//过期时间
    onClick: () -> Unit = {},
) {
    AuthClickable(
        modifier = Modifier
            .fillMaxWidth()
            .heightIn(120.dp)
            .padding(horizontal = 12.dp),
        onClick = onClick
    ) { authModifier ->
        Box(
            modifier = authModifier
        ) {
            Image(
                painter = painterResource(R.drawable.img_vip_banner),
                contentDescription = "",
                contentScale = ContentScale.FillWidth,
                modifier = Modifier.fillMaxWidth()
            )

            Row(
                Modifier
                    .border(
                        width = 0.5.dp,
                        color = Color(0x61D523FF),
                        shape = RoundedCornerShape(size = 12.dp)
                    )
                    .background(
                        color = Color(0x33D216FF),
                        shape = RoundedCornerShape(size = 12.dp)
                    )
                    .padding(horizontal = 8.dp)
                    .align(BiasAlignment(.95f, .1f)),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.Center

            ) {
                //三种UI状态显示，1. 无有效订阅 显示Activate Now；2. 有效订阅 显示Since 日期；3. 有订阅快过期 显示Expires ON 日期
                val str =
                    when (status) {
                        VipStatus.UI_SUBSCRIBED -> "Since $purchaseTime"
                        VipStatus.UI_SUBSCRIBED_EXPIRE_SOON -> "EXPIRES ON $expireTime"
                        else -> "Activate Now"
                    }

                Text(
                    text = str,
                    fontSize = 16.sp,
                    color = Color.White,
                    textAlign = TextAlign.Center
                )
            }
        }
    }

}


@Preview(showBackground = true, backgroundColor = 0xff000000)
@Composable
private fun MyPagePreview() {
    ProfilePage(
        modifier = Modifier.fillMaxSize(),
        userProfile = UserProfile(
            nickname = "nick",
            id = "12345",
            avatar = ""
        ),
        agents = listOf(),
        onClickAgent = {

        },
    )

}
