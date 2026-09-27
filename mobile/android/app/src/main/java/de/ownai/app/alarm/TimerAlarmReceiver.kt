package de.ownai.app.alarm

import android.annotation.SuppressLint
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import de.ownai.app.MainActivity

/**
 * Fires when a timer scheduled via [TimerAlarmScheduler] expires - shows a local notification
 * even if the app isn't running (that's the whole point: a "5 Minuten Nudeln"-style timer is
 * useless if it only fires while the app happens to be open). No server round-trip here; the
 * alarm itself already carries everything needed to show the notification.
 */
class TimerAlarmReceiver : BroadcastReceiver() {

    @SuppressLint("MissingPermission") // guarded by the hasPermission check below - lint can't see through it
    override fun onReceive(context: Context, intent: Intent) {
        val timerId = intent.getStringExtra(EXTRA_TIMER_ID) ?: return
        val label = intent.getStringExtra(EXTRA_LABEL)

        ensureChannel(context)

        val contentIntent = PendingIntent.getActivity(
            context,
            timerId.hashCode(),
            Intent(context, MainActivity::class.java).apply {
                flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            },
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(context, CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setContentTitle("Timer abgelaufen")
            .setContentText(label?.takeIf { it.isNotBlank() } ?: "Dein Timer ist abgelaufen.")
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setAutoCancel(true)
            .setContentIntent(contentIntent)
            .build()

        val hasPermission = Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU ||
            ContextCompat.checkSelfPermission(context, android.Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
        if (hasPermission) {
            NotificationManagerCompat.from(context).notify(timerId.hashCode(), notification)
        }
        // If permission was never granted, the timer still ran, just silently - the user can
        // grant "Allow OwnAI notifications" from NotificationAccessScreen for next time.
    }

    private fun ensureChannel(context: Context) {
        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (manager.getNotificationChannel(CHANNEL_ID) == null) {
            val channel = NotificationChannel(CHANNEL_ID, "Timer", NotificationManager.IMPORTANCE_HIGH).apply {
                description = "Benachrichtigung, wenn ein OwnAI-Timer abläuft"
            }
            manager.createNotificationChannel(channel)
        }
    }

    companion object {
        const val EXTRA_TIMER_ID = "timer_id"
        const val EXTRA_LABEL = "label"
        const val CHANNEL_ID = "ownai_timers"
    }
}
