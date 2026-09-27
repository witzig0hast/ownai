package de.ownai.app.voice

import android.content.Context
import android.speech.tts.TextToSpeech
import java.util.Locale

/**
 * Reads assistant replies aloud via Android's on-device [TextToSpeech] engine - free, no
 * server round-trip (see root DECISIONS.md: voice input goes through the user's own
 * self-hosted Whisper, but there's no reason for the reply-side to touch the network at
 * all when the OS already provides free, on-device TTS).
 *
 * Scoped to a single screen's lifecycle - construct in a `remember { }`, call [shutdown]
 * from a `DisposableEffect` cleanup so the engine is released when the screen leaves
 * composition.
 */
class SpeechReader(context: Context) {

    @Volatile
    private var isReady = false

    private lateinit var tts: TextToSpeech

    init {
        tts = TextToSpeech(context.applicationContext) { status ->
            isReady = status == TextToSpeech.SUCCESS
            if (isReady) {
                val result = tts.setLanguage(Locale.GERMAN)
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    tts.setLanguage(Locale.getDefault())
                }
            }
        }
    }

    fun speak(text: String) {
        if (!isReady || text.isBlank()) return
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, "ownai-reply")
    }

    fun stop() {
        if (isReady) tts.stop()
    }

    fun shutdown() {
        tts.stop()
        tts.shutdown()
    }
}
