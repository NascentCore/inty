package com.ai.intellimate.ui.components

import ai.sxwl.android.design.noRippleClickable
import ai.sxwl.android.design.theme.IntelliMateTheme
import ai.sxwl.android.design.theme.brushes
import ai.sxwl.android.firebase.FirebaseManager
import ai.sxwl.android.firebase.logEvent
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.paint
import androidx.compose.ui.graphics.BlendMode
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.ColorFilter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.dimensionResource
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.ai.intellimate.R
import com.ai.intellimate.ui.UiConfigs

/**
 * 评分弹窗（RankDialog）
 *
 * 使用场景：在用户与 iMate 聊天一段时间后，用于收集用户对聊天体验的 1～5 星评分。 预期视觉效果：圆角弹窗、虚化背景，顶部标题与副标题，中间为可点击的五星组件与可选的角色图，
 * 底部为主操作「Submit」与次要「Cancel」。
 *
 * 可配置项：
 * - [characterImageRes] 弹窗中央展示的 iMate 形象图资源 ID，为 0 时不显示图片
 * - [defaultRating] 初始选中的星级（0 表示未选择，1～5 为星级），默认 0；为 0 时 Submit 不可点击
 * - [onCancel] 点击 Cancel 或关闭时回调
 * - [onSubmit] 点击 Submit 时回调，参数为当前选中的星级（1～5）
 */
@Composable
fun RankDialog(
    onCancel: () -> Unit,
    onSubmit: (rating: Int) -> Unit,
    characterImageRes: Int = 0,
    defaultRating: Int = 0,
) {
    val starSize = dimensionResource(R.dimen.rank_dialog_star_size)
    val starSpacing = dimensionResource(R.dimen.rank_dialog_star_spacing)
    val characterImageHeight = dimensionResource(R.dimen.rank_dialog_character_image_height)
    val titleSubtitleSpacing = dimensionResource(R.dimen.rank_dialog_title_subtitle_spacing)
    val subtitleStarsSpacing = dimensionResource(R.dimen.rank_dialog_subtitle_stars_spacing)
    val starsImageSpacing = dimensionResource(R.dimen.rank_dialog_stars_image_spacing)
    val imageButtonsSpacing = dimensionResource(R.dimen.rank_dialog_image_buttons_spacing)
    val buttonSpacing = dimensionResource(R.dimen.rank_dialog_button_spacing)

    var selectedRating by remember { mutableIntStateOf(defaultRating.coerceIn(0, 5)) }

    LaunchedEffect(Unit) { FirebaseManager.Events.RANK_DIALOG_SHOW.logEvent() }

    Dialog(
        onDismissRequest = onCancel,
        properties =
            DialogProperties(
                dismissOnBackPress = true,
                dismissOnClickOutside = false,
                usePlatformDefaultWidth = true,
            ),
    ) {
        Box(
            modifier =
                Modifier.clip(MaterialTheme.shapes.extraLarge)
                    .border(
                        width = 1.dp,
                        color = Color.White,
                        shape = MaterialTheme.shapes.extraLarge,
                    )
                    .paint(
                        painter = painterResource(R.drawable.bg_rank_dialog),
                        contentScale = ContentScale.Crop,
                        colorFilter =
                            ColorFilter.tint(
                                Color.Black.copy(alpha = 0.6f),
                                blendMode = BlendMode.Multiply,
                            ),
                    )
        ) {
            Column(
                modifier =
                    Modifier.fillMaxWidth()
                        .padding(
                            horizontal = UiConfigs.Padding.DialogContentHorizontal,
                            vertical = UiConfigs.Padding.DialogContentVertical,
                        ),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Spacer(Modifier.height(32.dp))

                Text(
                    text = stringResource(R.string.rank_dialog_title),
                    style = MaterialTheme.typography.titleLarge,
                    color = MaterialTheme.colorScheme.onSurface,
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(titleSubtitleSpacing))
                Text(
                    text = stringResource(R.string.rank_dialog_subtitle),
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurface,
                    textAlign = TextAlign.Center,
                )
                Spacer(Modifier.height(subtitleStarsSpacing))

                Row(
                    horizontalArrangement = Arrangement.spacedBy(starSpacing),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    val star = painterResource(R.drawable.ic_star_uf)
                    val starFilled = painterResource(R.drawable.ic_star_f)

                    (1..5).forEach { index ->
                        val filled = index <= selectedRating
                        Image(
                            painter = if (filled) starFilled else star,
                            contentDescription = null,
                            modifier =
                                Modifier.size(starSize).noRippleClickable { selectedRating = index },
                        )
                    }
                }

                if (characterImageRes != 0) {
                    Spacer(Modifier.height(starsImageSpacing))
                    Image(
                        painter = painterResource(characterImageRes),
                        contentDescription = null,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.height(characterImageHeight),
                    )
                }

                Spacer(Modifier.height(imageButtonsSpacing))
                Box(
                    contentAlignment = Alignment.Center,
                    modifier =
                        Modifier.fillMaxWidth()
                            .height(48.dp)
                            .clip(RoundedCornerShape(100))
                            .alpha(if (selectedRating > 0) 1f else .6f)
                            .background(brush = MaterialTheme.brushes.vertical.gradientBrush1)
                            .clickable(enabled = selectedRating > 0) {
                                FirebaseManager.Events.RANK_DIALOG_SUBMIT_CLICK.logEvent(
                                    "rating" to selectedRating
                                )
                                onSubmit(selectedRating)
                            },
                ) {
                    Text(
                        text = stringResource(R.string.submit_button),
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                }
                Spacer(Modifier.height(dimensionResource(R.dimen.padding_small)))
                Box(
                    contentAlignment = Alignment.Center,
                    modifier =
                        Modifier.fillMaxWidth()
                            .height(48.dp)
                            .clip(RoundedCornerShape(100))
                            .background(brush = MaterialTheme.brushes.vertical.gradientBrush3)
                            .border(
                                width = 1.dp,
                                color = Color.White.copy(.2f),
                                shape = RoundedCornerShape(100),
                            )
                            .clickable {
                                FirebaseManager.Events.RANK_DIALOG_CANCEL_CLICK.logEvent()
                                onCancel()
                            },
                ) {
                    Text(
                        text = stringResource(R.string.cancel),
                        style = MaterialTheme.typography.bodyLarge,
                        color = MaterialTheme.colorScheme.onPrimary,
                    )
                }
            }
        }
    }
}

@Preview
@Composable
private fun PreviewRankDialog() {
    IntelliMateTheme { RankDialog(onCancel = {}, onSubmit = {}, characterImageRes = 0) }
}
