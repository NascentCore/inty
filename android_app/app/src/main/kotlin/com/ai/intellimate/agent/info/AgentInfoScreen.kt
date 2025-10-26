package com.ai.intellimate.agent.info

import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.data.store.IntySetting
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.HeartColor
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
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
import androidx.compose.runtime.getValue
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
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.intellimate.R
import com.ai.intellimate.agent.report.ReportActivity
import com.ai.intellimate.login.LoginActivity
import com.ai.intellimate.ui.components.AgentBackground
import com.ai.intellimate.ui.components.SmartTagsLayout

@OptIn(ExperimentalMaterial3Api::class)
@Composable
internal fun AiAgentInfoScreen(agent: AgentInfo, onBack: () -> Unit) {
    val context = LocalContext.current
    var showBottomSheet by remember { mutableStateOf(false) }
    val bottomSheetState = rememberModalBottomSheetState()

    Box(modifier = Modifier.fillMaxSize()) {
        AgentBackground(
            agentInfo = agent,
            modifier = Modifier.fillMaxSize(),
            showGradients = false, // 角色主页不需要渐变遮罩
        )

        Scaffold(
            modifier = Modifier.fillMaxSize(),
            containerColor = Color.Transparent,
            topBar = {
                CenterAlignedTopAppBar(
                    colors =
                        TopAppBarDefaults.centerAlignedTopAppBarColors()
                            .copy(containerColor = Color.Transparent),
                    title = {},
                    navigationIcon = {
                        Image(
                            modifier =
                                Modifier.padding(horizontal = 12.dp).noRippleClickable { onBack() },
                            painter = painterResource(R.drawable.back),
                            contentDescription = null,
                        )
                    },
                    actions = {
                        Image(
                            modifier =
                                Modifier.padding(horizontal = 12.dp).noRippleClickable {
                                    showBottomSheet = true
                                },
                            painter = painterResource(R.drawable.icon_more2),
                            contentDescription = null,
                        )
                    },
                )
            },
        ) { innerPadding ->
            Column {
                // 顶部渐变遮罩
                Box(
                    modifier =
                        Modifier.fillMaxWidth()
                            .height(160.dp)
                            .background(
                                brush =
                                    Brush.verticalGradient(
                                        listOf(Color(0xFF000000), Color(0x00000000))
                                    )
                            )
                )
                Box(modifier = Modifier.fillMaxWidth().weight(1f))
                Box(
                    modifier =
                        Modifier.fillMaxWidth()
                            .background(
                                brush =
                                    Brush.verticalGradient(
                                        listOf(
                                            Color(0x00000000),
                                            HeartColor.primaryColor.copy(.3f),
                                            HeartColor.primaryColor.copy(.7f),
                                            HeartColor.primaryColor.copy(.9f),
                                            HeartColor.primaryColor,
                                            HeartColor.primaryColor,
                                        ),
                                        endY = 900f,
                                    )
                            )
                ) {
                    Column(
                        modifier =
                            Modifier.padding(innerPadding).verticalScroll(rememberScrollState())
                    ) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    modifier = Modifier.padding(start = 16.dp),
                                    text = agent.name,
                                    fontSize = 20.sp,
                                    fontWeight = FontWeight.SemiBold,
                                    color = Color.White,
                                )
                                Spacer(Modifier.height(5.dp))
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Spacer(Modifier.width(16.dp))
                                    Text(
                                        modifier = Modifier.fillMaxWidth(),
                                        text = stringResource(R.string.ID, agent.id),
                                        fontSize = 12.sp,
                                        fontWeight = FontWeight.Light,
                                        color = Color.White.copy(0.55f),
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                }
                            }

                            Spacer(Modifier.width(16.dp))
                        }

                        Spacer(Modifier.height(24.dp))

                        Column(
                            modifier =
                                Modifier.padding(horizontal = 16.dp)
                                    .fillMaxWidth()
                                    .border(
                                        brush =
                                            Brush.linearGradient(
                                                colors =
                                                    listOf(
                                                        Color.Transparent,
                                                        Color.White.copy(0.2f),
                                                        Color.Transparent,
                                                    )
                                            ),
                                        width = 1.dp,
                                        shape = RoundedCornerShape(8.dp),
                                    )
                                    .background(
                                        color = Color(0x3378599A),
                                        shape = RoundedCornerShape(8.dp),
                                    )
                        ) {
                            Spacer(Modifier.height(16.dp))
                            Text(
                                modifier = Modifier.padding(horizontal = 12.dp),
                                text = stringResource(R.string.introduction),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color.White,
                            )
                            Spacer(Modifier.height(12.dp))
                            Column {
                                // 使用智能 Tags 布局
                                val gender =
                                    runCatching {
                                            val tmpGender = agent.gender.lowercase()
                                            tmpGender.replaceFirst(
                                                tmpGender.first(),
                                                tmpGender.first().uppercase().first(),
                                            )
                                        }
                                        .getOrNull() ?: ""

                                val agentTags =
                                    mutableListOf(
                                        // FEMALE/MALE转化为Female/Male
                                        stringResource(R.string.gender_tag_format, gender)
                                    )
                                // 取10个即可，避免太多，因为设计也只需要显示一行
                                agent.tags?.take(10)?.forEach { tag ->
                                    tag?.let { agentTags.add(tag) }
                                }
                                SmartTagsLayout(
                                    tags = agentTags,
                                    modifier = Modifier.padding(horizontal = 12.dp),
                                    maxLines = 1,
                                )
                                Spacer(Modifier.height(8.dp))
                                Text(
                                    modifier = Modifier.padding(horizontal = 12.dp),
                                    text = agent.intro,
                                    fontSize = 14.sp,
                                    fontWeight = FontWeight.Light,
                                    color = Color.White,
                                    maxLines = 3,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }

                            Spacer(Modifier.height(12.dp))
                            AgentSpacerLine()
                            Spacer(Modifier.height(10.dp))
                            Text(
                                modifier = Modifier.padding(horizontal = 12.dp),
                                text = stringResource(R.string.opening),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.SemiBold,
                                color = Color.White,
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

                        Spacer(Modifier.height(60.dp))
                    }
                }
            }
        }
    }

    // 底部菜单
    if (showBottomSheet) {
        ModalBottomSheet(
            onDismissRequest = { showBottomSheet = false },
            sheetState = bottomSheetState,
            containerColor = HeartColor.primaryColor,
            contentColor = Color.White,
        ) {
            BottomSheetContent(
                onReportClick = {
                    showBottomSheet = false
                    // 检查是否正式登录（非游客且已登录）
                    if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                        ReportActivity.Companion.launch(context, agent.id, "AGENT")
                    } else {
                        // 未登录或游客时跳转到登录页面
                        LoginActivity.launch(context)
                    }
                },
                onCancelClick = { showBottomSheet = false },
            )
        }
    }
}

@Composable
private fun AgentSpacerLine() {
    Spacer(Modifier.height(4.dp))
    Box(
        modifier =
            Modifier.fillMaxWidth()
                .height(1.dp)
                .background(
                    brush =
                        Brush.horizontalGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        )
                )
    ) {}
    Spacer(Modifier.height(4.dp))
}

@Composable
private fun BottomSheetContent(onReportClick: () -> Unit, onCancelClick: () -> Unit) {
    Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 24.dp)) {
        // Report按钮
        Button(
            onClick = onReportClick,
            modifier = Modifier.fillMaxWidth().height(60.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0x3378599A)),
            shape = RoundedCornerShape(16.dp),
        ) {
            Text(
                text = stringResource(R.string.str_report),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Normal,
            )
        }

        Spacer(modifier = Modifier.height(20.dp))

        // Cancel按钮
        Button(
            onClick = onCancelClick,
            modifier = Modifier.fillMaxWidth().height(60.dp),
            colors = ButtonDefaults.buttonColors(containerColor = Color(0x3378599A)),
            shape = RoundedCornerShape(16.dp),
        ) {
            Text(
                text = stringResource(R.string.cancel_button),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.Normal,
            )
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Preview
@Composable
private fun PreviewAgentInfoScreen() {
    val agent =
        AgentInfo(
            avatar = "",
            background = "",
            category = "category",
            gender = "Female",
            readableId = "readableID",
            isFollowed = true,
            name = "小甜甜",
            opening =
                "青青河边草，又有到海角，野火烧不尽，天涯也不到，啦啦啦啦啦，啦啦啦啦，啦啦啦啦，啦啦啦啦啦啦，轻轻河边草，又有到海角，野火烧不尽，春风吹不到。哈哈哈哈。",
            intro = "自我介绍，这是一个，什么可以说的呢，不知道，小甜甜就是小甜甜",
            prompt = "性感，时尚，火辣，大方",
        )

    AiAgentInfoScreen(agent) {}
}
