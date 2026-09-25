package de.ownai.app.data.model

import kotlinx.serialization.Serializable

@Serializable
data class RegisterRequest(
    val email: String,
    val password: String,
    val display_name: String
)

@Serializable
data class RegisterResponse(
    val id: String,
    val email: String,
    val display_name: String,
    val created_at: String
)

@Serializable
data class LoginRequest(
    val email: String,
    val password: String
)

@Serializable
data class RefreshRequest(
    val refresh_token: String
)

/** Response shape shared by POST /auth/login and POST /auth/refresh. */
@Serializable
data class TokenResponse(
    val access_token: String,
    val refresh_token: String,
    val token_type: String,
    val expires_in: Int
)

@Serializable
data class UserResponse(
    val id: String,
    val email: String,
    val display_name: String,
    val created_at: String
)
