package com.ai.inty

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.ai.inty.base.IntyImage
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.SysMsgItem
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.SysMsgsActivityViewModel
import com.inty.utils.convertUtcToLocal
import com.therouter.router.Route


enum class SysMsgTemplateId(val id: Int) {
    TEXT_WITH_LINK(1),
    IMAGE_WITH_LINK(2),
    TEXT_ONLY(3),
    IMAGE_ONLY(4),
    IMAGE_TEXT_LINK(5),
}

@Route(path = Constant.ROUTE_SYS_MSGS)
class SysMsgsActivity : ComponentActivity() {

    val viewModel: SysMsgsActivityViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        enableEdgeToEdge()
        setContent {
            IntyTheme {
                val msgs = viewModel.sysMsgs
                SysMsgsScreen(
                    msgs = msgs,
                    onBack = {
                        finish()
                    }
                )
            }
        }


    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SysMsgsScreen(
    msgs: List<SysMsgItem>,
    onBack: () -> Unit = {},
) {
    Box(
        modifier = Modifier.fillMaxSize()
    ) {
        Scaffold(
            modifier = Modifier.fillMaxSize(),
            topBar = {
                CenterAlignedTopAppBar(
                    title = {
                        Text(
                            text = stringResource(R.string.sys_notify_title),
                            color = Color.White,
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 20.sp,
                        )
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

                    }

                )
            }
        ) { innerPadding ->

            LazyColumn(
                modifier = Modifier.padding(innerPadding)
            ) {
                itemsIndexed(msgs) { index, msg ->
                    when(msg.templateId) {
                        SysMsgTemplateId.TEXT_WITH_LINK.id -> {
                            SysMsgItemTextLink(msg)
                        }
                        SysMsgTemplateId.IMAGE_WITH_LINK.id -> {
                            SysMsgItemImageLink(msg)
                        }
                        SysMsgTemplateId.TEXT_ONLY.id -> {
                            SysMsgItemTextLink(msg, false)
                        }
                        SysMsgTemplateId.IMAGE_ONLY.id -> {
                            SysMsgItemImage(msg)
                        }
                        SysMsgTemplateId.IMAGE_TEXT_LINK.id -> {
                            SysMsgItemImageTextLink(msg)
                        }
                    }
                }
            }

        }
    }

}

@Composable
fun SysMsgItemContainer(
    msg: SysMsgItem,
    showClick: Boolean = false,
    content: @Composable ColumnScope.() -> Unit
) {
    val context = LocalContext.current
    Column(
        modifier = Modifier
            .padding(16.dp, 16.dp, 16.dp, 9.dp)
            .noRippleClickable {
                msg.linkUrls.firstOrNull()?.let { onClickUrl(context, it) }
            }
        ,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .background(color = Color(0x3378599A), shape = RoundedCornerShape(12.dp))
                .padding(8.dp, 1.dp)
        ) {
            Text(
                text = convertUtcToLocal(msg.createdAt),
                fontSize = 12.sp,
                color = Color.White.copy(0.55f)
            )
        }
        Spacer(Modifier.height(10.dp))

        Column(
            modifier = Modifier
                .background(
                    color = Color(0x3378599A),
                    shape = RoundedCornerShape(8.dp)
                )
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
            ,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            content()

            if (showClick) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth().height(1.dp)
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(Color.Transparent, Color.White, Color.Transparent)
                            )
                        )
                ) {}

                Row(
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        modifier = Modifier.padding(16.dp, 14.dp),
                        text = "Click to check",
                        fontSize = 14.sp,
                        color = Color.White.copy(0.55f)
                    )

                    Spacer(Modifier.weight(1f))

                    Image(
                        modifier = Modifier
                            .padding(16.dp, 14.dp)
                            .noRippleClickable {

                            },
                        painter = painterResource(R.drawable.icon_next),
                        contentDescription = null,
                    )
                }
            }
        }
    }
}

@Composable
fun SysMsgItemImageTextLink(msg: SysMsgItem) {
    SysMsgItemContainer(
        msg = msg,
        showClick = true,
    ) {
        IntyImage(
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp, 8.dp, 0.dp, 0.dp)),
            model = msg.imageUrls.firstOrNull()
        )
        Text(
            modifier = Modifier.padding(16.dp).fillMaxWidth(),
            text = msg.content,
            fontSize = 14.sp,
            color = Color.White
        )
    }

}

@Composable
fun SysMsgItemImage(msg: SysMsgItem) {
    SysMsgItemContainer(
        msg = msg,
        showClick = false,
    ) {
        IntyImage(
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp)),
            model = msg.imageUrls.firstOrNull()
        )
    }

}

@Composable
fun SysMsgItemImageLink(msg: SysMsgItem) {
    SysMsgItemContainer(
        msg = msg,
        showClick = true,
    ) {
        IntyImage(
            modifier = Modifier.fillMaxWidth().clip(RoundedCornerShape(8.dp, 8.dp, 0.dp, 0.dp)),
            model = msg.imageUrls.firstOrNull()
        )
    }

}

fun onClickUrl(context: Context, url: String) {
    val intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
    context.startActivity(intent)

}

@Composable
fun SysMsgItemTextLink(
    msg: SysMsgItem,
    showClick: Boolean = true,
) {
    SysMsgItemContainer(
        msg = msg,
        showClick = showClick,
    ) {
        Text(
            modifier = Modifier.padding(16.dp).fillMaxWidth(),
            text = msg.content,
            fontSize = 14.sp,
            color = Color.White
        )
    }
}

