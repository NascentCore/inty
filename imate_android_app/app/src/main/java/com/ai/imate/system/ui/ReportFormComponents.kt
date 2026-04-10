package com.ai.imate.system.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.BasicTextField
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckBox
import androidx.compose.material.icons.outlined.Add
import androidx.compose.material.icons.outlined.CheckBoxOutlineBlank
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.composed
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.SolidColor
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil3.compose.AsyncImage
import coil3.request.ImageRequest
import com.ai.imate.R

@Composable
fun ReportItemRow(text: String, selected: Boolean, onClick: () -> Unit) {
    Row(
        modifier =
            Modifier.fillMaxWidth()
                .height(48.dp)
                .clickableNoRipple(onClick),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(
            text = text,
            fontSize = 14.sp,
            color = Color.White.copy(0.55f),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.weight(1f))
        Icon(
            imageVector = if (selected) Icons.Filled.CheckBox else Icons.Outlined.CheckBoxOutlineBlank,
            contentDescription = null,
            modifier = Modifier.size(20.dp),
            tint = Color.White.copy(0.85f),
        )
    }
}

@Composable
fun ReportReasonsContainer(title: String, content: @Composable () -> Unit) {
    Column(
        modifier =
            Modifier.background(color = Color(0x1A78599A), shape = RoundedCornerShape(8.dp))
                .border(
                    brush =
                        Brush.linearGradient(
                            colors =
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent),
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
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent),
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
                Modifier.fillMaxWidth()
                    .padding(vertical = 10.dp)
                    .background(Color.White.copy(0.1f), RoundedCornerShape(8.dp))
                    .padding(horizontal = 12.dp, vertical = 10.dp)
        ) {
            BasicTextField(
                value = description.take(maxLength),
                onValueChange = { onDescriptionChange(it.take(maxLength)) },
                textStyle =
                    TextStyle(
                        color = Color.White,
                        fontSize = 14.sp,
                        lineHeight = 20.sp,
                    ),
                cursorBrush = SolidColor(Color.White),
                modifier = Modifier.fillMaxWidth().height(88.dp),
                decorationBox = { inner ->
                    if (description.isEmpty()) {
                        Text(
                            text = placeholder,
                            color = Color.White.copy(0.45f),
                            fontSize = 14.sp,
                        )
                    }
                    inner()
                },
            )
        }
        Spacer(Modifier.height(16.dp))
    }
}

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
                                listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent),
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
        Row(
            modifier =
                Modifier.fillMaxWidth()
                    .align(Alignment.Start)
                    .horizontalScroll(rememberScrollState())
        ) {
            images.forEachIndexed { index, imageUrl ->
                EvidenceImageThumbnail(imageUrl = imageUrl)
                if (index != images.lastIndex) {
                    Spacer(Modifier.size(8.dp))
                }
            }
            if (images.isNotEmpty()) {
                Spacer(Modifier.size(8.dp))
            }
            AddEvidenceImageButton(onClickAddImage = onClickAddImage)
        }
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun EvidenceImageThumbnail(imageUrl: String) {
    Box(
        modifier =
            Modifier.size(88.dp)
                .background(color = Color.White.copy(0.1f), shape = RoundedCornerShape(8.dp))
                .clip(RoundedCornerShape(8.dp))
    ) {
        AsyncImage(
            modifier = Modifier.fillMaxSize(),
            model = ImageRequest.Builder(LocalContext.current).data(imageUrl).build(),
            contentDescription = null,
            contentScale = ContentScale.Crop,
        )
    }
}

@Composable
private fun AddEvidenceImageButton(onClickAddImage: () -> Unit) {
    Box(
        modifier =
            Modifier.size(88.dp)
                .background(color = Color.White.copy(0.1f), shape = RoundedCornerShape(8.dp))
                .clip(RoundedCornerShape(8.dp))
                .clickableNoRipple(onClickAddImage),
        contentAlignment = Alignment.Center,
    ) {
        Icon(
            imageVector = Icons.Outlined.Add,
            contentDescription = stringResource(R.string.system_content_desc_add_evidence),
            modifier = Modifier.size(28.dp),
            tint = Color.White.copy(0.85f),
        )
    }
}

@Composable
fun ReportSubmitButton(onSave: () -> Unit, isSubmitting: Boolean = false, enabled: Boolean = true) {
    val isEnabled = enabled && !isSubmitting
    Box(
        modifier =
            Modifier.fillMaxWidth()
                .padding(horizontal = 16.dp)
                .height(50.dp)
                .background(
                    brush =
                        if (isEnabled) {
                            Brush.linearGradient(colors = listOf(Color(0xFFC122FF), Color(0xFFFF905D)))
                        } else {
                            Brush.linearGradient(
                                colors = listOf(Color.White.copy(0.12f), Color.White.copy(0.12f)),
                            )
                        },
                    shape = RoundedCornerShape(25.dp),
                )
                .clickableNoRipple {
                    if (isEnabled) {
                        onSave()
                    }
                }
    ) {
        if (isSubmitting) {
            CircularProgressIndicator(
                modifier = Modifier.align(Alignment.Center).size(24.dp),
                color = Color.White,
                strokeWidth = 2.dp,
            )
        } else {
            Text(
                modifier = Modifier.align(Alignment.Center),
                text = stringResource(R.string.system_submit_button),
                fontSize = 16.sp,
                fontWeight = FontWeight.Normal,
                color = if (isEnabled) Color.White else Color.White.copy(0.6f),
            )
        }
    }
}

private fun Modifier.clickableNoRipple(onClick: () -> Unit): Modifier =
    composed {
        then(
            clickable(
                indication = null,
                interactionSource = remember { MutableInteractionSource() },
                onClick = onClick,
            )
        )
    }
