package com.ai.inty

import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.compose.setContent
import androidx.activity.viewModels
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
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.view.WindowCompat
import com.ai.inty.base.AntiClick
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.AgentInfoViewModel
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter
import com.therouter.router.Autowired
import com.therouter.router.Route

/**
 * Ai模型的信息介绍页面
 */
@Route(path = Constant.ROUTE_AGENT_INFO)
class AgentInfoActivity : BaseActivity() {

    @Autowired
    var agent: AgentInfo? = null

    @Autowired
    var agent_id: String? = null

    val viewModel: AgentInfoViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // 强制设置状态栏为白色图标 - 多重保险
        setupStatusBar()

        if (agent == null) {
            if (agent_id != null) {
                viewModel.setAgentID(agent_id!!)
            } else {
                // 既没有 agent 对象也没有 agent_id，说明参数传递有问题
                finish()
                return
            }
        } else {
            viewModel.setAgentInfo(agent)
        }

        setContent {
            IntyTheme {
                val agentInfo = viewModel.agentInfo.collectAsState()
                agentInfo.value?.let {
                    AgentInfoScreen(
                        agent = it,
                        viewModel = viewModel,
                        onBack = {
                            finish()
                        }
                    )
                }
            }
        }
    }
}


@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AgentInfoScreen(
    agent: AgentInfo,
    viewModel: AgentInfoViewModel,
    onBack: () -> Unit,
) {
    val context = LocalContext.current
    var showBottomSheet by remember { mutableStateOf(false) }
    val bottomSheetState = rememberModalBottomSheetState()

    Box(
        modifier = Modifier.fillMaxSize()
    ) {
        IntyImage(
            modifier = Modifier.fillMaxWidth(),
            model = agent.avatar,
        )
        Column {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(120.dp)
                    .background(
                        brush = Brush.verticalGradient(
                            listOf(
                                Color(0xFF000000),
                                Color(0x00000000)
                            )
                        )
                    )
            )
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(240.dp)
                    .background(
                        brush = Brush.verticalGradient(
                            listOf(
                                Color(0x00000000),
                                BackGround,
                            )
                        )
                    )
            )
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f)
                    .background(color = BackGround)
            )
        }
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            containerColor = Color.Transparent,
            topBar = {
                CenterAlignedTopAppBar(
                    colors = TopAppBarDefaults.centerAlignedTopAppBarColors()
                        .copy(containerColor = Color.Transparent),
                    title = {
                    },
                    navigationIcon = {
                        Image(
                            modifier = Modifier
                                .padding(horizontal = 12.dp)
                                .noRippleClickable {
                                    onBack()
                                },
                            painter = painterResource(R.drawable.back),
                            contentDescription = null,
                        )

                    },
                    actions = {
                        Image(
                            modifier = Modifier
                                .padding(horizontal = 12.dp)
                                .noRippleClickable {
                                    showBottomSheet = true
                                },
                            painter = painterResource(R.drawable.icon_more2),
                            contentDescription = null,
                        )
                    }
                )

            },
        ) { innerPadding ->

            Column(
                modifier = Modifier
                    .padding(innerPadding)
                    .verticalScroll(rememberScrollState()),
            ) {
                Spacer(Modifier.height(149.dp))
                Text(
                    modifier = Modifier.padding(horizontal = 16.dp),
                    text = agent.name,
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White
                )
                Spacer(Modifier.height(5.dp))
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Spacer(Modifier.width(16.dp))
                    Text(
                        modifier = Modifier.widthIn(0.dp, 100.dp),
                        text = stringResource(
                            R.string.ID,
                            agent.readableId.takeIf { it.isNotEmpty() } ?: agent.id),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Light,
                        color = Color.White.copy(0.55f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )

                }
                Spacer(Modifier.height(24.dp))

                // 统计行
                StatsRow(
                    modifier = Modifier.padding(horizontal = 16.dp),
                    connectorsCount = agent.connectorCount,
                    followersCount = agent.followerCount,
                    isFollowing = agent.isFollowed,
                    onFollowClick = {
                        viewModel.followAgent(agent.id, context)
                    }
                )

                Spacer(Modifier.height(24.dp))
                Text(
                    modifier = Modifier.padding(horizontal = 16.dp),
                    text = stringResource(R.string.info),
                    fontSize = 16.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White
                )
                Spacer(Modifier.height(10.dp))

                Column(
                    modifier = Modifier
                        .padding(horizontal = 16.dp)
                        .fillMaxWidth()
                        .border(
                            brush = Brush.linearGradient(
                                colors = listOf(
                                    Color.Transparent,
                                    Color.White.copy(0.2f),
                                    Color.Transparent
                                )
                            ),
                            width = 1.dp,
                            shape = RoundedCornerShape(8.dp)
                        )
                        .background(
                            color = Color(0x3378599A),
                            shape = RoundedCornerShape(8.dp)
                        )
                ) {
                    Spacer(Modifier.height(16.dp))
                    Text(
                        modifier = Modifier.padding(horizontal = 12.dp),
                        text = stringResource(R.string.introduction),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                    Spacer(Modifier.height(12.dp))
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp)
                    ) {
                        TagItem(text = "#${agent.gender}")
                    }
                    Spacer(Modifier.height(21.dp))
                    AgentSpacerLine()
                    Spacer(Modifier.height(13.dp))
                    Text(
                        modifier = Modifier.padding(horizontal = 12.dp),
                        text = stringResource(R.string.opening),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                    Spacer(Modifier.height(12.dp))
                    Text(
                        modifier = Modifier.padding(horizontal = 12.dp),
                        text = agent.opening,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Light,
                        color = Color.White,
                        maxLines = 3,
                        overflow = TextOverflow.Ellipsis,
                    )

                    Spacer(Modifier.height(16.dp))
                }

                Spacer(Modifier.height(16.dp))

                Spacer(Modifier.height(100.dp))
            }
        }

        // 底部菜单
        if (showBottomSheet) {
            ModalBottomSheet(
                onDismissRequest = { showBottomSheet = false },
                sheetState = bottomSheetState,
                containerColor = BackGround,
                contentColor = Color.White
            ) {
                BottomSheetContent(
                    onReportClick = {
                        showBottomSheet = false
                        // 检查是否正式登录（非游客且已登录）
                        if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                            TheRouter.build(Constant.ROUTE_REPORT)
                                .withString("targetID", agent.id)
                                .withString("targetType", "AGENT")
                                .navigation(context)
                        } else {
                            // 未登录或游客时跳转到登录页面
                            TheRouter.build(Constant.ROUTE_LOGIN)
                                .navigation(context)
                        }
                    },
                    onCancelClick = {
                        showBottomSheet = false
                    }
                )
            }
        }
    }
}

@Composable
private fun TagItem(text: String) {
    Box(
        modifier = Modifier
            .background(color = Color(0xff1C1523), shape = RoundedCornerShape(4.dp))
            .border(
                width = 1.dp,
                brush = Brush.linearGradient(
                    colors = listOf(
                        Color.Transparent,
                        Color.White.copy(0.09f),
                        Color.Transparent
                    )
                ),
                shape = RoundedCornerShape(4.dp)
            )
    ) {
        Text(
            modifier = Modifier.padding(horizontal = 6.dp, vertical = 5.dp),
            text = text,
            fontSize = 12.sp,
            fontWeight = FontWeight.Light,
            color = Color.White.copy(0.55f)
        )
    }
}

@Composable
private fun StatsRow(
    modifier: Modifier = Modifier,
    connectorsCount: Int,
    followersCount: Int,
    isFollowing: Boolean,
    onFollowClick: () -> Unit,
) {
    Row(
        modifier = modifier.fillMaxWidth(),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        // 左侧统计信息
        Row(
            horizontalArrangement = Arrangement.spacedBy(32.dp)
        ) {
            // Connectors
            StatItem(
                count = connectorsCount,
                label = "Connectors"
            )

            // Followers
            StatItem(
                count = followersCount,
                label = "Followers"
            )
        }

        // 右侧关注按钮
        FollowButton(
            isFollowing = isFollowing,
            onClick = onFollowClick
        )
    }
}

@Composable
private fun StatItem(
    count: Int,
    label: String,
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = formatCount(count),
            fontSize = 16.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White
        )
        Text(
            text = label,
            fontSize = 13.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White
        )
    }
}

@Composable
private fun FollowButton(
    isFollowing: Boolean,
    onClick: () -> Unit,
) {
    var lastClickTime by remember { mutableLongStateOf(0L) }

    Button(
        onClick = {
            val currentTime = System.currentTimeMillis()
            if (AntiClick.isValidClick(lastClickTime)) {
                lastClickTime = currentTime
                onClick()
            }
        },
        colors = ButtonDefaults.buttonColors(
            containerColor = if (isFollowing) Color(0x3378599A) else Color.Transparent
        ),
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier
            .height(35.dp)
            .width(105.dp)
            .let {
                if (!isFollowing) {
                    it.background(
                        brush = Brush.horizontalGradient(
                            colors = listOf(
                                Color(0xFFE91E63),
                                Color(0xFFFF9800)
                            )
                        ),
                        shape = RoundedCornerShape(16.dp)
                    )
                } else it
            }
    ) {
        Text(
            text = if (isFollowing) "Following" else "Follow",
            color = Color.White,
            fontSize = 12.sp,
            fontWeight = FontWeight.Medium
        )
    }
}

@Composable
private fun BottomSheetContent(
    onReportClick: () -> Unit,
    onCancelClick: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 20.dp, vertical = 24.dp)
    ) {
        // Report按钮
        Button(
            onClick = onReportClick,
            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0x3378599A)
            ),
            shape = RoundedCornerShape(16.dp)
        ) {
            Text(
                text = "Report",
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Normal
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Cancel按钮
        Button(
            onClick = onCancelClick,
            modifier = Modifier
                .fillMaxWidth()
                .height(60.dp),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color(0x3378599A)
            ),
            shape = RoundedCornerShape(16.dp)
        ) {
            Text(
                text = "Cancel",
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Normal
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun AgentSpacerLine() {
    Spacer(Modifier.height(4.dp))
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .height(1.dp)
            .background(
                brush = Brush.horizontalGradient(
                    colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                )
            )
    ) {}
    Spacer(Modifier.height(4.dp))
}

private fun formatCount(count: Int): String {
    return when {
        count >= 1000000 -> "${count / 1000000}.${(count % 1000000) / 100000}M"
        count >= 1000 -> "${count / 1000}.${(count % 1000) / 100}K"
        else -> count.toString()
    }
}

private fun AgentInfoActivity.setupStatusBar() {
    // 使用现代API设置状态栏颜色
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.LOLLIPOP) {
        window.statusBarColor = android.graphics.Color.parseColor("#1C1523")
        window.addFlags(WindowManager.LayoutParams.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
    }

    // 使用WindowCompat兼容库统一处理状态栏样式
    WindowCompat.setDecorFitsSystemWindows(window, false)
    val windowInsetsController = WindowCompat.getInsetsController(window, window.decorView)
    windowInsetsController.isAppearanceLightStatusBars = false
}