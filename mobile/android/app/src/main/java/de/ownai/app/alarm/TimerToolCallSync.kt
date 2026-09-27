package de.ownai.app.alarm

import android.content.Context
import de.ownai.app.data.model.Message
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonPrimitive

/**
 * Scans a conversation's messages for set_timer/cancel_timer tool-call results (see API.md /
 * app/agent/tools.py on the backend) and schedules or cancels the corresponding local alarm.
 * Idempotent (see [TimerAlarmScheduler]) - safe to call on every message-list change, e.g. from
 * a Composable's LaunchedEffect, without tracking which tool calls were already handled.
 */
fun syncTimerAlarmsFromMessages(context: Context, messages: List<Message>) {
    for (message in messages) {
        val toolCalls = message.tool_calls ?: continue
        for (call in toolCalls) {
            val result = call.result as? JsonObject ?: continue
            when (call.tool) {
                "set_timer" -> {
                    val id = result["id"]?.jsonPrimitive?.contentOrNull ?: continue
                    val endsAt = result["ends_at"]?.jsonPrimitive?.contentOrNull ?: continue
                    val label = result["label"]?.jsonPrimitive?.contentOrNull
                    TimerAlarmScheduler.scheduleFromIso(context, id, label, endsAt)
                }

                "cancel_timer" -> {
                    val id = result["id"]?.jsonPrimitive?.contentOrNull ?: continue
                    TimerAlarmScheduler.cancel(context, id)
                }
            }
        }
    }
}
