package de.ownai.app.ui.notifications

import android.Manifest
import android.content.Intent
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.unit.dp
import androidx.core.app.NotificationManagerCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import de.ownai.app.ui.common.LogoutAction

/**
 * Explains, and links to, the one Android system permission that cannot be
 * requested through the normal runtime-permission dialog: notification
 * access for [de.ownai.app.notification.NotificationForwardingService].
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NotificationAccessScreen(onLogout: () -> Unit) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current

    var isListenerEnabled by remember { mutableStateOf(isNotificationListenerEnabled(context)) }

    // Re-check every time the user comes back from system Settings.
    DisposableEffect(lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            if (event == Lifecycle.Event.ON_RESUME) {
                isListenerEnabled = isNotificationListenerEnabled(context)
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
    }

    val postNotificationsLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { /* no-op: OwnAI does not post local notifications today, see manifest comment */ }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Notification access") },
                actions = { LogoutAction(onLogout) }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(20.dp)
                .verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(
                text = if (isListenerEnabled) "Notification access is granted." else "Notification access is not granted yet.",
                style = MaterialTheme.typography.titleLarge
            )

            Text(
                text = "OwnAI's core Android feature reads notifications posted by your other apps " +
                    "(WhatsApp, SMS, etc.), and forwards the relevant ones to your self-hosted backend, " +
                    "which uses the assistant to suggest things like adding a calendar event. " +
                    "This requires a special system permission - \"Notification access\" - that Android " +
                    "only lets you grant from Settings, not from an in-app permission dialog.",
                style = MaterialTheme.typography.bodyLarge
            )

            Card {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(text = "What gets sent", style = MaterialTheme.typography.titleLarge)
                    Text(
                        text = "For each relevant notification: the source app, its title and text, and " +
                            "when it was posted. Your own OwnAI notifications, and silent/ongoing system " +
                            "notifications (e.g. music controls), are filtered out on-device before anything " +
                            "is sent. See the app's README for the exact filtering rules.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }

            Button(
                onClick = {
                    context.startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
                }
            ) {
                Text(if (isListenerEnabled) "Open notification access settings" else "Grant notification access")
            }

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Android 13+ also requires permission for OwnAI to show its own notifications " +
                        "(not used yet, reserved for future features).",
                    style = MaterialTheme.typography.bodyMedium
                )
                Button(onClick = { postNotificationsLauncher.launch(Manifest.permission.POST_NOTIFICATIONS) }) {
                    Text("Allow OwnAI notifications")
                }
            }

            Card {
                Column(modifier = Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(text = "About SMS", style = MaterialTheme.typography.titleLarge)
                    Text(
                        text = "Incoming SMS already reaches OwnAI the same way as any other app's " +
                            "notification, as long as your messaging app posts a notification for it (the " +
                            "default on Android). Reading raw SMS content directly - e.g. while notifications " +
                            "are muted - would require this app to become your phone's default SMS handler, " +
                            "which is out of scope for v1. See the README for details.",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
            }
        }
    }
}

private fun isNotificationListenerEnabled(context: android.content.Context): Boolean {
    val enabledPackages = NotificationManagerCompat.getEnabledListenerPackages(context)
    return enabledPackages.contains(context.packageName)
}
