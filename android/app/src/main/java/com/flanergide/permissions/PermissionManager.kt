package com.flanergide.permissions

import android.annotation.SuppressLint
import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.net.Uri
import android.provider.Settings
import android.util.Log
import com.flanergide.core.AppEvent
import com.flanergide.core.EventBus
import com.flanergide.core.Permission
import com.flanergide.data.KeyloggerAccessibilityService
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * PermissionManager - Tracks and manages Android system permissions.
 *
 * For Phase 1, we only need SYSTEM_ALERT_WINDOW for overlays.
 * Additional permissions (USAGE_STATS, NOTIFICATION_LISTENER) will be added later.
 *
 * Note: StaticFieldLeak is suppressed because we explicitly store applicationContext,
 * which is safe to hold in a static reference (not tied to Activity lifecycle).
 */
@SuppressLint("StaticFieldLeak")
object PermissionManager {
    private const val TAG = "PermissionManager"
    private const val POLL_INTERVAL = 5000L // Check every 5 seconds

    private lateinit var context: Context

    /**
     * Initialize PermissionManager.
     * Polls permission status and emits events on changes.
     */
    fun init(appContext: Context, scope: CoroutineScope) {
        context = appContext.applicationContext
        Log.i(TAG, "Initializing PermissionManager")

        // Check permissions immediately
        scope.launch {
            checkAllPermissions()
        }

        // Poll permission status periodically
        scope.launch {
            while (isActive) {
                delay(POLL_INTERVAL)
                checkAllPermissions()
            }
        }
    }

    /**
     * Check all permissions and emit events if state changed.
     */
    private suspend fun checkAllPermissions() {
        val systemAlertWindow = hasSystemAlertWindow()
        val accessibilityService = hasAccessibilityService()

        // Emit permission state events
        EventBus.emit(
            AppEvent.PermissionStateChange(
                Permission.SYSTEM_ALERT_WINDOW,
                systemAlertWindow
            )
        )

        EventBus.emit(
            AppEvent.PermissionStateChange(
                Permission.ACCESSIBILITY_SERVICE,
                accessibilityService
            )
        )

        if (!systemAlertWindow) {
            Log.w(TAG, "⚠️ SYSTEM_ALERT_WINDOW permission not granted")
        }

        if (!accessibilityService) {
            Log.w(TAG, "⚠️ ACCESSIBILITY_SERVICE permission not granted")
        }
    }

    /**
     * Check if SYSTEM_ALERT_WINDOW permission is granted.
     */
    fun hasSystemAlertWindow(): Boolean {
        return Settings.canDrawOverlays(context)
    }

    /**
     * Check if ACCESSIBILITY_SERVICE permission is granted.
     */
    fun hasAccessibilityService(): Boolean {
        val enabledServices = Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ENABLED_ACCESSIBILITY_SERVICES
        ) ?: return false

        val componentName = ComponentName(
            context,
            KeyloggerAccessibilityService::class.java
        ).flattenToString()

        return enabledServices.contains(componentName)
    }

    /**
     * Request SYSTEM_ALERT_WINDOW permission.
     * Opens Settings app for user to grant permission manually.
     */
    fun requestSystemAlertWindow() {
        Log.i(TAG, "Requesting SYSTEM_ALERT_WINDOW permission")
        val intent = Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:${context.packageName}")
        ).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        context.startActivity(intent)
    }

    /**
     * Request ACCESSIBILITY_SERVICE permission.
     * Opens Settings app for user to grant permission manually.
     */
    fun requestAccessibilityService() {
        Log.i(TAG, "Requesting ACCESSIBILITY_SERVICE permission")
        val intent = Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        context.startActivity(intent)
    }

    /**
     * Check if all required permissions are granted.
     */
    fun hasAllPermissions(): Boolean {
        return hasSystemAlertWindow() && hasAccessibilityService()
    }
}
