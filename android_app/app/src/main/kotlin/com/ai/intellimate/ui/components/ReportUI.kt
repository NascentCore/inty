package com.ai.intellimate.ui.components

import ai.sxwl.android.design.noRippleClickable
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CircularProgressIndicator
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
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.intellimate.R
import com.ai.intellimate.ui.IntySmallTextField2
import com.ai.intellimate.xb.components.MultiLineBasicTextField

/** 举报项组件 */
@Composable
fun ReportItem(text: String, selected: Boolean, onClick: () -> Unit = {}) {
    Row(
        modifier = Modifier.fillMaxWidth().height(48.dp).noRippleClickable { onClick() },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text = text, fontSize = 14.sp, color = Color.White.copy(0.55f))
        Spacer(Modifier.weight(1f))

        Image(
            painter = painterResource(if (selected) R.drawable.checked else R.drawable.check_no),
            contentDescription = null,
        )
    }
}

/** 举报原因容器组件 */
@Composable
fun ReportReasonsContainer(title: String, content: @Composable () -> Unit) {
    Column(
        modifier =
            Modifier.background(color = Color(0x1A78599A), shape = RoundedCornerShape(8.dp))
                .border(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                    width = 1.dp,
                    shape = RoundedCornerShape(8.dp),
                )
                .padding(horizontal = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(16.dp))

        Text(
            text = title,
            modifier = Modifier.fillMaxWidth(),
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
        Spacer(Modifier.height(12.dp))

        content()

        Spacer(Modifier.height(14.dp))
    }
}

/** 举报描述容器组件 */
@Composable
fun ReportDescriptionContainer(
    title: String,
    description: String,
    onDescriptionChange: (String) -> Unit,
    placeholder: String,
    maxLength: Int = 400,
) {
    Column(
        modifier =
            Modifier.fillMaxWidth()
                .background(color = Color(0x1A78599A), shape = RoundedCornerShape(8.dp))
                .border(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                    width = 1.dp,
                    shape = RoundedCornerShape(8.dp),
                )
                .padding(horizontal = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(16.dp))
        Text(
            modifier = Modifier.fillMaxWidth(),
            text = title,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
        Spacer(Modifier.height(12.dp))

        Box(modifier = Modifier.padding(vertical = 10.dp)) {
            MultiLineBasicTextField(
                value = description,
                backgroundColor = Color.White.copy(0.1f),
                showBorder = false,
                minLines = 2,
                fontSize = 14.sp,
                maxLength = maxLength,
                placeholder = placeholder,
                onValueChange = { onDescriptionChange(it) },
            )
        }
        Spacer(Modifier.height(16.dp))
    }
}

/** 举报图片证据容器组件 */
@Composable
fun ReportImageEvidenceContainer(title: String, images: List<String>, onClickAddImage: () -> Unit) {
    Column(
        modifier =
            Modifier.fillMaxWidth()
                .background(color = Color(0x1A78599A), shape = RoundedCornerShape(8.dp))
                .border(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                    width = 1.dp,
                    shape = RoundedCornerShape(8.dp),
                )
                .padding(horizontal = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(16.dp))
        Text(
            modifier = Modifier.fillMaxWidth(),
            text = title,
            fontSize = 14.sp,
            fontWeight = FontWeight.SemiBold,
            color = Color.White,
        )
        Spacer(Modifier.height(12.dp))

        Box(
            modifier =
                Modifier.size(88.dp)
                    .align(Alignment.Start)
                    .background(color = Color.White.copy(0.1f), shape = RoundedCornerShape(8.dp))
                    .clip(RoundedCornerShape(8.dp))
        ) {
            if (images.isNotEmpty()) {
                AsyncImage(
                    modifier = Modifier.fillMaxSize(),
                    model =
                        ImageRequest.Builder(LocalContext.current)
                            .data(images.firstOrNull())
                            .build(),
                    contentDescription = null,
                )
            } else {
                Image(
                    modifier =
                        Modifier.size(26.dp).align(Alignment.Center).noRippleClickable {
                            onClickAddImage()
                        },
                    painter = painterResource(R.drawable.btn_add6),
                    contentDescription = null,
                )
            }
        }

        Spacer(Modifier.height(16.dp))
    }
}

/** 保存按钮组件 */
@Composable
fun SaveBtn(onSave: () -> Unit, isSubmitting: Boolean = false) {
    Box(
        modifier =
            Modifier.fillMaxWidth()
                .padding(horizontal = 16.dp)
                .height(50.dp)
                .background(
                    brush =
                        Brush.linearGradient(
                            colors =
                                if (isSubmitting) {
                                    // TODO：需要优化视觉设计
                                    // https://github.com/NascentCore/inty/issues/436
                                    listOf(Color(0xFF666666), Color(0xFF888888))
                                } else {
                                    listOf(Color(0xFFC122FF), Color(0xFFFF905D))
                                }
                        ),
                    shape = RoundedCornerShape(25.dp),
                )
                .noRippleClickable {
                    if (!isSubmitting) {
                        onSave()
                    }
                }
    ) {
        if (isSubmitting) {
            // 显示加载动画
            CircularProgressIndicator(
                modifier = Modifier.align(Alignment.Center),
                color = Color.White,
                strokeWidth = 2.dp,
            )
        } else {
            Text(
                modifier = Modifier.align(Alignment.Center),
                text = stringResource(R.string.submit_button),
                fontSize = 16.sp,
                fontWeight = FontWeight.Normal,
                color = Color.White,
            )
        }
    }
}
