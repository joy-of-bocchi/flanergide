package com.flanergide

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.flanergide.BuildConfig
import com.flanergide.ai.AIOrchestrator
import com.flanergide.core.StateStore
import com.flanergide.data.LogUploader
import com.flanergide.data.NetworkManager
import com.flanergide.data.TextCaptureEngine
import com.flanergide.overlay.OverlayEngine
import com.flanergide.permissions.PermissionManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking

/**
 * RealityService - Main foreground service that keeps RealitySkin alive.
 *
 * Responsibilities:
 * - Run as foreground service with persistent notification
 * - Initialize all modules (StateStore, AIOrchestrator, OverlayEngine, etc.)
 * - Coordinate permission checks
 * - Handle service lifecycle
 */
class RealityService : Service() {
    private val tag = "RealityService"
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val notificationChannelId = "flanergide_service"

    companion object {
        private const val NOTIFICATION_ID = 1001

        /**
         * Start the RealityService.
         */
        fun start(context: Context) {
            val intent = Intent(context, RealityService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        /**
         * Stop the RealityService.
         */
        fun stop(context: Context) {
            val intent = Intent(context, RealityService::class.java)
            context.stopService(intent)
        }
    }

    override fun onCreate() {
        super.onCreate()
        Log.i(tag, "🚀 RealityService starting...")

        // Create notification channel
        createNotificationChannel()

        // Start as foreground service
        startForeground(NOTIFICATION_ID, createNotification())

        // Initialize modules in order
        initializeModules()

        Log.i(tag, "✅ RealityService started successfully")
    }

    /**
     * Initialize all modules.
     */
    private fun initializeModules() {
        Log.i(tag, "Initializing modules...")

        // 1. Initialize StateStore (must be first - other modules depend on it)
        StateStore.init(serviceScope)
        Log.d(tag, "✓ StateStore initialized")

        // 2. Initialize PermissionManager (checks permissions and emits events)
        PermissionManager.init(applicationContext, serviceScope)
        Log.d(tag, "✓ PermissionManager initialized")

        // 3. Initialize NetworkManager (monitors network connectivity)
        NetworkManager.init(applicationContext, serviceScope)
        Log.d(tag, "✓ NetworkManager initialized")

        // 4. Initialize TextCaptureEngine (captures text from accessibility service)
        TextCaptureEngine.init(applicationContext, serviceScope)
        Log.d(tag, "✓ TextCaptureEngine initialized")

        // 5. Initialize LogUploader (batches and uploads captured text logs)
        LogUploader.init(applicationContext, serviceScope, BuildConfig.JWT_TOKEN)
        LogUploader.serverUrl = BuildConfig.SERVER_URL
        Log.d(tag, "✓ LogUploader initialized")
        Log.d(tag, "  Server: ${BuildConfig.SERVER_URL}")

        // 6. Initialize OverlayEngine (subscribes to state changes)
        OverlayEngine.init(applicationContext, serviceScope)
        Log.d(tag, "✓ OverlayEngine initialized")

        // 7. Initialize AIOrchestrator (loads model and starts generating messages)
        AIOrchestrator.init(applicationContext, serviceScope)
        Log.d(tag, "✓ AIOrchestrator initialized")

        Log.i(tag, "All modules initialized")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        Log.d(tag, "onStartCommand called")
        return START_STICKY // Restart service if killed
    }

    override fun onDestroy() {
        Log.i(tag, "🛑 RealityService stopping...")

        // Clean up overlays
        OverlayEngine.hideAllOverlays()

        // Clean up AI resources (blocking call since we're shutting down)
        runBlocking {
            AIOrchestrator.cleanup()
        }

        // Cancel coroutines
        serviceScope.cancel()

        super.onDestroy()
        Log.i(tag, "✅ RealityService stopped")
    }

    override fun onBind(intent: Intent?): IBinder? = null

    /**
     * Create notification channel for foreground service (Android 8+).
     */
    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                notificationChannelId,
                "RealitySkin Service",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Keeps RealitySkin overlays active"
                setShowBadge(false)
            }
            val notificationManager = getSystemService(NotificationManager::class.java)
            notificationManager.createNotificationChannel(channel)
            Log.d(tag, "Notification channel created")
        }
    }

    /**
     * Create persistent notification for foreground service.
     */
    private fun createNotification(): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this,
            0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )

        return NotificationCompat.Builder(this, notificationChannelId)
            .setContentTitle("RealitySkin Active")
            .setContentText("Tap to configure")
            .setSmallIcon(android.R.drawable.ic_dialog_info) // TODO: Replace with custom icon
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }
}
