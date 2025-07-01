package com.ai.inty

import android.os.Bundle
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.lifecycleScope
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.IntyImage
import com.ai.inty.base.IntySmallTextField2
import com.ai.inty.base.noRippleClickable
import com.ai.inty.beans.ReportItem
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.ai.inty.viewmodels.ReportViewModel
import com.inty.utils.log.EasyLog
import com.therouter.router.Autowired
import com.therouter.router.Route
import kotlinx.coroutines.launch

@Route(path = Constant.ROUTE_REPORT)
class ReportActivity : BaseActivity() {

    private val viewModel: ReportViewModel by viewModels()


    @Autowired
    var targetID: String = ""
    
    @Autowired
    var targetType: String = "USER"

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        viewModel.targetID = targetID
        viewModel.targetType = targetType

        lifecycleScope.launch {
            viewModel.finishActivity.collect {
                if (it) {
                    finish()
                }
            }
        }

        setContent {
            IntyTheme {
                val reasons = viewModel.reasons.collectAsState()
                val selectIDs = viewModel.selectIDS
                val description = viewModel.description.collectAsState()
                val localImages = viewModel.localImages

                val galleryLauncher = rememberLauncherForActivityResult(
                    ActivityResultContracts.GetContent()) { imageUri ->
                    imageUri?.let {
                        viewModel.onAddImage(imageUri)
                    }

                }

                ReportScreen(
                    reasons = reasons.value,
                    selectIDs = selectIDs,
                    onClickReason = { id, isSelect ->
                        EasyLog.log("onClickReason id = $id, isSelect = $isSelect")
                        if (isSelect) {
                            viewModel.selectIDS.add(id)
                        } else {
                            viewModel.selectIDS.remove(id)
                        }
                    },
                    description = description.value,
                    onDescriptionChange = {
                        viewModel.setDescription(it)
                    },
                    images = localImages.toList(),
                    onClickAddImage = {
                        galleryLauncher.launch("image/*")
                    },
                    onSave = {
                        viewModel.submit()
                    },
                    onBack = {
                        finish()
                    }
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportScreen(
    onBack: () -> Unit = {},
    reasons: List<ReportItem>,
    selectIDs: Set<Int>,
    onClickReason: (Int, Boolean) -> Unit,
    description: String,
    onDescriptionChange: (String) -> Unit,
    images: List<String>,
    onClickAddImage: () -> Unit,
    onSave: () -> Unit,
) {

    Scaffold(
        modifier = Modifier.fillMaxSize().background(BackGround),
        containerColor = BackGround,
        topBar = {
            CenterAlignedTopAppBar(
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors().copy(containerColor = Color.Transparent),
                title = {
                    Text(
                        text = stringResource(R.string.report),
                        color = Color.White,
                        fontWeight = FontWeight.SemiBold,
                        fontSize = 20.sp,
                    )
                },
                navigationIcon = {
                    Image(
                        modifier = Modifier
                            .padding(horizontal = 12.dp)
                            .noRippleClickable {
                                onBack()
                            },
                        painter = painterResource(R.drawable.back),
                        contentDescription = null,
                    )

                },

            )
        },
        bottomBar = {
            Column {

                SaveBtn(onSave = onSave)
                Spacer(Modifier.height(60.dp))
            }
        }
    ) { paddingValues ->

        Column(
            modifier = Modifier
                .padding(
                    top = paddingValues.calculateTopPadding(),
                    bottom = paddingValues.calculateBottomPadding(),
                    start = 16.dp,
                    end = 16.dp,
                )
                .verticalScroll(rememberScrollState())
            ,
            horizontalAlignment = Alignment.CenterHorizontally
        ) {

            Spacer(Modifier.height(16.dp))

            Column(
                modifier = Modifier
                    .background(
                        color = Color(0x1A78599A),
                        shape = RoundedCornerShape(8.dp)
                    )
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
                    .padding(horizontal = 12.dp)
                ,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Spacer(Modifier.height(16.dp))

                Text(
                    text = "NPC *",
                    modifier = Modifier.fillMaxWidth(),
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )
                Spacer(Modifier.height(12.dp))

                reasons.forEach { reason ->
                    val isSelected = selectIDs.contains(reason.id)
                    ReportItem(
                        text = reason.description,
                        selected = isSelected,
                        onClick = {
                            onClickReason(reason.id, !isSelected)
                        }
                    )
                }

                Spacer(Modifier.height(14.dp))
            }

            Spacer(Modifier.height(24.dp))


            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        color = Color(0x1A78599A),
                        shape = RoundedCornerShape(8.dp)
                    )
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
                    .padding(horizontal = 12.dp)
                ,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Spacer(Modifier.height(16.dp))
                Text(
                    modifier = Modifier.fillMaxWidth(),
                    text = "Report description*",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )
                Spacer(Modifier.height(12.dp))

                Box(
                    modifier = Modifier.fillMaxWidth().height(112.dp)
                        .background(
                            color = Color.White.copy(0.1f),
                            shape = RoundedCornerShape(8.dp)
                        )
                        .padding(vertical = 10.dp)
                ) {
                    IntySmallTextField2(
                        modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp),
                        value = description,
                        placeholder = {
                            Text(
                                modifier = Modifier.align(Alignment.TopStart),
                                text = "Please fill in the feedback content...",
                                fontWeight = FontWeight.Normal,
                                color = Color.White.copy(0.55f),
                                fontSize = 14.sp,
                            )
                        },
                        onValueChange = {
                            onDescriptionChange(it)
                        },

                    )

                    Text(
                        modifier = Modifier.align(Alignment.BottomEnd).padding(horizontal = 12.dp),
                        text = "${description.length}/400",
                        fontSize = 12.sp,
                        color = Color.White.copy(0.55f),

                    )
                }
                Spacer(Modifier.height(16.dp))
            }


            Spacer(Modifier.height(24.dp))


            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(
                        color = Color(0x1A78599A),
                        shape = RoundedCornerShape(8.dp)
                    )
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
                    .padding(horizontal = 12.dp)
                ,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Spacer(Modifier.height(16.dp))
                Text(
                    modifier = Modifier.fillMaxWidth(),
                    text = "Image evidence",
                    fontSize = 14.sp,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White,
                )
                Spacer(Modifier.height(12.dp))

                Box(
                    modifier = Modifier.size(88.dp)
                        .align(Alignment.Start)
                        .background(
                            color = Color.White.copy(0.1f),
                            shape = RoundedCornerShape(8.dp)
                        )
                        .clip(RoundedCornerShape(8.dp))
                    ,
                ) {
                    if (images.isNotEmpty()) {
                        IntyImage(
                            modifier = Modifier.fillMaxSize(),
                            model = images.firstOrNull(),
                        )
                    } else {
                        Image(
                            modifier = Modifier.size(26.dp).align(Alignment.Center).noRippleClickable {
                                onClickAddImage()
                            },
                            painter = painterResource(R.drawable.btn_add6),
                            contentDescription = null,
                        )
                    }
                }

                Spacer(Modifier.height(16.dp))
            }

            Spacer(Modifier.height(60.dp))



        }
    }
}


@Composable
fun ReportItem(
    text: String,
    selected: Boolean,
    onClick: () -> Unit = {},
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp)
            .noRippleClickable {
                onClick()
            }
        ,
        verticalAlignment = Alignment.CenterVertically,
    ) {

        Text(
            text = text,
            fontSize = 14.sp,
            color = Color.White.copy(0.55f),
        )
        Spacer(Modifier.weight(1f))

        Image(
            painter = painterResource(
                if (selected) R.drawable.checked else R.drawable.check_no
            ),
            contentDescription = null,
        )
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
            text = "Submit",
            fontSize = 16.sp,
            fontWeight = FontWeight.Normal,
            color = Color.White,
        )
    }
}
