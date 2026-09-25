package de.ownai.app.notification

import android.app.Notification
import android.content.pm.PackageManager
import android.provider.Telephony
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import de.ownai.app.OwnAiApplication
import de.ownai.app.data.model.IngestRequest
import de.ownai.app.data.remote.ApiResult
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import java.time.Instant

/**
 * The core Android-specific feature of OwnAI (see CONCEPT.md section 4):
 * reads notifications posted by other apps - with the user's explicit
 * "Notification access" grant, see [de.ownai.app.ui.notifications.NotificationAccessScreen] -
 * and forwards the relevant ones to `POST /notifications/ingest`, authenticated
 * with the per-device API key (never the user's JWT).
 *
 * ## Filtering
 * Kept deliberately simple and cheap to run on every posted notification:
 * - Our own app's notifications are always skipped.
 * - A small set of Android system packages that only ever post
 *   non-actionable chrome (System UI, the system package itself) is skipped.
 * - Ongoing notifications ([StatusBarNotification.isOngoing]) are skipped -
 *   this covers persistent/foreground-service notifications and media
 *   transport controls (play/pause etc.), which are never something the
 *   assistant should act on.
 * - Group-summary notifications ([Notification.FLAG_GROUP_SUMMARY]) are
 *   skipped, since the individual notifications in the group already carry
 *   the real content and forwarding both would duplicate it.
 * - Notifications with neither a title nor body text are skipped - nothing
 *   useful to analyze.
 * - Notifications posted at [Notification.PRIORITY_MIN] are skipped as a
 *   best-effort "silent" signal. This uses the legacy `Notification.priority`
 *   field (still populated by the platform for compatibility) rather than
 *   looking up the source app's [android.app.NotificationChannel] importance,
 *   which would need an extra per-notification lookup
 *   (`getNotificationChannels(pkg, user)`) for a fairly marginal gain - a
 *   reasonable place to start for v1, revisit if too much (or too little)
 *   gets filtered in practice.
 *
 * ## Category
 * API.md's `category` field is derived without needing SMS permissions:
 * [Telephony.Sms.getDefaultSmsPackage] names the current default SMS app
 * (a lightweight, permission-free lookup) - a notification from that package
 * is tagged "sms"; anything else tagged [Notification.CATEGORY_MESSAGE] by
 * its source app is "msg"; everything else is "other".
 *
 * ## What this is NOT
 * This reads the *notification* the default SMS app posts for an incoming
 * text - the same banner the user sees - not the raw SMS content via
 * `RECEIVE_SMS`/`READ_SMS`. See README.md ("SMS nuance") for why raw SMS
 * capture is out of scope for v1.
 */
class NotificationForwardingService : NotificationListenerService() {

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    private val systemPackageDenylist = setOf(
        "android",
        "com.android.systemui"
    )

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        super.onNotificationPosted(sbn)
        try {
            handleNotification(sbn)
        } catch (t: Throwable) {
            // Never let a malformed notification crash the listener - that would
            // silently disable forwarding for every app until the user re-grants access.
            Log.w(TAG, "Failed to process notification from ${sbn.packageName}", t)
        }
    }

    private fun handleNotification(sbn: StatusBarNotification) {
        if (sbn.packageName == packageName) return
        if (sbn.packageName in systemPackageDenylist) return
        if (sbn.isOngoing) return

        val notification = sbn.notification ?: return
        if (notification.flags and Notification.FLAG_GROUP_SUMMARY != 0) return
        if (notification.priority == Notification.PRIORITY_MIN) return

        val extras = notification.extras
        val title = extras?.getCharSequence(Notification.EXTRA_TITLE)?.toString().orEmpty()
        val text = extras?.getCharSequence(Notification.EXTRA_TEXT)?.toString().orEmpty()
        if (title.isBlank() && text.isBlank()) return

        val appLabel = resolveAppLabel(sbn.packageName)
        val category = resolveCategory(sbn, notification)
        val postedAt = Instant.ofEpochMilli(sbn.postTime).toString()

        val request = IngestRequest(
            package_name = sbn.packageName,
            app_label = appLabel,
            title = title,
            text = text,
            posted_at = postedAt,
            category = category
        )

        forward(request)
    }

    private fun resolveAppLabel(packageName: String): String {
        return try {
            val appInfo = packageManager.getApplicationInfo(packageName, 0)
            packageManager.getApplicationLabel(appInfo).toString()
        } catch (e: PackageManager.NameNotFoundException) {
            packageName
        }
    }

    private fun resolveCategory(sbn: StatusBarNotification, notification: Notification): String {
        val defaultSmsPackage = try {
            Telephony.Sms.getDefaultSmsPackage(applicationContext)
        } catch (e: Exception) {
            null
        }
        return when {
            defaultSmsPackage != null && sbn.packageName == defaultSmsPackage -> "sms"
            notification.category == Notification.CATEGORY_MESSAGE -> "msg"
            else -> "other"
        }
    }

    private fun forward(request: IngestRequest) {
        val app = application as? OwnAiApplication ?: return
        serviceScope.launch {
            when (val result = app.container.notificationRepository.ingest(request)) {
                is ApiResult.Success -> Log.d(TAG, "Forwarded notification from ${request.package_name}")
                is ApiResult.Failure -> Log.w(
                    TAG,
                    "Failed to forward notification from ${request.package_name}: ${result.message}"
                )
            }
        }
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        Log.d(TAG, "Notification listener connected")
    }

    override fun onDestroy() {
        serviceScope.cancel()
        super.onDestroy()
    }

    private companion object {
        const val TAG = "NotifForwarding"
    }
}
