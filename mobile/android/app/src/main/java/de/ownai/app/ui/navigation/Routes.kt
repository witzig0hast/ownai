package de.ownai.app.ui.navigation

/** Auth-flow routes, used by the NavHost shown while logged out. */
object AuthRoutes {
    const val LOGIN = "login"
    const val REGISTER = "register"
}

/** Main-app routes, used by the NavHost shown behind the bottom navigation bar. */
object MainRoutes {
    const val CHAT_LIST = "chat"
    const val CHAT_THREAD = "chat/{conversationId}"
    const val CALENDAR = "calendar"
    const val SUGGESTIONS = "suggestions"
    const val NOTIFICATION_ACCESS = "notification_access"

    const val CHAT_THREAD_ARG = "conversationId"

    fun chatThread(conversationId: String) = "chat/$conversationId"
}
