/*
 * CREATED_BY_AGENT
 */
package com.ai.intellimate.boost.ui

import ai.sxwl.android.data.api.getCdnImageUrl
import ai.sxwl.android.data.api.model.AgentInfo
import ai.sxwl.android.design.noRippleClickable
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostCalculator
import com.ai.intellimate.boost.BoostConfig
import kotlinx.coroutines.launch

@Composable
fun BoostStatusChip(
    modifier: Modifier = Modifier,
    availablePoints: Int,
    onClick: () -> Unit,
) {
    val canBoost = availablePoints >= BoostConfig.BOOST_STEP_POINTS
    val gradient =
        Brush.horizontalGradient(
            colors =
                if (canBoost) {
                    listOf(Color(0xFFFF7A18), Color(0xFFAF002D))
                } else {
                    listOf(Color(0xFF444444), Color(0xFF1F1F1F))
                }
        )
    Row(
        modifier =
            modifier
                .clip(RoundedCornerShape(24.dp))
                .background(gradient)
                .border(
                    width = 1.dp,
                    color = Color.White.copy(alpha = 0.08f),
                    shape = RoundedCornerShape(24.dp),
                )
                .padding(horizontal = 16.dp, vertical = 10.dp)
                .noRippleClickable(enabled = canBoost, onClick = onClick),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Icon(
            painter = painterResource(R.drawable.ic_boost_fire),
            contentDescription = null,
            tint = Color.White,
            modifier = Modifier.size(20.dp),
        )
        Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(
                text = stringResource(R.string.boost_points_label),
                color = Color.White.copy(alpha = 0.75f),
                fontSize = 12.sp,
            )
            Text(
                text = stringResource(R.string.boost_points_value, availablePoints),
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
            )
        }
        Text(
            text = stringResource(if (canBoost) R.string.boost_points_action else R.string.boost_points_action_disabled),
            color = if (canBoost) Color.White else Color.White.copy(alpha = 0.4f),
            fontSize = 12.sp,
            modifier = Modifier.padding(start = 8.dp),
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BoostSheet(
    agentInfo: AgentInfo,
    availablePoints: Int,
    hasDailyReward: Boolean,
    onBoostConfirmed: (Int) -> Unit,
    onClaimDailyReward: () -> Unit,
    onDismiss: () -> Unit,
) {
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var desiredPoints by remember(availablePoints) {
        mutableIntStateOf(
            BoostCalculator.normalizeBoostAmount(
                BoostConfig.BOOST_STEP_POINTS,
                availablePoints,
            )
        )
    }

    LaunchedEffect(availablePoints) {
        desiredPoints =
            BoostCalculator.normalizeBoostAmount(
                desiredPoints.coerceAtLeast(BoostConfig.BOOST_STEP_POINTS),
                availablePoints,
            )
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = Color(0xFF0F0F11),
    ) {
        Column(modifier = Modifier.fillMaxWidth().padding(24.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            BoostSheetHeader(agentInfo = agentInfo)

            BoostPointsSummary(availablePoints = availablePoints, desiredPoints = desiredPoints)

            BoostStepper(
                desiredPoints = desiredPoints,
                availablePoints = availablePoints,
                onIncrease = {
                    desiredPoints =
                        (desiredPoints + BoostConfig.BOOST_STEP_POINTS).coerceAtMost(availablePoints)
                },
                onDecrease = {
                    desiredPoints =
                        (desiredPoints - BoostConfig.BOOST_STEP_POINTS)
                            .coerceAtLeast(BoostConfig.BOOST_STEP_POINTS)
                },
            )

            if (availablePoints < BoostConfig.BOOST_STEP_POINTS) {
                Text(
                    text = stringResource(R.string.boost_sheet_not_enough_points),
                    color = Color.White.copy(alpha = 0.7f),
                    fontSize = 12.sp,
                )
            }

            Button(
                onClick = {
                    scope.launch {
                        sheetState.hide()
                        onBoostConfirmed(desiredPoints)
                    }
                },
                enabled = desiredPoints >= BoostConfig.BOOST_STEP_POINTS &&
                    availablePoints >= BoostConfig.BOOST_STEP_POINTS,
                modifier = Modifier.fillMaxWidth(),
                colors =
                    ButtonDefaults.buttonColors(
                        containerColor = Color(0xFFFF7A18),
                        contentColor = Color.White,
                    ),
                contentPadding = PaddingValues(vertical = 12.dp),
            ) {
                Text(text = stringResource(R.string.boost_sheet_confirm))
            }

            TextButton(
                onClick = onDismiss,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = stringResource(R.string.boost_sheet_cancel),
                    color = Color.White,
                )
            }

            if (!hasDailyReward) {
                TextButton(
                    onClick = onClaimDailyReward,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(
                        text = stringResource(R.string.boost_daily_reward_cta),
                        color = Color(0xFFFFB347),
                    )
                }
            }
        }
    }
}

@Composable
private fun BoostSheetHeader(agentInfo: AgentInfo) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        AsyncImage(
            modifier = Modifier.size(52.dp).clip(CircleShape),
            model =
                ImageRequest.Builder(LocalContext.current)
                    .data(getCdnImageUrl(agentInfo.avatar, width = 128))
                    .build(),
            placeholder = painterResource(R.drawable.img_default_avatar),
            error = painterResource(R.drawable.img_default_avatar),
            contentScale = ContentScale.Crop,
            contentDescription = null,
        )
        Column {
            Text(text = stringResource(R.string.boost_sheet_title), color = Color.White.copy(alpha = 0.7f), fontSize = 12.sp)
            Text(text = agentInfo.name, color = Color.White, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun BoostPointsSummary(availablePoints: Int, desiredPoints: Int) {
    Column(
        modifier =
            Modifier.fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFF1C1D21))
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(8.dp),
    ) {
        Text(
            text = stringResource(R.string.boost_points_available, availablePoints),
            color = Color.White,
            fontSize = 16.sp,
            fontWeight = FontWeight.Medium,
        )
        Text(
            text = stringResource(R.string.boost_points_to_invest, desiredPoints),
            color = Color.White.copy(alpha = 0.75f),
            fontSize = 14.sp,
        )
    }
}

@Composable
private fun BoostStepper(
    desiredPoints: Int,
    availablePoints: Int,
    onIncrease: () -> Unit,
    onDecrease: () -> Unit,
) {
    Row(
        modifier =
            Modifier.fillMaxWidth()
                .clip(RoundedCornerShape(12.dp))
                .background(Color(0xFF15151A))
                .padding(horizontal = 12.dp, vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        IconButton(
            onClick = onDecrease,
            enabled = desiredPoints > BoostConfig.BOOST_STEP_POINTS,
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_arrow_down),
                contentDescription = "Decrease",
                tint = Color.White,
            )
        }
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = stringResource(R.string.boost_selected_points, desiredPoints),
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
            )
            Text(
                text = stringResource(R.string.boost_points_step_hint, BoostConfig.BOOST_STEP_POINTS),
                color = Color.White.copy(alpha = 0.6f),
                fontSize = 12.sp,
            )
        }
        IconButton(
            onClick = onIncrease,
            enabled = desiredPoints + BoostConfig.BOOST_STEP_POINTS <= availablePoints,
        ) {
            Icon(
                painter = painterResource(R.drawable.ic_arrow_up),
                contentDescription = "Increase",
                tint = Color.White,
            )
        }
    }
}
