package ai.sxwl.demos.intyvoicecall

import io.ktor.client.HttpClient
import io.ktor.client.engine.okhttp.OkHttp
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.websocket.WebSockets
import io.ktor.serialization.kotlinx.KotlinxWebsocketSerializationConverter
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json

fun createIntyDemoHttpClient(): HttpClient {
    val json =
        Json {
            ignoreUnknownKeys = true
            isLenient = true
            encodeDefaults = false
        }
    return HttpClient(OkHttp) {
        install(ContentNegotiation) { json(json) }
        install(WebSockets) { contentConverter = KotlinxWebsocketSerializationConverter(json) }
    }
}
