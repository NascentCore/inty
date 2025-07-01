package com.ai.inty

import android.content.Context
import android.content.Intent
import android.net.Uri
import android.os.Bundle
import android.widget.Toast
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
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
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
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
import androidx.core.content.ContextCompat.startActivity
import com.ai.inty.base.BaseActivity
import com.ai.inty.base.noRippleClickable
import com.ai.inty.ui.theme.BackGround
import com.ai.inty.ui.theme.IntyTheme
import com.inty.utils.storage.IntySetting
import com.therouter.router.Route
import androidx.lifecycle.ViewModelProvider
import com.ai.inty.viewmodels.MainViewModel
import com.therouter.TheRouter

@Route(path = Constant.ROUTE_SETTING)
class SettingActivity : BaseActivity() {

    private val mainViewModel: MainViewModel by lazy {
        ViewModelProvider(this)[MainViewModel::class.java]
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)


        setContent {
            IntyTheme {
                SettingScreen(
                    modifier = Modifier
                        .fillMaxSize()
                        .background(BackGround),
                    onBack = {
                        finish()
                    },
                    onLogout = {
                        // 使用MainViewModel的logout方法，不重启应用
                        mainViewModel.logout()
                        // 显示退出成功提示
                        Toast.makeText(this@SettingActivity, getString(R.string.logout_successfully), Toast.LENGTH_SHORT).show()
                        // 返回到主页面
                        TheRouter.build(Constant.ROUTE_MAIN).navigation(this@SettingActivity)
                        finish()
                    }
                )
            }
        }
    }

}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingScreen(
    modifier: Modifier,
    onBack: () -> Unit,
    onLogout: () -> Unit,
) {

    val context = LocalContext.current

    var showKeepTalking by remember { mutableStateOf(IntySetting.isShowKeepTalking()) }
    var isAutoPlayAudio by remember { mutableStateOf(IntySetting.isAutoPlayAudio()) }

    Scaffold(
        modifier = modifier,
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        text = stringResource(R.string.settings),
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

                }
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier.padding(innerPadding)
        ) {

            Column(
                modifier = Modifier
                    .padding(horizontal = 16.dp)
                    .fillMaxWidth()
                    .border(
                        brush = Brush.linearGradient(
                            colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                        width = 1.dp,
                        shape = RoundedCornerShape(8.dp)
                    )
                    .background(
                        color = Color(0x3378599A),
                        shape = RoundedCornerShape(8.dp)
                    )
            ) {
                Spacer(Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth().height(48.dp).padding(horizontal = 12.dp).noRippleClickable {
                        showKeepTalking = !showKeepTalking
                        IntySetting.setShowKeepTalking(showKeepTalking)
                    },
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = stringResource(R.string.settings_keep_talking),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                    Spacer(Modifier.weight(1f))
                    Image(
                        painter = if (showKeepTalking) painterResource(R.drawable.opened) else painterResource(R.drawable.closed),
                        contentDescription = null,
                    )
                }
                // 暂时隐藏 auto-play voice messages 开关和分隔线
                /*
                Spacer(Modifier.height(4.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth().height(1.dp)
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                            )
                        )
                ) {

                }
                Spacer(Modifier.height(4.dp))
                Row(
                    modifier = Modifier.fillMaxWidth().height(48.dp).padding(horizontal = 12.dp).noRippleClickable {
                        isAutoPlayAudio = !isAutoPlayAudio
                        IntySetting.setAutoPlayAudio(isAutoPlayAudio)
                    },
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = stringResource(R.string.settings_auto_play_audio),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White

                    )
                    Spacer(Modifier.weight(1f))
                    Image(
                        painter = if (isAutoPlayAudio) painterResource(R.drawable.opened) else painterResource(R.drawable.closed),
                        contentDescription = null,
                    )
                }
                */
                Spacer(Modifier.height(8.dp))
            }

            Spacer(Modifier.height(16.dp))

            Column(
                modifier = Modifier
                    .padding(horizontal = 16.dp)
                    .fillMaxWidth()
                    .border(
                        brush = Brush.linearGradient(
                            colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                        width = 1.dp,
                        shape = RoundedCornerShape(8.dp)
                    )
                    .background(
                        color = Color(0x3378599A),
                        shape = RoundedCornerShape(8.dp)
                    )
            ) {
                val email = stringResource(R.string.settings_email_inty)
                Spacer(Modifier.height(8.dp))
                Row(
                    modifier = Modifier.fillMaxWidth().height(48.dp).padding(horizontal = 12.dp).noRippleClickable {
                        mailTo(context, email)
                    },
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = stringResource(R.string.settings_email_support),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White

                    )
                    Spacer(Modifier.weight(1f))
                    Text(
                        text = email,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Normal,
                        color = Color.White.copy(0.55f)

                    )
                    Spacer(Modifier.width(10.dp))
                    Image(
                        modifier = Modifier.noRippleClickable {

                        },
                        painter = painterResource(R.drawable.icon_next),
                        contentDescription = null,
                    )
                }
                Spacer(Modifier.height(4.dp))
                Box(
                    modifier = Modifier
                        .fillMaxWidth().height(1.dp)
                        .background(
                            brush = Brush.horizontalGradient(
                                colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                            )
                        )
                ) {

                }
                Spacer(Modifier.height(4.dp))
                Row(
                    modifier = Modifier.fillMaxWidth().height(48.dp).padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = stringResource(R.string.settings_about),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                    Spacer(Modifier.weight(1f))
                    Text(
                        text = BuildConfig.VERSION_NAME,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Normal,
                        color = Color.White.copy(0.55f)
                    )
                }
                Spacer(Modifier.height(8.dp))
            }


            Spacer(Modifier.height(16.dp))

            Column(
                modifier = Modifier
                    .padding(horizontal = 16.dp)
                    .fillMaxWidth()
                    .border(
                        brush = Brush.linearGradient(
                            colors = listOf(Color.Transparent, Color.White.copy(0.2f), Color.Transparent)
                        ),
                        width = 1.dp,
                        shape = RoundedCornerShape(8.dp)
                    )
                    .background(
                        color = Color(0x3378599A),
                        shape = RoundedCornerShape(8.dp)
                    )
                    .noRippleClickable {
                        onLogout()
                    }
            ) {
                Spacer(Modifier.height(21.dp))
                Row(
                    modifier = Modifier.fillMaxWidth().height(48.dp).padding(horizontal = 12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Spacer(Modifier.weight(1f))
                    Text(
                        text = stringResource(R.string.logout),
                        fontSize = 14.sp,
                        fontWeight = FontWeight.SemiBold,
                        color = Color.White
                    )
                    Spacer(Modifier.weight(1f))
                }

                Spacer(Modifier.height(17.dp))
            }


        }
    }
}

fun restartAppProcess(context: Context) {
    val intent = context.packageManager.getLaunchIntentForPackage(context.packageName)
    intent?.apply {
        addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP) // 清除历史栈
        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)  // 新任务栈
        context.startActivity(this)
    }
    // 终止当前进程
    android.os.Process.killProcess(android.os.Process.myPid())
}

fun mailTo(context: Context, email: String) {
    val intent = Intent(Intent.ACTION_SENDTO).apply {
        data = Uri.parse("mailto:$email")
    }
    try {
        context.startActivity(Intent.createChooser(intent, "email"))
    } catch (e: Exception) {
        Toast.makeText(context, "email error", Toast.LENGTH_SHORT).show()
    }
}