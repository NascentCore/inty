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
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.HelpOutline
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.ProvideTextStyle
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
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
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.navigation.NavController
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.boost.BoostCalculator
import com.ai.intellimate.boost.BoostConfig
import com.ai.intellimate.boost.BoostLeaderboardActivity
import com.ai.intellimate.xb.navigation.Routes
import kotlinx.coroutines.launch

@Composable
fun BoostStatusChip(
    navController: NavController,
    modifier: Modifier = Modifier,
    availablePoints: Int,
    onClick: (() -> Unit)? = null,
    content: @Composable () -> Unit = { Text("$availablePoints ${stringResource(R.string.boost_points_label)}")}
) {
    val context = LocalContext.current
    val canBoost = availablePoints >= BoostConfig.BOOST_STEP_POINTS
    var showHelpSheet by remember { mutableStateOf(false) }

    val handleClick: () -> Unit = {
        if (onClick != null) {
            onClick()
        } else {
            showHelpSheet = true
        }
    }

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
                .noRippleClickable(enabled = true, onClick = handleClick),
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.Center,
    ) {
        Icon(
            painter = painterResource(R.drawable.rocket_launch_24px),
            contentDescription = null,
            tint = Color.White,
            modifier = Modifier.size(20.dp),
        )
        Spacer(Modifier.size(12.dp))

        ProvideTextStyle(
            value = TextStyle(
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            ),
            content = content
        )
    }

    if (showHelpSheet) {
        BoostPointsHelpSheet(
            availablePoints = availablePoints,
            onDismiss = { showHelpSheet = false },
            onOpenLeaderboard = {
                showHelpSheet = false
                navController.navigate(Routes.BoostLeaderboard)
//                BoostLeaderboardActivity.launch(context)
            },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BoostSheet(
    navController: NavController,
    agentInfo: AgentInfo,
    availablePoints: Int,
    onBoostConfirmed: (Int) -> Unit,
    onDismiss: () -> Unit,
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    var showHelpSheet by remember { mutableStateOf(false) }
    var desiredPoints by
        remember(availablePoints) {
            mutableIntStateOf(
                BoostCalculator.normalizeBoostAmount(BoostConfig.BOOST_STEP_POINTS, availablePoints)
            )
        }

    LaunchedEffect(availablePoints) {
        desiredPoints = 0
        if (availablePoints >= BoostConfig.BOOST_STEP_POINTS) {
            desiredPoints =
                BoostCalculator.normalizeBoostAmount(
                    0.coerceAtLeast(BoostConfig.BOOST_STEP_POINTS),
                    availablePoints,
                )
        }
    }

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = Color(0xFF0F0F11),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            BoostSheetHeader(agentInfo = agentInfo)

            BoostStepper(
                desiredPoints = desiredPoints,
                availablePoints = availablePoints,
                onIncrease = {
                    desiredPoints =
                        (desiredPoints + BoostConfig.BOOST_STEP_POINTS).coerceAtMost(
                            availablePoints
                        )
                },
                onDecrease = {
                    desiredPoints =
                        (desiredPoints - BoostConfig.BOOST_STEP_POINTS).coerceAtLeast(
                            BoostConfig.BOOST_STEP_POINTS
                        )
                },
            )
            Text(
                text = stringResource(R.string.my_boost_points, availablePoints),
                color = Color.White,
                fontSize = 12.sp,
                modifier = Modifier.align(Alignment.CenterHorizontally)
            )
            if (availablePoints < BoostConfig.BOOST_STEP_POINTS) {
                Text(
                    text =
                        stringResource(
                            R.string.boost_sheet_not_enough_points,
                            BoostConfig.BOOST_STEP_POINTS,
                        ),
                    color = Color.White.copy(alpha = 0.7f),
                    fontSize = 12.sp,
                )
                IconButton(
                    onClick = { showHelpSheet = true },
                    modifier = Modifier.align(Alignment.CenterHorizontally)
                ) {
                    Icon(
                        imageVector = Icons.AutoMirrored.Outlined.HelpOutline,
                        contentDescription = "help",
                        tint = Color.White
                    )
                }
            }

            Button(
                onClick = {
                    scope.launch {
                        sheetState.hide()
                        onBoostConfirmed(desiredPoints)
                    }
                },
                enabled =
                    desiredPoints >= BoostConfig.BOOST_STEP_POINTS &&
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

            TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) {
                Text(text = stringResource(R.string.boost_sheet_cancel), color = Color.White)
            }
        }
    }

    if (showHelpSheet) {
        BoostPointsHelpSheet(
            availablePoints = availablePoints,
            onDismiss = { showHelpSheet = false },
            onOpenLeaderboard = {
                showHelpSheet = false
                navController.navigate(Routes.BoostLeaderboard)
//                BoostLeaderboardActivity.launch(context)
            },
        )
    }
}

@Composable
private fun BoostSheetHeader(agentInfo: AgentInfo) {
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(12.dp),
    ) {
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
            Text(
                text = stringResource(R.string.boost_sheet_title),
                color = Color.White.copy(alpha = 0.7f),
                fontSize = 12.sp,
            )
            Text(
                text = agentInfo.name,
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
            )
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
        IconButton(onClick = onDecrease, enabled = desiredPoints > BoostConfig.BOOST_STEP_POINTS) {
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
                text =
                    stringResource(R.string.boost_points_step_hint, BoostConfig.BOOST_STEP_POINTS),
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

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun BoostPointsHelpSheet(
    availablePoints: Int,
    onDismiss: () -> Unit,
    onOpenLeaderboard: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val target = BoostConfig.BOOST_STEP_POINTS
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = Color(0xFF0F0F11),
    ) {
        Column(
            modifier = Modifier.fillMaxWidth().padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Icon(
                imageVector = Icons.AutoMirrored.Outlined.HelpOutline,
                contentDescription = "help",
                tint = Color.White,
                modifier = Modifier
                    .align(Alignment.CenterHorizontally)
                    .size(32.dp)
            )
            Text(
                text = stringResource(R.string.boost_points_help_title),
                color = Color.White,
                fontSize = 18.sp,
                fontWeight = FontWeight.SemiBold,
            )
            Text(
                text = stringResource(R.string.boost_points_help_subtitle),
                color = Color.White.copy(alpha = 0.75f),
                fontSize = 13.sp,
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = stringResource(R.string.boost_points_help_progress, availablePoints, target),
                color = Color.White,
                fontSize = 16.sp,
                fontWeight = FontWeight.Medium,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = stringResource(R.string.boost_points_help_how_to_earn_title),
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
            )

            Text(
                text = stringResource(R.string.boost_points_help_how_to_earn_body),
                color = Color.White.copy(alpha = 0.75f),
                fontSize = 13.sp,
            )
            TextButton(onClick = onDismiss, modifier = Modifier.fillMaxWidth()) {
                Text(text = stringResource(R.string.boost_points_help_close), color = Color.White)
            }
        }
    }
}

@Composable
private fun CharacterEnergyPointsCard(energyPoints: Int, onOpenLeaderboard: () -> Unit) {
    Column(
        modifier =
            Modifier.fillMaxWidth()
                .clip(RoundedCornerShape(16.dp))
                .background(Color(0xFF1C1D21))
                .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        Text(
            text = stringResource(R.string.boost_character_energy_points, energyPoints),
            color = Color.White,
            fontSize = 14.sp,
            fontWeight = FontWeight.Medium,
        )
        Text(
            text = stringResource(R.string.boost_character_energy_points_hint),
            color = Color.White.copy(alpha = 0.7f),
            fontSize = 12.sp,
        )
        TextButton(onClick = onOpenLeaderboard, modifier = Modifier.fillMaxWidth()) {
            Text(
                text = stringResource(R.string.boost_points_help_cta_leaderboard),
                color = Color.White,
            )
        }
    }
}
