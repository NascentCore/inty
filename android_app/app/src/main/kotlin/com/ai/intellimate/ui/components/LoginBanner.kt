// CREATED_BY_AGENT: GPT-5.2 (Cursor Cloud Agent)
package com.ai.intellimate.ui.components

import ai.sxwl.android.design.theme.AppColors
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.ai.intellimate.R

@Composable
fun UltimateCompanionshipBanner(modifier: Modifier = Modifier) {
    Box(
        modifier =
            modifier
                .background(
                    color = AppColors.DarkPurpleOverlay60,
                    shape = RoundedCornerShape(999.dp),
                )
                .padding(PaddingValues(horizontal = 14.dp, vertical = 8.dp)),
    ) {
        Text(
            text = stringResource(R.string.login_ultimate_companionship_banner),
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.92f),
            style = MaterialTheme.typography.titleSmall,
            fontWeight = FontWeight.SemiBold,
        )
    }
}

