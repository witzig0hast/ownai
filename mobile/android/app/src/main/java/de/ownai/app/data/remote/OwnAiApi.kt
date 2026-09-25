package de.ownai.app.data.remote

import de.ownai.app.data.model.CalendarEvent
import de.ownai.app.data.model.ConnectCalDavRequest
import de.ownai.app.data.model.ConnectCalDavResponse
import de.ownai.app.data.model.Conversation
import de.ownai.app.data.model.ConversationsResponse
import de.ownai.app.data.model.CreateConversationRequest
import de.ownai.app.data.model.CreateEventRequest
import de.ownai.app.data.model.DeviceRegisterRequest
import de.ownai.app.data.model.DeviceRegisterResponse
import de.ownai.app.data.model.DismissResponse
import de.ownai.app.data.model.EventsResponse
import de.ownai.app.data.model.IngestRequest
import de.ownai.app.data.model.IngestResponse
import de.ownai.app.data.model.LoginRequest
import de.ownai.app.data.model.MessagesResponse
import de.ownai.app.data.model.RefreshRequest
import de.ownai.app.data.model.RegisterRequest
import de.ownai.app.data.model.RegisterResponse
import de.ownai.app.data.model.SendMessageRequest
import de.ownai.app.data.model.SendMessageResponse
import de.ownai.app.data.model.Suggestion
import de.ownai.app.data.model.SuggestionsResponse
import de.ownai.app.data.model.TokenResponse
import de.ownai.app.data.model.UserResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

/**
 * Retrofit mirror of API.md. Paths are relative (no leading "/") so they
 * resolve against the trailing-slash base URL in BuildConfig.API_BASE_URL,
 * e.g. base "http://10.0.2.2:8000/api/v1/" + "auth/login" ->
 * "http://10.0.2.2:8000/api/v1/auth/login".
 *
 * Auth: most endpoints need a Bearer access token, which
 * [AuthInterceptor] attaches automatically. The two exceptions per API.md:
 * `/auth/*` (no auth yet) and `/notifications/ingest` (uses X-Device-Key
 * instead, passed explicitly below - never the user's JWT).
 */
interface OwnAiApi {

    // --- Auth ---

    @POST("auth/register")
    suspend fun register(@Body request: RegisterRequest): RegisterResponse

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): TokenResponse

    @POST("auth/refresh")
    suspend fun refresh(@Body request: RefreshRequest): TokenResponse

    @GET("users/me")
    suspend fun getMe(): UserResponse

    // --- Devices ---

    @POST("devices/register")
    suspend fun registerDevice(@Body request: DeviceRegisterRequest): DeviceRegisterResponse

    // --- Chat ---

    @GET("chat/conversations")
    suspend fun getConversations(): ConversationsResponse

    @POST("chat/conversations")
    suspend fun createConversation(@Body request: CreateConversationRequest): Conversation

    @GET("chat/conversations/{id}/messages")
    suspend fun getMessages(@Path("id") conversationId: String): MessagesResponse

    /** Synchronous: blocks server-side until the assistant's full reply (incl. any tool calls) is ready. */
    @POST("chat/conversations/{id}/messages")
    suspend fun sendMessage(
        @Path("id") conversationId: String,
        @Body request: SendMessageRequest
    ): SendMessageResponse

    // --- Calendar ---

    @POST("integrations/caldav")
    suspend fun connectCalDav(@Body request: ConnectCalDavRequest): ConnectCalDavResponse

    @GET("calendar/events")
    suspend fun getEvents(
        @Query("start") start: String,
        @Query("end") end: String
    ): EventsResponse

    @POST("calendar/events")
    suspend fun createEvent(@Body request: CreateEventRequest): CalendarEvent

    // --- Notifications (Android -> Backend) ---

    /** Device-key auth, deliberately not the user's Bearer token - see API.md, "Geräte". */
    @POST("notifications/ingest")
    suspend fun ingestNotification(
        @Header("X-Device-Key") deviceApiKey: String,
        @Body request: IngestRequest
    ): IngestResponse

    @GET("notifications/suggestions")
    suspend fun getSuggestions(@Query("status") status: String = "open"): SuggestionsResponse

    @POST("notifications/suggestions/{id}/apply")
    suspend fun applySuggestion(@Path("id") suggestionId: String): Suggestion

    @POST("notifications/suggestions/{id}/dismiss")
    suspend fun dismissSuggestion(@Path("id") suggestionId: String): DismissResponse
}
