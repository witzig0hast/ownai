package de.ownai.app

import android.app.Application
import de.ownai.app.data.AppContainer
import de.ownai.app.data.local.SessionManager

class OwnAiApplication : Application() {

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
        // Restore login state across process restarts (tokens survive in EncryptedSharedPreferences).
        SessionManager.setLoggedIn(container.securePrefs.hasSession())
    }
}
