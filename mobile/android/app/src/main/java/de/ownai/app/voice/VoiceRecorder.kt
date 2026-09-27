package de.ownai.app.voice

import android.content.Context
import android.media.MediaRecorder
import android.os.Build
import java.io.File

/**
 * Thin wrapper around [MediaRecorder] that records a short voice clip to a temp file in
 * the app's cache dir, encoded as AAC-in-MP4 - supported natively on every Android
 * version back to API 26 with no extra codec setup. The backend decodes whatever format
 * arrives via ffmpeg (see API.md, POST /voice/transcribe), so the exact container format
 * here doesn't need to match anything server-side.
 *
 * Caller is responsible for the RECORD_AUDIO runtime permission before calling [start].
 */
class VoiceRecorder(private val context: Context) {

    val mimeType: String = "audio/mp4"

    private var recorder: MediaRecorder? = null
    private var outputFile: File? = null

    /** Starts recording. Returns false (and cleans up) if the recorder could not be started. */
    fun start(): Boolean {
        val file = File(context.cacheDir, "voice-${System.currentTimeMillis()}.m4a")
        val newRecorder = createRecorder()
        return try {
            newRecorder.apply {
                setAudioSource(MediaRecorder.AudioSource.MIC)
                setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
                setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
                setAudioSamplingRate(16000)
                setAudioEncodingBitRate(96000)
                setOutputFile(file.absolutePath)
                prepare()
                start()
            }
            recorder = newRecorder
            outputFile = file
            true
        } catch (e: Exception) {
            // IOException (prepare failed), IllegalStateException (wrong call order) or a
            // RuntimeException from start() on some OEM devices when the mic is busy -
            // all mean "couldn't record", handled identically by the caller either way.
            newRecorder.release()
            outputFile = null
            false
        }
    }

    /** Stops recording and returns the recorded file, or null if nothing usable was captured. */
    fun stop(): File? {
        val current = recorder ?: return null
        recorder = null
        return try {
            current.stop()
            outputFile
        } catch (e: RuntimeException) {
            // stop() throws if no audio was actually captured before stopping (e.g. cut off
            // immediately after start()) - nothing usable to send in that case.
            outputFile?.delete()
            null
        } finally {
            current.release()
        }
    }

    /** Aborts an in-progress recording without returning anything, discarding the temp file. */
    fun cancel() {
        val current = recorder
        recorder = null
        try {
            current?.stop()
        } catch (e: RuntimeException) {
            // discarding anyway
        }
        current?.release()
        outputFile?.delete()
        outputFile = null
    }

    @Suppress("DEPRECATION")
    private fun createRecorder(): MediaRecorder {
        return if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            MediaRecorder(context)
        } else {
            MediaRecorder()
        }
    }
}
