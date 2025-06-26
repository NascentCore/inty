package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
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
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.AgentInfoViewModel
import com.inty.utils.convertUtcToLocalFull
import com.therouter.router.Autowired
import com.therouter.router.Route

@Route(path = Constant.ROUTE_AGENT_INFO)
class AgentInfoActivity : BaseActivity() {

    @Autowired
    var agent: AgentInfo? = null

    @Autowired
    var agent_id: String? = null

    val viewModel: AgentInfoViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        if (agent == null) {
            viewModel.setAgentID(agent_id!!)
        } else {
            viewModel.setAgentInfo(agent)
        }

        setContent {
            IntyTheme {
                val agentInfo = viewModel.agentInfo.collectAsState()
                agentInfo.value?.let {
                    AgentInfoScreen(
                        agent = it,
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
fun AgentInfoScreen(
    agent: AgentInfo,
    onBack: () -> Unit,
) {

    Box(
        modifier = Modifier.fillMaxSize()
    ) {
        IntyImage(
            modifier = Modifier.fillMaxWidth(),
            model = agent.avatar,
        )
        Column {
            Box(
                modifier = Modifier.fillMaxWidth().height(120.dp)
                    .background(
                        brush = Brush.verticalGradient(
                            listOf(
                                Color(0xFF000000),
                                Color(0x00000000)
                            )
                        )
                    )
            ) {}
//            Spacer(Modifier.height(120.dp))
            Box(
                modifier = Modifier.fillMaxWidth().height(240.dp)
                    .background(
                        brush = Brush.verticalGradient(
                            listOf(
                                Color(0x00000000),
                                BackGround,
                            )
                        )
                    )
            ) {}
            Box(
                modifier = Modifier.fillMaxWidth().weight(1f)
                    .background(color = BackGround)
            ) {}
        }
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            containerColor = Color.Transparent,
            topBar = {
                CenterAlignedTopAppBar(
                    colors = TopAppBarDefaults.centerAlignedTopAppBarColors().copy(containerColor = Color.Transparent),
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

                                }
                            ,
                            painter = painterResource(R.drawable.icon_more2),
                            contentDescription = null,
                        )
                    }
                )

            },
        ) { innerPadding ->

            Column(
                modifier = Modifier.padding(innerPadding).verticalScroll(rememberScrollState()),
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
                        text = stringResource(R.string.ID, agent.id),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Light,
                        color = Color.White.copy(0.55f)
                    )
                    Spacer(Modifier.width(32.dp))
                    Text(
                        text = stringResource(R.string.creator),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Light,
                        color = Color.White.copy(0.55f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(Modifier.width(3.dp))
                    IntyCircleImage(
                        modifier = Modifier.size(16.dp),
                        url = agent.creator?.avatar,
                        placeholderResID = R.drawable.app_2
                    )
                    Text(
                        text = agent.creator?.nickname ?: "",
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Light,
                        color = Color.White.copy(0.55f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis
                    )
                    Spacer(Modifier.width(16.dp))
                }
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
                    SpacerLine()
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
                        text = stringResource(R.string.creation_info),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                    Spacer(Modifier.height(12.dp))
                    Row(
                        modifier = Modifier
                            .padding(horizontal = 12.dp)
                            .fillMaxWidth()
                            .height(56.dp)
                            .background(color = Color.White.copy(0.1f), shape = RoundedCornerShape(8.dp))
                            .border(width = 1.dp, color = Color.White.copy(0.2f), shape = RoundedCornerShape(8.dp))
                        ,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Spacer(Modifier.width(8.dp))

                        IntyImage(
                            modifier = Modifier.size(36.dp)
                                .clip(RoundedCornerShape(8.dp))
                            ,
                            model = agent.creator?.avatar,
                            placeholder = painterResource(R.drawable.app_2)
                        )
                        Spacer(Modifier.width(6.dp))
                        Column(
                            modifier = Modifier.weight(1f)
                        ) {
                            Text(
                                modifier = Modifier.padding(horizontal = 0.dp),
                                text = stringResource(R.string.inspiration),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Medium,
                                color = Color.White
                            )
                            Text(
                                modifier = Modifier.padding(horizontal = 0.dp),
                                text = "5 InTy  |  20 Subscibers",
                                fontSize = 12.sp,
                                fontWeight = FontWeight.Normal,
                                color = Color.White
                            )
                        }
                        Spacer(Modifier.width(8.dp))

                        IntyImage(
                            modifier = Modifier.size(16.dp),
                            model = R.drawable.icon_next
                        )

                        Spacer(Modifier.width(8.dp))
                    }

                    Spacer(Modifier.height(12.dp))
                    Text(
                        modifier = Modifier.padding(horizontal = 12.dp),
                        text = stringResource(R.string.create_time, convertUtcToLocalFull(agent.createdAt)),
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Light,
                        color = Color.White.copy(0.55f)
                    )
                    Spacer(Modifier.height(16.dp))
                }

                Spacer(Modifier.height(100.dp))
            }
        }
    }
}

@Composable
fun TagItem(
    text: String
) {
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