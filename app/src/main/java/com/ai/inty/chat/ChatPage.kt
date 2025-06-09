package com.ai.inty.chat

import androidx.compose.foundation.background
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextField
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.R
import com.ai.inty.base.IntyCircleImage
import com.ai.inty.base.IntyImage
import com.ai.inty.base.IntySmallTextField
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.beans.MsgInfo
import com.ai.inty.home.BottomBar
import com.ai.inty.viewmodels.ChatViewModel
import com.inty.utils.log.EasyLog
import okhttp3.internal.wait

@Composable
fun ChatPage(
    modifier: Modifier,
    chatViewModel: ChatViewModel,

) {
    val agentInfo = chatViewModel.agentInfo.collectAsState().value

    Box(
        modifier = modifier
    ) {
        IntyImage(
            modifier = Modifier.fillMaxSize(),
            model = agentInfo?.avatar,

        )
        val colors = listOf(
            Color(0xFF000000),
            Color(0x00000000)
        )
        Box(modifier = Modifier
            .fillMaxWidth()
            .height(120.dp)
            .background(
                brush = Brush.verticalGradient(colors),
            )
        ) {

        }

        val bottomColors = listOf(
            Color(0x001C1523),
            Color(0xFF1C1523)
        )
        Box(modifier = Modifier
            .fillMaxWidth()
            .height(300.dp)
            .background(
                brush = Brush.verticalGradient(bottomColors),
            )
            .align(Alignment.BottomCenter)
        ) {

        }

        Scaffold(
            modifier = Modifier.fillMaxSize().background(Color.Transparent),
            containerColor = Color.Transparent,
            topBar = {
            },

        ) { innerPadding ->
            Column(
                modifier = Modifier.padding(innerPadding)
            ) {
                if (agentInfo != null) {
                    TopBar(
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(36.dp)
                            .padding(horizontal = 18.dp, vertical = 0.dp),
                        agentInfo = agentInfo
                    )
                }

                Spacer(Modifier.height(100.dp))

                LazyColumn(
                    modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
                    reverseLayout = true,
                ) {
                    val msgs = chatViewModel.msgs
                    EasyLog.log("msgs count = ${msgs.size}")
                    item {
                        Spacer(
                            modifier = Modifier
                                .height(16.dp)
                                .fillMaxWidth()

                        )
                    }
                    itemsIndexed(msgs) { index, item ->
                        ChatItem(item)
                        Spacer(
                            modifier = Modifier
                                .height(16.dp)
                                .fillMaxWidth()

                        )
                    }
                }

                Row(
                    modifier = Modifier
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                        .fillMaxWidth().height(64.dp)
                        .background(Color(0x9937303D), RoundedCornerShape(24.dp))
                    ,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    val inputData = chatViewModel.inputData.collectAsState()
                    IntySmallTextField(
                        modifier = Modifier.weight(1f),
                        value = inputData.value,
                        onValueChange = {
                            chatViewModel.inputData.value = it
                        },
                        keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                        keyboardActions = KeyboardActions(
                            onSend = {
                                chatViewModel.sendMsg()
                            }
                        )
                    )

                    if (inputData.value.isNotEmpty()) {
                        IntyImage(
                            modifier = Modifier.padding(16.dp, 0.dp).size(24.dp).noRippleClickable {
                                chatViewModel.sendMsg()
                            },
                            model = R.drawable.btn_send
                        )
                    } else {
                        IntyImage(
                            modifier = Modifier.padding(16.dp, 0.dp).size(24.dp).noRippleClickable {

                            },
                            model = R.drawable.btn_add2
                        )
                    }
                }

            }
        }
    }
}

@Composable
fun ChatItem(
    item: MsgInfo
) {
    when (item.role) {
        "assistant" -> {
            ChatItemAI(item)
        }
        "user" -> {
            ChatItemUser(item)
        }
        else -> {
            EasyLog.log("unknown role: $item")
        }
    }
}

@Composable
fun ChatItemAI(
    item: MsgInfo
) {
    Row {
        Box(
            modifier = Modifier
                .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(12.dp))
                .padding(12.dp, 13.dp)
                .widthIn(1.dp, 300.dp)
        ) {
            Text(
                text = item.content,
                fontWeight = FontWeight.Normal,
                fontSize = 14.sp,
                color = Color.White.copy(0.55f)
            )
        }
        Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
    }

}


@Composable
fun ChatItemUser(
    item: MsgInfo
) {
    Row {
        Spacer(modifier = Modifier.widthIn(80.dp).weight(1f))
        Box(
            modifier = Modifier
                .background(Color.White.copy(alpha = 0.6f), RoundedCornerShape(12.dp))
                .padding(12.dp, 13.dp)
                .widthIn(1.dp, 300.dp)
        ) {
            Text(
                text = item.content,
                fontWeight = FontWeight.Normal,
                fontSize = 14.sp,
                color = Color(0xff090909)
            )
        }
    }

}


@Composable
fun TopBar(
    modifier: Modifier,
    agentInfo: AgentInfo,
) {
    Row(
        modifier = modifier,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            modifier = Modifier.background(color = Color(33, 0, 0, 77), shape = RoundedCornerShape(10.dp)),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IntyCircleImage(
                modifier = Modifier.padding(2.dp).size(36.dp),
                url = agentInfo.avatar,
                placeholderResID = R.drawable.ic_launcher_foreground
            )

            Spacer(modifier = Modifier.width(6.dp))

            Text(
                text = agentInfo.name,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
                color = Color.White
            )

            Spacer(modifier = Modifier.width(6.dp))

            IntyImage(
                modifier = Modifier.size(20.dp),
                model = R.drawable.btn_add
            )


            Spacer(modifier = Modifier.width(8.dp))
        }

        Spacer(modifier = Modifier.weight(1f))

        IntyImage(
            modifier = Modifier.size(20.dp),
            model = R.drawable.icon_more
        )
    }

}
