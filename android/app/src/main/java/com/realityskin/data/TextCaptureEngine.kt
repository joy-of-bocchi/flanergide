package com.realityskin.data

import android.annotation.SuppressLint
import android.content.Context
import android.util.Log
import com.flanergide.data.CapturedText
import com.realityskin.core.Permission
import com.realityskin.core.StateStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

/**
 * TextCaptureEngine - Manages in-memory text capture log.
 *
 * Coordinates text capture from AccessibilityService, applies redaction,
 * and provides query API for AI module.
 *
 * Note: StaticFieldLeak is suppressed because we explicitly store applicationContext,
 * which is safe to hold in a static reference (not tied to Activity lifecycle).
 */
@SuppressLint("StaticFieldLeak")
object TextCaptureEngine {
    private const val TAG = "TextCaptureEngine"
    private const val MAX_LOG_SIZE = 1000
    private const val IDLE_TIMEOUT_MS = 8000L  // 8 seconds of no typing = flush

    private lateinit var context: Context
    private lateinit var scope: CoroutineScope
    private val capturedTextLog = mutableListOf<CapturedText>()

    // Batching state
    private var currentBuffer = StringBuilder()
    private var currentAppPackage = ""
    private var lastActivityTime = 0L
    private var idleTimerJob: kotlinx.coroutines.Job? = null

    /**
     * Initialize TextCaptureEngine.
     * Subscribes to permission state to enable/disable capture.
     */
    fun init(appContext: Context, scope: CoroutineScope) {
        context = appContext.applicationContext
        this.scope = scope
        Log.i(TAG, "Initializing TextCaptureEngine (idle timeout: ${IDLE_TIMEOUT_MS}ms)")

        // Subscribe to accessibility permission state
        scope.launch {
            StateStore.appState
                .map { it.permissions.accessibilityService }
                .distinctUntilChanged()
                .collect { enabled ->
                    if (enabled) {
                        Log.i(TAG, "Accessibility service enabled - ready to capture text")
                    } else {
                        Log.w(TAG, "Accessibility service disabled - clearing log and buffer")
                        synchronized(this@TextCaptureEngine) {
                            flushBufferLocked()
                        }
                        clear()
                    }
                }
        }
    }

    /**
     * Add captured text to buffer. Batches by idle timeout instead of per-character logging.
     * Only emits to LogUploader when idle timeout expires.
     */
    fun addCapturedText(text: String, appPackage: String) {
        if (text.isBlank()) return

        // Apply context-aware redaction
        val redactedText = SensitiveDataRedactor.redactForApp(text, appPackage)

        // Skip if redaction resulted in generic placeholder (e.g., password manager activity)
        if (redactedText == "[PASSWORD_MANAGER_ACTIVITY]") {
            Log.d(TAG, "Skipping password manager activity")
            return
        }

        synchronized(this) {
            // App changed - flush previous buffer before starting new one
            if (currentAppPackage.isNotEmpty() && currentAppPackage != appPackage) {
                Log.d(TAG, "App changed from $currentAppPackage to $appPackage - flushing buffer")
                flushBufferLocked()
            }

            currentAppPackage = appPackage
            currentBuffer.append(redactedText)
            lastActivityTime = System.currentTimeMillis()

            Log.v(TAG, "Buffered text (${currentBuffer.length} chars, app: $appPackage)")
        }

        // Cancel previous timeout and schedule new one (outside synchronized block)
        idleTimerJob?.cancel()
        idleTimerJob = scope.launch {
            try {
                delay(IDLE_TIMEOUT_MS)
                // Check if still idle (no new activity in timeout period)
                synchronized(this@TextCaptureEngine) {
                    if (System.currentTimeMillis() - lastActivityTime >= IDLE_TIMEOUT_MS) {
                        Log.d(TAG, "Idle timeout triggered - flushing buffer")
                        flushBufferLocked()
                    }
                }
            } catch (e: kotlinx.coroutines.CancellationException) {
                // Timer was cancelled due to new activity - this is expected
            }
        }
    }

    /**
     * Flush buffered text to log and upload queue.
     * Must be called while holding the object lock.
     */
    private fun flushBufferLocked() {
        if (currentBuffer.isEmpty()) {
            return
        }

        val bufferedText = currentBuffer.toString()
        val appPackage = currentAppPackage

        // Add to in-memory log
        val capturedText = CapturedText(
            text = bufferedText,
            appPackage = appPackage,
            timestamp = System.currentTimeMillis()
        )

        capturedTextLog.add(capturedText)
        if (capturedTextLog.size > MAX_LOG_SIZE) {
            capturedTextLog.removeAt(0)
        }

        // Send to LogUploader for batched upload
        try {
            com.flanergide.data.LogUploader.addLog(capturedText)
            Log.i(TAG, "Flushed buffer: '${bufferedText.take(50)}...' from $appPackage (${bufferedText.length} chars)")
        } catch (e: Exception) {
            Log.w(TAG, "Failed to add log to uploader: ${e.message}")
        }

        // Clear buffer
        currentBuffer.clear()
        currentAppPackage = ""
    }

    /**
     * Get recent captured text for AI consumption.
     */
    fun getRecentText(limit: Int = 100): List<CapturedText> {
        synchronized(capturedTextLog) {
            return capturedTextLog.takeLast(limit)
        }
    }

    /**
     * Clear all captured text (called when service disabled).
     */
    fun clear() {
        synchronized(capturedTextLog) {
            capturedTextLog.clear()
        }
        Log.i(TAG, "Cleared text capture log")
    }

    /**
     * Get log size (for debugging).
     */
    fun getLogSize(): Int {
        synchronized(capturedTextLog) {
            return capturedTextLog.size
        }
    }
}
