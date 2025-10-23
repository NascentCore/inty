package ai.sxwl.android.common.ui

import ai.sxwl.android.common.R
import android.graphics.Bitmap
import android.os.Build
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.navigation.NavController
import androidx.navigation.NavGraphBuilder
import androidx.navigation.NavOptions
import androidx.navigation.compose.composable
import androidx.navigation.toRoute
import kotlinx.serialization.Serializable

/**
 * 项目封装的简单的webView
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun IntelliWebView(url: String, onBack: () -> Unit) {

    var progress by rememberSaveable { mutableIntStateOf(0) }
    var isRefreshing by rememberSaveable { mutableStateOf(false) }
    var webTitle by remember { mutableStateOf("IntelliMate") }

    Column(Modifier.fillMaxSize()) {
        TopAppBar(
            title = {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.Center,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = webTitle, fontSize = 18.sp)
                }
            },
            navigationIcon = {
                IconButton(onClick = onBack) {
                    Icon(
                        painter = painterResource(R.drawable.ic_arrow_back_web),
                        contentDescription = "返回按钮",
                    )
                }
            },
            actions = {
                IconButton(onClick = {}, enabled = false) { }
            }
        )
        ProgressIndicator(progress)
        WebViewer(
            webUrl = url,
            isRefreshing = isRefreshing,
            setRefreshed = { isRefreshing = false },
            updateProgress = { currentProgress -> progress = currentProgress },
            titleInvoke = { title -> webTitle = title ?: "IntelliMate" },
        )
    }

}

@Composable
private fun ProgressIndicator(progress: Int) {
    AnimatedVisibility(
        modifier = Modifier.fillMaxWidth(), visible = progress in 1..99
    ) {
        LinearProgressIndicator(progress = { progress.toFloat() / 100 })
    }
}

@Composable
private fun WebViewer(
    modifier: Modifier = Modifier,
    webUrl: String,
    isRefreshing: Boolean,
    setRefreshed: () -> Unit,
    updateProgress: (Int) -> Unit,
    titleInvoke: (title: String?) -> Unit,
) {
    var webView: WebView? = null
    var isBackEnabled by rememberSaveable { mutableStateOf(false) }

    // Override back navigation to load WebView's previous webpage
    BackHandler(enabled = isBackEnabled) {
        webView?.goBack()
    }
    AndroidView(modifier = modifier.fillMaxSize(), factory = { context ->
        WebView(context).apply {
            webViewClient = object : WebViewClient() {

                // Enable BackHandler if WebView can go back
                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    super.onPageStarted(view, url, favicon)
                    isBackEnabled = view?.canGoBack() == true
                    //web的title
                    titleInvoke(view?.title)
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    super.onPageFinished(view, url)
                    titleInvoke(view?.title)
                }

            }
            webChromeClient = object : WebChromeClient() {

                // Pass up current loading progress to be used by ProgressIndicator function
                override fun onProgressChanged(view: WebView?, newProgress: Int) {
                    super.onProgressChanged(view, newProgress)
                    updateProgress(newProgress)
                }

                override fun onReceivedTitle(view: WebView?, title: String?) {
                    super.onReceivedTitle(view, title)
                    titleInvoke(title)
                }
            }
            // Configure WebView client
            with(this.settings) {
                domStorageEnabled = true
                javaScriptEnabled = true
                setSupportZoom(false)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    isAlgorithmicDarkeningAllowed = true
                }
            }
            this.loadUrl(webUrl)
            webView = this
        }
    }, update = { wv ->
        if (isRefreshing) {
            wv.reload()
            setRefreshed()
        }
        webView = wv
    })

}


//region 对外提供路由

//使用data class 定义对象，作为路由,内部就是参数
// https://developer.android.google.cn/guide/navigation/design/type-safety?hl=zh_cn
/**
 * 这里是跳转到webView的路由，带有参数url
 */
@Serializable
data class RouteWeb(val url: String)

/**
 * 扩展navController导航到Web页面
 */
fun NavController.navigateToWeb(url: String, options: NavOptions? = null) =
    navigate(route = RouteWeb(url), options)

/**
 * 添加页面到navHost
 */
fun NavGraphBuilder.webScreen(controller: NavController) {
    composable<RouteWeb> { backStackEntry ->
        val web = backStackEntry.toRoute<RouteWeb>()
        IntelliWebView(web.url, { controller.navigateUp() })
    }
}

//endregion
