package de.ownai.app.alarm

import android.annotation.SuppressLint
import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import java.time.OffsetDateTime

/**
 * Schedules/cancels the local alarm that makes a timer fire a notification even if the app
 * isn't running (see [TimerAlarmReceiver]). Scheduling by the same timer id is idempotent -
 * AlarmManager replaces any existing alarm under the same PendingIntent request code - so this
 * is safe to call repeatedly for the same timer (e.g. on every poll/tool-call sync) without
 * tracking what's already scheduled.
 */
object TimerAlarmScheduler {

    /**
     * The backend sends `ends_at` as Python's `datetime.isoformat()`, e.g.
     * "2026-09-27T16:45:00.615260+00:00" - a "+00:00" offset, not a "Z" suffix. Parse with
     * [OffsetDateTime], not [java.time.Instant] directly: `Instant.parse` requires a literal "Z"
     * and throws on "+00:00", which would otherwise make every timer silently fail to schedule.
     */
    fun scheduleFromIso(context: Context, timerId: String, label: String?, endsAtIso: String) {
        val endsAtMillis = runCatching { OffsetDateTime.parse(endsAtIso).toInstant().toEpochMilli() }.getOrNull()
            ?: return
        schedule(context, timerId, label, endsAtMillis)
    }

    @SuppressLint("MissingPermission") // guarded by canScheduleExactAlarms() / the inexact fallback below
    fun schedule(context: Context, timerId: String, label: String?, endsAtEpochMillis: Long) {
        val appContext = context.applicationContext
        val alarmManager = appContext.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        val pendingIntent = pendingIntentFor(appContext, timerId, label)

        val canScheduleExact = Build.VERSION.SDK_INT < Build.VERSION_CODES.S || alarmManager.canScheduleExactAlarms()
        try {
            if (canScheduleExact) {
                alarmManager.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, endsAtEpochMillis, pendingIntent)
            } else {
                // No permission for exact alarms on this OS version - an inexact one (subject to
                // Doze deferral) still beats no alarm at all.
                alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, endsAtEpochMillis, pendingIntent)
            }
        } catch (e: SecurityException) {
            // Some OEMs revoke exact-alarm scheduling despite canScheduleExactAlarms() - fall back.
            alarmManager.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, endsAtEpochMillis, pendingIntent)
        }
    }

    fun cancel(context: Context, timerId: String) {
        val appContext = context.applicationContext
        val alarmManager = appContext.getSystemService(Context.ALARM_SERVICE) as? AlarmManager ?: return
        alarmManager.cancel(pendingIntentFor(appContext, timerId, label = null))
    }

    private fun pendingIntentFor(context: Context, timerId: String, label: String?): PendingIntent {
        val intent = Intent(context, TimerAlarmReceiver::class.java).apply {
            putExtra(TimerAlarmReceiver.EXTRA_TIMER_ID, timerId)
            putExtra(TimerAlarmReceiver.EXTRA_LABEL, label)
        }
        return PendingIntent.getBroadcast(
            context,
            timerId.hashCode(),
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }
}
