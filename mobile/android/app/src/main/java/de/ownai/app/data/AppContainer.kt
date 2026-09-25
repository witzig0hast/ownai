package de.ownai.app.data

import android.content.Context
import de.ownai.app.BuildConfig
import de.ownai.app.data.local.SecurePrefs
import de.ownai.app.data.remote.AuthInterceptor
import de.ownai.app.data.remote.OwnAiApi
import de.ownai.app.data.remote.TokenAuthenticator
import de.ownai.app.data.repository.AuthRepository
import de.ownai.app.data.repository.CalendarRepository
import de.ownai.app.data.repository.ChatRepository
import de.ownai.app.data.repository.DeviceRepository
import de.ownai.app.data.repository.NotificationRepository
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Simple, hand-rolled dependency container (no DI framework - the app is
 * small enough that one isn't warranted). Created once in [de.ownai.app.OwnAiApplication]
 * and reachable from both Compose (via LocalContext -> Application) and the
 * background [de.ownai.app.notification.NotificationForwardingService].
 */
class AppContainer(context: Context) {

    private val appContext = context.applicationContext

    val securePrefs = SecurePrefs(appContext)

    val json: Json = Json {
        ignoreUnknownKeys = true
        encodeDefaults = true
        isLenient = true
    }

    private val jsonMediaType = "application/json; charset=UTF-8".toMediaType()

    /**
     * Plain client with no auth interceptor/authenticator, used only to call
     * `/auth/refresh` itself - attaching [TokenAuthenticator] to this one
     * would let a failing refresh call recurse into itself.
     */
    private val refreshHttpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private val refreshApi: OwnAiApi = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(refreshHttpClient)
        .addConverterFactory(json.asConverterFactory(jsonMediaType))
        .build()
        .create(OwnAiApi::class.java)

    private val tokenAuthenticator = TokenAuthenticator(securePrefs, refreshApi)

    private val httpClient: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(15, TimeUnit.SECONDS)
        .readTimeout(60, TimeUnit.SECONDS) // chat replies are synchronous and can take a while (LLM + tool calls)
        .addInterceptor(AuthInterceptor(securePrefs))
        .authenticator(tokenAuthenticator)
        .apply {
            if (BuildConfig.DEBUG) {
                addInterceptor(HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC })
            }
        }
        .build()

    val api: OwnAiApi = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .client(httpClient)
        .addConverterFactory(json.asConverterFactory(jsonMediaType))
        .build()
        .create(OwnAiApi::class.java)

    val authRepository = AuthRepository(api, securePrefs, json)
    val deviceRepository = DeviceRepository(api, securePrefs, json)
    val chatRepository = ChatRepository(api, json)
    val calendarRepository = CalendarRepository(api, json)
    val notificationRepository = NotificationRepository(api, securePrefs, json)
}
