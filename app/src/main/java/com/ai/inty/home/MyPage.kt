package com.ai.inty.home

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.grid.rememberLazyGridState
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.snapshotFlow
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.base.AntiClick
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.UserProfile
import com.ai.inty.utils.AuthClickable
import com.therouter.TheRouter


@Composable
fun MyPage(
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
    var lastClickTime by remember { mutableLongStateOf(0L) }
    Box(
        modifier = modifier
    ) {
        IntyImage(
            modifier = Modifier.align(Alignment.TopEnd),
            model = R.drawable.notify_header_bg
        )
        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent
        ) { innerPadding ->

            Column {
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
                            placeholderResID = R.drawable.app_2
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

                Spacer(Modifier.height(16.dp))

                Text(
                    modifier = Modifier.padding(horizontal = 16.dp),
                    text = userProfile.description ?: "Share a fun fact about yourself",
                    color = Color.White,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(Modifier.height(24.dp))

                Row(
                    modifier = Modifier.padding(horizontal = 16.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            text = "1232",
                            color = Color.White,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = "Connectors",
                            color = Color.White,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Normal,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }

                    Spacer(Modifier.width(24.dp))
                    Column(
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            text = "8.4K",
                            color = Color.White,
                            fontSize = 16.sp,
                            fontWeight = FontWeight.SemiBold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                        Text(
                            text = "Followers",
                            color = Color.White,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.Normal,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis
                        )
                    }

                    Spacer(Modifier.weight(1f))

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

                Text(
                    modifier = Modifier.padding(horizontal = 16.dp),
                    text = stringResource(R.string.app_name),
                    color = Color.White,
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                if (agents.isEmpty()) {
                    Spacer(Modifier.height(48.dp))

                    IntyImage(
                        modifier = Modifier.align(Alignment.CenterHorizontally),
                        model = R.drawable.group2085655908
                    )

                    Spacer(Modifier.height(16.dp))

                    Text(
                        modifier = Modifier.padding(horizontal = 16.dp).align(Alignment.CenterHorizontally),
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
                                    agents.isNotEmpty()) {
                                    onLoadMore()
                                }
                            }
                    }

                    LazyVerticalGrid(
                        state = listState,
                        modifier = Modifier.padding(start = 16.dp, end = 16.dp, bottom = 100.dp),
                        columns = GridCells.Fixed(2),
                        horizontalArrangement = Arrangement.spacedBy(13.dp),
                        verticalArrangement = Arrangement.spacedBy(16.dp)
                    ) {
                        items(agents) { agent ->
                            MyAgentCard(
                                modifier = Modifier.noRippleClickable {
                                    onClickAgent(agent)
                                },
                                agentInfo = agent,
                                onEditAgent = onEditAgent,
                                onDeleteAgent = onDeleteAgent
                            )
                        }
                        
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
fun MyAgentCard(
    modifier: Modifier,
    agentInfo: AgentInfo,
    onEditAgent: ((AgentInfo) -> Unit)? = null,
    onDeleteAgent: ((AgentInfo) -> Unit)? = null
) {
    var showMenu by remember { mutableStateOf(false) }
    var showDeleteDialog by remember { mutableStateOf(false) }
    var lastClickTime by remember { mutableLongStateOf(0L) }
    
    Box(
        modifier = modifier.size(165.dp, 220.dp)
    ) {
        IntyImage(
            modifier = Modifier.fillMaxSize(),
            model = agentInfo.avatar,
            placeholder = painterResource(R.drawable.app_2),
            error = painterResource(R.drawable.app_2),
        )
        
        Text(
            modifier = Modifier.align(Alignment.BottomStart).padding(12.dp),
            text = agentInfo.name,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
        
        // 右下角的菜单按钮
        if (onEditAgent != null || onDeleteAgent != null) {
            Box(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(8.dp)
            ) {
                IconButton(
                    onClick = {
                        val currentTime = System.currentTimeMillis()
                        if (AntiClick.isValidClick(lastClickTime)) {
                            lastClickTime = currentTime
                            showMenu = true
                        }
                    },
                    modifier = Modifier
                        .size(24.dp)
                        .background(
                            Color.Black.copy(alpha = 0.5f),
                            RoundedCornerShape(12.dp)
                        )
                ) {
                    IntyImage(
                        modifier = Modifier.size(16.dp),
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
                                    text = "Edit",
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
                                    text = "Delete",
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
                        text = "Delete Character",
                        color = Color.White,
                        fontSize = 18.sp,
                        fontWeight = FontWeight.SemiBold
                    )
                },
                text = {
                    Text(
                        text = "Are you sure you want to delete \"${agentInfo.name}\"? This action cannot be undone.",
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
                            text = "Delete",
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
                            text = "Cancel",
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


@Preview(showBackground = true, backgroundColor = 0xff000000)
@Composable
fun MyPagePreview() {
    MyPage(
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
