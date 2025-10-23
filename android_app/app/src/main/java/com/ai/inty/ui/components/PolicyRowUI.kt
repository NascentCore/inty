package com.ai.inty.ui.components

import android.content.Context
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.TextUnit
import com.ai.intellimate.R
import com.ai.inty.utils.TextStyleUtils

@Composable
fun PolicyRow(context: Context, fontSize: TextUnit) {
    Row(
        // 占据全部宽度，这样下面的居中显示才有意义
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.Center,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        TextStyleUtils.BuildLink(
            context = context,
            text = stringResource(R.string.terms_of_use),
            url = context.getString(R.string.url_user_agreement),
            fontSize = fontSize,
        )

        Text(
            text =
                buildAnnotatedString {
                    withStyle(
                        SpanStyle(
                            color = Color.White.copy(alpha = 0.6f),
                            fontSize = fontSize,
                            fontWeight = FontWeight.Normal,
                        )
                    ) {
                        append(" and ")
                    }
                }
        )

        TextStyleUtils.BuildLink(
            context = context,
            text = stringResource(R.string.privacy_policy),
            url = context.getString(R.string.url_privacy_policy),
            fontSize = fontSize,
        )
    }
}
