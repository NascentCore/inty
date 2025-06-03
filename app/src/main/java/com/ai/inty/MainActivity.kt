package com.ai.inty

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import com.ai.inty.storage.Setting
import com.ai.inty.ui.theme.IntyTheme
import com.therouter.router.Autowired
import com.therouter.router.Route

@Route(path = Constant.ROUTE_MAIN)
class MainActivity : ComponentActivity() {

    @Autowired
    var action: String = ""

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            IntyTheme {
                Scaffold(modifier = Modifier.fillMaxSize()) { innerPadding ->
                    var msg by remember { mutableStateOf("${Setting.getCurUserID()} = ${Setting.getCurToken()}") }
                    Column {
                        Greeting(
                            name = msg,
                            modifier = Modifier.padding(innerPadding)
                        )
                        Button(onClick = {
                            Setting.changeUser("123")
                            Setting.setToken("token123")
                        }) {
                            Text(text = "change user=123")
                        }
                        Button(onClick = {
                            Setting.changeUser("guest_123")
                            Setting.setToken("guesttoken123")
                        }) {
                            Text(text = "change user=guest")
                        }
                        Button(onClick = {
                            msg = "${Setting.getCurUserID()} = ${Setting.getCurToken()}"
                        }) {
                            Text(text = "get user info")
                        }

                    }
                }
            }
        }
    }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Text(
        text = "Hello $name!",
        modifier = modifier
    )
}

@Preview(showBackground = true)
@Composable
fun GreetingPreview() {
    IntyTheme {
        Greeting("Android")
    }
}