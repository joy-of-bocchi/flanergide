package com.realityskin.data

import android.annotation.SuppressLint
import android.content.Context
import android.util.Log
import com.realityskin.core.Permission
import com.realityskin.core.StateStore
import kotlinx.coroutines.CoroutineScope
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

    private lateinit var context: Context
    private val capturedTextLog = mutableListOf<CapturedText>()

    /**
     * Initialize TextCaptureEngine.
     * Subscribes to permission state to enable/disable capture.
     */
    fun init(appContext: Context, scope: CoroutineScope) {
        context = appContext.applicationContext
        Log.i(TAG, "Initializing TextCaptureEngine")

        // Subscribe to accessibility permission state
        scope.launch {
            StateStore.appState
                .map { it.permissions.accessibilityService }
                .distinctUntilChanged()
                .collect { enabled ->
                    if (enabled) {
                        Log.i(TAG, "Accessibility service enabled - ready to capture text")
                    } else {
                        Log.w(TAG, "Accessibility service disabled - clearing log")
                        clear()
                    }
                }
        }
    }

    /**
     * Add captured text to log with redaction.
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

        // Create captured text entry
        val capturedText = CapturedText(
            text = redactedText,
            appPackage = appPackage,
            timestamp = System.currentTimeMillis()
        )

        synchronized(capturedTextLog) {
            // Add to log
            capturedTextLog.add(capturedText)

            // Maintain circular buffer (keep only last MAX_LOG_SIZE entries)
            if (capturedTextLog.size > MAX_LOG_SIZE) {
                capturedTextLog.removeAt(0)
            }
        }

        Log.d(TAG, "Captured text from $appPackage: ${redactedText.take(50)}...")
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
