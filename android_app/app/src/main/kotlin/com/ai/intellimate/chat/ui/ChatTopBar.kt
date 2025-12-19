package com.ai.intellimate.chat.ui

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.utils.ToastUtils
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.EnergySavingsLeaf
import androidx.compose.material3.Icon
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
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.TextUnit
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs
import com.ai.intellimate.xb.helper.AgentStore
import com.ai.intellimate.xb.navigation.Routes
import kotlinx.coroutines.launch

/** 聊天页面顶部栏组件 */
@Composable
fun ChatTopBar(
    navController: NavController,
    modifier: Modifier,
    agentInfo: AgentInfo,
    showBackButton: Boolean = false,
    onBack: (() -> Unit)? = null,
    onClickMore: () -> Unit,
    avatarWidth: Dp = UiConfigs.ChatTopBar.AvatarSize,
    fontSize: TextUnit = 14.sp,
    earnedPoints: Int? = null,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()

    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        // 返回按钮
        if (showBackButton) {
            AsyncImage(
                modifier =
                    Modifier.size(UiConfigs.ChatTopBar.BackButtonIconSize).noRippleClickable {
                        onBack?.invoke()
                    },
                model = R.drawable.back,
                contentDescription = null,
            )
            Spacer(modifier = Modifier.width(UiConfigs.ChatTopBar.BackButtonToAvatarSpacing))
        }

        Row(
            modifier =
                Modifier.background(
                        color = UiConfigs.ChatTopBar.BackgroundColor,
                        shape = RoundedCornerShape(UiConfigs.ChatTopBar.CornerRadius),
                    )
                    .noRippleClickable {
                        scope.launch {
                            // 如果是已经删除的agent，则不可点击，并提示
                            if (agentInfo.isDeleted) {
                                ToastUtils.showShort(R.string.str_agent_is_deleted)
                            } else {
                                AgentStore.addAgent(agentInfo)
                                navController.navigate(Routes.agentInfPage(agentInfo.id))
                                //                                AgentInfoActivity.launch(context,
                                // agentInfo)
                            }
                        }
                    },
            verticalAlignment = Alignment.CenterVertically,
        ) {
            AsyncImage(
                modifier =
                    Modifier.padding(UiConfigs.ChatTopBar.AvatarPadding)
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

            Spacer(modifier = Modifier.width(UiConfigs.ChatTopBar.AvatarToContentSpacing))

            val showPoints = earnedPoints != null

            Column(modifier = Modifier.padding(end = UiConfigs.ChatTopBar.ContentRightPadding)) {
                if (showPoints) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Rounded.EnergySavingsLeaf,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(UiConfigs.ChatTopBar.EnergyIconSize),
                        )
                        Spacer(
                            modifier = Modifier.width(UiConfigs.ChatTopBar.EnergyIconToTextSpacing)
                        )
                        Text(
                            text =
                                stringResource(id = R.string.energy_points_counter, earnedPoints),
                            fontSize = UiConfigs.ChatTopBar.EnergyPointsFontSize,
                            color = Color.White.copy(alpha = 0.9f),
                            fontWeight = FontWeight.Medium,
                        )
                    }
                    Spacer(
                        modifier = Modifier.height(UiConfigs.ChatTopBar.EnergyPointsToNameSpacing)
                    )
                }
                Text(
                    text = agentInfo.name,
                    fontSize = fontSize,
                    fontWeight = FontWeight.Medium,
                    color = Color.White,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
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
                modifier =
                    Modifier.size(UiConfigs.ChatTopBar.MoreButtonIconSize).noRippleClickable {
                        onClickMore()
                    },
                model = R.drawable.icon_more,
                contentDescription = null,
            )
        }
    }
}
