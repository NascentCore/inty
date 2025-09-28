package com.ai.inty.chat.ui

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.MutableState
import androidx.compose.runtime.collectAsState
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
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.LifecycleResumeEffect
import com.ai.inty.Constant
import com.ai.inty.R
import com.ai.inty.base.MyModalNavigationDrawer
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.AgentInfo
import com.ai.inty.billing.BillingRepository
import com.ai.inty.chat.ChatViewModel
import com.ai.inty.ui.components.MySettingItem
import com.inty.utils.storage.IntySetting
import com.therouter.TheRouter

/**
 * 聊天设置抽屉组件
 */
@Composable
fun ChatSettingsDrawer(
    chatViewModel: ChatViewModel,
    agentInfo: AgentInfo?,
    drawerState: MutableState<DrawerValue>,
    onPremiumDialogShow: (Boolean) -> Unit,
    onPremiumModeChange: (Boolean) -> Unit,
    onKeepTalkingChange: (Boolean) -> Unit,
) {
    val context = LocalContext.current
    val vipStatus by BillingRepository.vipStatusFlow.collectAsState()

    // Keep talking二状态设置：默认跟随全局设置
    var agentKeepTalking by remember(agentInfo?.id) {
        mutableStateOf(
            agentInfo?.let {
                // 获取角色专用设置，如果不存在则使用全局设置
                IntySetting.getAgentKeepTalking(it.id) ?: IntySetting.isShowKeepTalking()
            } ?: false
        )
    }

    // Premium model二状态设置：默认跟随全局设置，但受VIP状态限制
    var agentPremiumModel by remember(agentInfo?.id, vipStatus.isSubscribed) {
        mutableStateOf(
            if (!vipStatus.isSubscribed) {
                // 如果不是VIP，强制关闭Premium model
                false
            } else {
                agentInfo?.let {
                    // 获取角色专用设置，如果不存在则使用全局设置
                    IntySetting.getAgentPremiumModel(it.id) ?: IntySetting.isShowPremiumModel()
                } ?: false
            }
        )
    }

    LifecycleResumeEffect(chatViewModel) {
        chatViewModel.updateUserInfo()
        onPauseOrDispose { }
    }

    val horizontalPadding = 16

    MyModalNavigationDrawer(
        modifier = Modifier,
        drawerState = drawerState,
        drawerContent = {
            Column(
                modifier = Modifier
                    .width(319.dp)
                    .fillMaxHeight()
                    .background(
                        brush = Brush.verticalGradient(
                            colors = listOf(
                                Color(0xFF322341),
                                Color(0xFF120E24)
                            )
                        )
                    )
            ) {
                Text(
                    text = stringResource(R.string.chat_settings_my_persona_title),
                    modifier = Modifier.padding(top = 58.dp, start = 16.dp),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White
                )

                Spacer(Modifier.height(14.dp))

                Column(
                    modifier = Modifier
                        .padding(horizontal = horizontalPadding.dp)
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
                    val userProfile = chatViewModel.userProfile.collectAsState()
                    MySettingItem(
                        key = "Name",
                        value = userProfile.value.nickname,
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否正式登录（非游客且已登录）
                            if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                TheRouter.build(Constant.ROUTE_SETTING_MY)
                                    .withObject("userProfile", userProfile.value)
                                    .navigation(context)
                            } else {
                                // 未登录或游客时跳转到登录页面
                                TheRouter.build(Constant.ROUTE_LOGIN)
                                    .navigation(context)
                            }
                        }
                    )
                    MySettingItem(
                        key = "Pronoun",
                        value = userProfile.value.pronouns(),
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否正式登录（非游客且已登录）
                            if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                TheRouter.build(Constant.ROUTE_SETTING_MY)
                                    .withObject("userProfile", userProfile.value)
                                    .navigation(context)
                            } else {
                                // 未登录或游客时跳转到登录页面
                                TheRouter.build(Constant.ROUTE_LOGIN)
                                    .navigation(context)
                            }
                        }
                    )
                    MySettingItem(
                        key = "Intro",
                        value = userProfile.value.description ?: "Edit",
                        horizontalPadding = horizontalPadding,
                        onClick = {
                            // 检查是否正式登录（非游客且已登录）
                            if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                TheRouter.build(Constant.ROUTE_SETTING_MY)
                                    .withObject("userProfile", userProfile.value)
                                    .navigation(context)
                            } else {
                                // 未登录或游客时跳转到登录页面
                                TheRouter.build(Constant.ROUTE_LOGIN)
                                    .navigation(context)
                            }
                        }
                    )
                }

                Spacer(Modifier.height(30.dp))

                Text(
                    text = stringResource(R.string.chat_settings_settings_title),
                    modifier = Modifier.padding(start = 16.dp),
                    fontSize = 20.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White
                )

                Spacer(Modifier.height(14.dp))

                Column(
                    modifier = Modifier
                        .padding(horizontal = horizontalPadding.dp)
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
                    agentInfo?.let { agent ->

                        // Premium model设置（二状态，与全局设置同步）
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp)
                                .padding(horizontal = horizontalPadding.dp)
                                .noRippleClickable {
                                    // 检查是否正式登录（非游客且已登录）
                                    if (IntySetting.isLogin() && !IntySetting.isGuestUser()) {
                                        // 检查VIP状态
                                        if (!vipStatus.isSubscribed) {
                                            // 如果不是VIP，显示提示
                                            onPremiumDialogShow(true)
                                        } else {
                                            // 如果是VIP，允许切换
                                            agentPremiumModel = agentPremiumModel.not()
                                            IntySetting.setAgentPremiumModel(
                                                agent.id,
                                                agentPremiumModel
                                            )
                                            onPremiumModeChange(agentPremiumModel)
                                        }
                                    } else {
                                        // 未登录或游客时跳转到登录页面
                                        TheRouter.build(Constant.ROUTE_LOGIN)
                                            .navigation(context)
                                    }
                                },
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = stringResource(R.string.settings_premium_model),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Normal,
                                color = Color.White
                            )
                            Spacer(Modifier.weight(1f))
                            Image(
                                painter = if (agentPremiumModel) painterResource(R.drawable.opened) else painterResource(
                                    R.drawable.closed
                                ),
                                contentDescription = null,
                            )
                        }

                        // 举报入口
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .height(56.dp)
                                .padding(horizontal = horizontalPadding.dp)
                                .noRippleClickable {
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
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                text = stringResource(R.string.report),
                                fontSize = 14.sp,
                                fontWeight = FontWeight.Normal,
                                color = Color.White
                            )
                            Spacer(Modifier.weight(1f))
                            Image(
                                painter = painterResource(R.drawable.icon_next),
                                contentDescription = null,
                            )
                        }
                    }
                }
            }
        }
    ) {
        // 主屏内容
    }
} 
