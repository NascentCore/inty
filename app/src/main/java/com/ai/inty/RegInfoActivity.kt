package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.tooling.preview.Preview
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.GENDER
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.RegInfoActivityViewModel
import com.therouter.router.Route
import kotlinx.coroutines.launch

@Route(path = Constant.ROUTE_REG_INFO)
class RegInfoActivity : BaseActivity() {

    private val viewModel: RegInfoActivityViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()


        setContent {
            IntyTheme {
                RegInfoScreen(
                    onClose = {
                        finish()
                    },
                    onSave = { gender, age ->
                        viewModel.onSave(gender, age)
                    }
                )
            }
        }

        lifecycleScope.launch {
            viewModel.finishActivity.collect {
                if (it) {
                    finish()
                }
            }
        }
    }
}

@Composable
fun RegInfoScreen(
    onClose: () -> Unit = {},
    onSave: (gender: GENDER, age: String) -> Unit = { gender, age -> },
) {
    var selectGender by remember { mutableStateOf(GENDER.OTHER) }
    var selectAge by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(0.6f))
        ,
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .align(Alignment.BottomCenter)
                .background(
                    brush = Brush.verticalGradient(
                        colors = listOf(
                            Color(0xFF322341),
                            Color(0xFF120E24)
                        )
                    ),
                    shape = RoundedCornerShape(24.dp, 24.dp, 0.dp, 0.dp)
                )
        ) {
            Image(
                modifier = Modifier
                    .align(Alignment.End)
                    .padding(end = 16.dp, top = 16.dp)
                    .size(18.dp, 18.dp)
                    .noRippleClickable {
                        onClose()
                    }
                ,
                painter = painterResource(R.drawable.close),
                contentDescription = null,
            )
            Spacer(Modifier.height(6.dp))
            Text(
                modifier = Modifier.padding(horizontal = 24.dp),
                text = "Hello \uD83D\uDC4B",
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
            )
            Spacer(Modifier.height(13.dp))
            Text(
                modifier = Modifier.padding(horizontal = 24.dp),
                text = "Welcome to HeartMate",
                fontSize = 26.sp,
                fontWeight = FontWeight.Bold,
                color = Color.White,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                modifier = Modifier.padding(horizontal = 24.dp),
                text = "Tell us more for a better personalized experience",
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
                color = Color.White.copy(0.55f),
            )
            Spacer(Modifier.height(26.dp))
            Text(
                modifier = Modifier.padding(horizontal = 24.dp),
                text = "Which pronoun do you use?  *",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
            Spacer(Modifier.height(12.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
            ) {
                Spacer(Modifier.width(40.dp))
                GenderItem(
                    gender = GENDER.MALE,
                    selected = (selectGender == GENDER.MALE),
                    onClick = {
                        selectGender = GENDER.MALE
                    }
                )
                Spacer(Modifier.weight(0.5f))
                GenderItem(
                    gender = GENDER.FEMALE,
                    selected = (selectGender == GENDER.FEMALE),
                    onClick = {
                        selectGender = GENDER.FEMALE
                    }
                )
                Spacer(Modifier.weight(0.5f))
                GenderItem(
                    gender = GENDER.OTHER,
                    selected = (selectGender == GENDER.OTHER),
                    onClick = {
                        selectGender = GENDER.OTHER
                    }
                )
                Spacer(Modifier.width(40.dp))
            }
            Spacer(Modifier.height(16.dp))
            Text(
                modifier = Modifier.padding(horizontal = 24.dp),
                text = "What is your age? *",
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
                color = Color.White,
            )
            Spacer(Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth().height(48.dp),
            ) {
                Spacer(Modifier.width(24.dp))
                AgeItem(
                    text = "18-20",
                    isSelected = (selectAge == "18-20"),
                    onSelected = {
                        selectAge = "18-20"
                    }
                )
                Spacer(Modifier.width(13.dp))
                AgeItem(
                    text = "21-23",
                    isSelected = (selectAge == "21-23"),
                    onSelected = {
                        selectAge = "21-23"
                    }
                )
                Spacer(Modifier.width(24.dp))
            }

            Spacer(Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth().height(48.dp),
            ) {
                Spacer(Modifier.width(24.dp))
                AgeItem(
                    text = "30-36",
                    isSelected = (selectAge == "30-36"),
                    onSelected = {
                        selectAge = "30-36"
                    }
                )
                Spacer(Modifier.width(13.dp))
                AgeItem(
                    text = "Above 36",
                    isSelected = (selectAge == "Above 36"),
                    onSelected = {
                        selectAge = "Above 36"
                    }
                )
                Spacer(Modifier.width(24.dp))
            }
            Spacer(Modifier.height(64.dp))
            SaveBtn(
                onSave = {
                    onSave(selectGender, selectAge)
                }
            )

            Spacer(Modifier.height(60.dp))
        }
    }
}


@Composable
private fun SaveBtn(onSave: () -> Unit) {
    Box(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp)
            .height(50.dp)
            .background(
                brush = Brush.linearGradient(
                    colors = listOf(Color(0xFFC122FF), Color(0xFFFF905D))
                ),
                shape = RoundedCornerShape(25.dp)
            )
            .noRippleClickable {
                onSave()
            }
    ) {
        Text(
            modifier = Modifier.align(Alignment.Center),
            text = "Enter",
            fontSize = 16.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White,
        )
    }
}

@Composable
fun GenderItem(
    gender: GENDER,
    selected: Boolean,
    onClick: () -> Unit,
) {
    val gender_bg = when (gender) {
        GENDER.MALE -> R.drawable.gender_bg_male
        GENDER.FEMALE -> R.drawable.gender_bg_female
        GENDER.OTHER -> R.drawable.gender_bg_other
    }
    val gender_icon = when (gender) {
        GENDER.MALE -> if (selected) R.drawable.gender_male_selected else R.drawable.gender_male
        GENDER.FEMALE -> if (selected) R.drawable.gender_female_selected else R.drawable.gender_female
        GENDER.OTHER -> if (selected) R.drawable.gender_other_selected else R.drawable.gender_other
    }
    Column(
        modifier = Modifier.noRippleClickable {
            onClick()
        },
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .size(80.dp)
                .background(
                    color = Color.White.copy(0.1f),
                    shape = CircleShape
                )
                .then(
                    if (selected) {
                        Modifier.border(
                            brush = Brush.linearGradient(
                                colors = listOf(
                                    Color(0xffC122FF),
                                    Color(0xffFF905D),
                                )
                            ),
                            width = 2.dp,
                            shape = CircleShape
                        )
                    } else {
                        Modifier.border(
                            width = 0.5.dp,
                            color = Color.White.copy(0.2f),
                            shape = CircleShape
                        )
                    }
                )
            ,
            contentAlignment = Alignment.Center,
        ) {
//            Image(
//                modifier = Modifier.fillMaxSize(),
//                painter = painterResource(gender_bg),
//                contentDescription = null,
//            )
            Image(
                modifier = Modifier.size(38.dp),
                painter = painterResource(gender_icon),
                contentDescription = null,
            )
        }
        Spacer(Modifier.height(8.dp))
        Text(
            text = when (gender) {
                GENDER.MALE -> "He/Him"
                GENDER.FEMALE -> "She/Her"
                GENDER.OTHER -> "They/Them"
            },
            color = if (selected) Color.White else Color.White.copy(0.55f),
            fontSize = 14.sp,
        )
    }
}

@Composable
fun RowScope.AgeItem(
    text: String,
    isSelected: Boolean = false,
    onSelected: () -> Unit = {}
) {
    Box(
        modifier = Modifier
            .weight(1f)
            .fillMaxHeight()
            .background(
                color = Color(0x3378599A),
                shape = RoundedCornerShape(24.dp)
            )
            .then(
                if (isSelected) {
                    Modifier.border(
                        brush = Brush.linearGradient(
                            colors = listOf(
                                Color(0xffC122FF),
                                Color(0xffFF905D),
                            )
                        ),
                        width = 2.dp,
                        shape = RoundedCornerShape(24.dp)
                    )
                } else {
                    Modifier.border(
                        width = 0.5.dp,
                        color = Color.White.copy(0.2f),
                        shape = RoundedCornerShape(24.dp)
                    )
                }
            )
            .noRippleClickable {
                onSelected()
            }
        ,
        contentAlignment = Alignment.Center,
    ) {
        if (isSelected) {
            Text(
                text = text,
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.SemiBold,
            )
        } else {
            Text(
                text = text,
                color = Color.White.copy(0.55f),
                fontSize = 14.sp,
                fontWeight = FontWeight.Normal,
            )
        }
    }
}

@Preview(backgroundColor = 0xFFffffff, showBackground = true)
@Composable
fun RegInfoScreenPreview() {
    RegInfoScreen()
}