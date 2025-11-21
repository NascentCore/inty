package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.agent.info.AgentInfoActivity
import kotlinx.coroutines.launch

private const val CHAT_TOP_BAR_AVATAR_SIZE = 30
private const val CHAT_TOP_BAR_AVATAR_PADDING = 3
private const val CHAT_TOP_BAR_CORNER_RADIUS = 20
private val CHAT_TOP_BAR_BACKGROUND_COLOR = Color(33, 0, 0, 77)

private const val BACK_BUTTON_SIZE = 24
private const val MORE_BUTTON_SIZE = 20

/** 聊天页面顶部栏组件 */
@Composable
fun ChatTopBar(
    modifier: Modifier,
    agentInfo: AgentInfo,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
    onClickMore: () -> Unit,
    avatarWidth: Dp = 30.dp,
    fontSize: TextUnit = 14.sp,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        // 返回按钮
        if (showBackButton) {
            AsyncImage(
                modifier =
                    Modifier.size(BACK_BUTTON_SIZE.dp).noRippleClickable { onBack?.invoke() },
                model = R.drawable.back,
                contentDescription = null,
            )
            Spacer(modifier = Modifier.width(8.dp))
        }

        Row(
            modifier =
                Modifier.background(
                        color = CHAT_TOP_BAR_BACKGROUND_COLOR,
                        shape = RoundedCornerShape(avatarWidth),
                    )
                    .noRippleClickable {
                        scope.launch {
                            // 如果是已经删除的agent，则不可点击，并提示
                            if (agentInfo.isDeleted) {
                                ToastUtils.showShort(R.string.str_agent_is_deleted)
                            } else {
                                AgentInfoActivity.launch(context, agentInfo)
                            }
                        }
                    },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            AsyncImage(
                modifier =
                    Modifier.padding(CHAT_TOP_BAR_AVATAR_PADDING.dp)
                        .size(avatarWidth)
                        .clip(CircleShape),
                model =
                    ImageRequest.Builder(context)
                        .data(getCdnImageUrl(agentInfo.avatar, width = 64))
                        .build(),
                placeholder = painterResource(R.drawable.img_default_avatar),
                error = painterResource(R.drawable.img_default_avatar),
                contentDescription = null,
                alignment = Alignment.TopCenter,
                contentScale = ContentScale.Crop,
            )

            Spacer(modifier = Modifier.width(6.dp))

            Text(
                text = agentInfo.name,
                fontSize = fontSize,
                fontWeight = FontWeight.Medium,
                color = Color.White,
            )

            Spacer(modifier = Modifier.width(16.dp))
        }

        Spacer(modifier = Modifier.weight(1f))

        Box(
            modifier =
                Modifier.size(48.dp, 32.dp)
                    .background(
                        color = Color.Black.copy(.3f),
                        shape = RoundedCornerShape(topStart = 16.dp, bottomStart = 16.dp),
                    ),
            contentAlignment = Alignment.Center,
        ) {
            AsyncImage(
                modifier = Modifier.size(MORE_BUTTON_SIZE.dp).noRippleClickable { onClickMore() },
                model = R.drawable.icon_more,
                contentDescription = null,
            )
        }
    }
}
