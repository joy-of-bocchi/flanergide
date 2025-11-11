package com.realityskin.overlay

import android.annotation.SuppressLint
import android.content.Context
import android.graphics.PixelFormat
import android.util.Log
import android.view.Gravity
import android.view.WindowManager
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.ComposeView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import androidx.lifecycle.setViewTreeLifecycleOwner
import androidx.savedstate.SavedStateRegistry
import androidx.savedstate.SavedStateRegistryController
import androidx.savedstate.SavedStateRegistryOwner
import androidx.savedstate.setViewTreeSavedStateRegistryOwner
import com.realityskin.core.Message
import com.realityskin.core.OverlayType
import com.realityskin.core.StateStore
import com.realityskin.overlay.composables.ScrollingMessageOverlay
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

/**
 * OverlayEngine - Manages all system overlays using WindowManager + Compose.
 *
 * Responsibilities:
 * - Subscribe to StateStore for state changes
 * - Create/destroy overlay windows
 * - Render Nico-nico style scrolling messages
 * - Check permissions before showing overlays
 *
 * Note: StaticFieldLeak is suppressed because we explicitly use applicationContext,
 * which is safe to hold in a static reference (it's not tied to Activity lifecycle).
 */
@SuppressLint("StaticFieldLeak")
object OverlayEngine {
    private const val TAG = "OverlayEngine"
    private const val MAX_CONCURRENT_MESSAGES = 5

    private lateinit var windowManager: WindowManager
    private lateinit var context: Context

    // Track active message overlays
    private val activeOverlays = mutableListOf<ComposeView>()

    /**
     * Initialize OverlayEngine.
     * Subscribes to StateStore for message updates.
     */
    fun init(appContext: Context, scope: CoroutineScope) {
        context = appContext.applicationContext
        windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager

        Log.i(TAG, "Initializing OverlayEngine")

        // Subscribe to new messages
        scope.launch {
            StateStore.appState
                .map { it.recentMessages to it.permissions.systemAlertWindow }
                .distinctUntilChanged()
                .collect { (messages, hasPermission) ->
                    if (!hasPermission) {
                        Log.w(TAG, "SYSTEM_ALERT_WINDOW permission not granted, skipping overlay")
                        return@collect
                    }

                    // Show the most recent message if available
                    val latestMessage = messages.firstOrNull()
                    if (latestMessage != null) {
                        showScrollingMessage(latestMessage)
                    }
                }
        }

        // Subscribe to overlay visibility settings
        scope.launch {
            StateStore.appState
                .map { it.overlayVisibility[OverlayType.SCROLLING_MESSAGE] }
                .distinctUntilChanged()
                .collect { visible ->
                    if (visible == false) {
                        hideAllOverlays()
                    }
                }
        }
    }

    /**
     * Show a scrolling message overlay.
     * Creates a new overlay window with Nico-nico style animation.
     * Each message gets a random font via FontProvider.
     */
    fun showScrollingMessage(message: Message) {
        try {
            // Limit concurrent overlays
            if (activeOverlays.size >= MAX_CONCURRENT_MESSAGES) {
                Log.d(TAG, "Max concurrent messages reached, removing oldest")
                removeOldestOverlay()
            }

            Log.d(TAG, "Showing scrolling message: ${message.content.take(50)}...")

            val overlayView = createComposeOverlay { view ->
                ScrollingMessageOverlay(
                    message = message,
                    applicationContext = context
                )
            }

            windowManager.addView(overlayView, createScrollingMessageParams())
            activeOverlays.add(overlayView)

            Log.d(TAG, "Active overlays: ${activeOverlays.size}")

            // Auto-remove after 20 seconds (max animation time + buffer)
            kotlinx.coroutines.GlobalScope.launch {
                kotlinx.coroutines.delay(20_000)
                removeOverlay(overlayView)
            }
        } catch (e: SecurityException) {
            Log.e(TAG, "SecurityException: SYSTEM_ALERT_WINDOW permission revoked", e)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to show scrolling message", e)
        }
    }

    /**
     * Remove a specific overlay from the screen.
     */
    private fun removeOverlay(view: ComposeView) {
        try {
            if (activeOverlays.contains(view)) {
                windowManager.removeView(view)
                activeOverlays.remove(view)
                Log.d(TAG, "Removed overlay, remaining: ${activeOverlays.size}")
            }
        } catch (e: IllegalArgumentException) {
            // View wasn't attached, ignore
            Log.w(TAG, "Attempted to remove non-attached view")
        } catch (e: Exception) {
            Log.e(TAG, "Error removing overlay", e)
        }
    }

    /**
     * Remove the oldest overlay to make room for new ones.
     */
    private fun removeOldestOverlay() {
        if (activeOverlays.isNotEmpty()) {
            val oldest = activeOverlays.removeAt(0)
            try {
                windowManager.removeView(oldest)
            } catch (e: Exception) {
                Log.w(TAG, "Error removing oldest overlay", e)
            }
        }
    }

    /**
     * Hide all active overlays.
     */
    fun hideAllOverlays() {
        Log.i(TAG, "Hiding all overlays (${activeOverlays.size} active)")
        activeOverlays.toList().forEach { view ->
            try {
                windowManager.removeView(view)
            } catch (e: Exception) {
                Log.w(TAG, "Error removing overlay", e)
            }
        }
        activeOverlays.clear()
    }

    /**
     * Create a ComposeView for overlay rendering.
     */
    private fun createComposeOverlay(content: @Composable (ComposeView) -> Unit): ComposeView {
        return ComposeView(context).apply {
            // Create a simple lifecycle owner for the overlay
            val lifecycleOwner = MyLifecycleOwner()
            setViewTreeLifecycleOwner(lifecycleOwner)

            // Create saved state registry owner
            val savedStateRegistryOwner = MySavedStateRegistryOwner()
            setViewTreeSavedStateRegistryOwner(savedStateRegistryOwner)

            // Start the lifecycle
            lifecycleOwner.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
            lifecycleOwner.handleLifecycleEvent(Lifecycle.Event.ON_START)
            lifecycleOwner.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)

            setContent {
                content(this)
            }
        }
    }

    /**
     * Simple LifecycleOwner implementation for overlay windows.
     */
    private class MyLifecycleOwner : LifecycleOwner {
        private val lifecycleRegistry = LifecycleRegistry(this)

        override val lifecycle: Lifecycle
            get() = lifecycleRegistry

        fun handleLifecycleEvent(event: Lifecycle.Event) {
            lifecycleRegistry.handleLifecycleEvent(event)
        }
    }

    /**
     * Simple SavedStateRegistryOwner implementation.
     */
    private class MySavedStateRegistryOwner : SavedStateRegistryOwner {
        private val controller = SavedStateRegistryController.create(this)

        override val lifecycle: Lifecycle = LifecycleRegistry(this)

        override val savedStateRegistry: SavedStateRegistry
            get() = controller.savedStateRegistry

        init {
            controller.performRestore(null)
        }
    }

    /**
     * Create WindowManager.LayoutParams for scrolling message overlay.
     * - Allows touches to pass through (FLAG_NOT_TOUCHABLE)
     * - Doesn't steal focus (FLAG_NOT_FOCUSABLE)
     * - Positioned at top of screen with random offset
     */
    private fun createScrollingMessageParams(): WindowManager.LayoutParams {
        return WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                    or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                    or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            // Random vertical position (0-800px from top)
            y = (0..800).random()
        }
    }
}
