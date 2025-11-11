# RealityService — Main Orchestrator

## Status: ✅ IMPLEMENTED (Phase 4)

## Current Implementation
- Foreground service with notification
- Initializes: StateStore, PermissionManager, OverlayEngine, AIOrchestrator
- Does NOT initialize: AppGuardianService, DataRepository (not implemented)
- FontProvider is stateless utility (no init needed)
- Does NOT persist/restore state (DataRepository not implemented)
- START_STICKY for automatic restart

## Purpose
Foreground service that keeps RealitySkin alive and initializes all modules.

---

## RealityService.kt
**Type**: Android Foreground Service

**Responsibilities**:
- Run as foreground service with persistent notification
- Initialize all modules on `onCreate()`
- Coordinate permission checks with PermissionManager
- Restore persisted state on startup
- Persist state on shutdown
- Handle service lifecycle (start/stop/restart)

---

## Implementation

```kotlin
class RealityService : Service() {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)
    private val notificationChannelId = "reality_skin_service"

    override fun onCreate() {
        super.onCreate()

        // Create notification channel (Android 8+)
        createNotificationChannel()

        // Start as foreground service
        startForeground(NOTIFICATION_ID, createNotification())

        // Initialize storage
        DataRepository.init(applicationContext)

        // Restore persisted state
        serviceScope.launch {
            StateStore.restoreState(DataRepository)
        }

        // Initialize core modules
        StateStore.init(serviceScope)
        EventBus // Singleton, no init needed

        // Initialize other modules
        PermissionManager.init(applicationContext, serviceScope)
        // FontProvider is stateless, no init needed
        OverlayEngine.init(applicationContext, serviceScope)
        AIOrchestrator.init(applicationContext, serviceScope)
        AppGuardianService.init(applicationContext, serviceScope)

        // Periodic auto-save
        serviceScope.launch {
            while (isActive) {
                delay(60_000) // Every 60 seconds
                StateStore.persistState(DataRepository)
            }
        }

        // Show onboarding if permissions missing
        serviceScope.launch {
            StateStore.appState
                .map { it.permissions }
                .distinctUntilChanged()
                .collect { permissions ->
                    if (!permissions.allGranted()) {
                        showPermissionOnboarding()
                    }
                }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY // Restart service if killed
    }

    override fun onDestroy() {
        // Persist state before shutdown
        runBlocking {
            StateStore.persistState(DataRepository)
        }

        // Clean up overlays
        OverlayEngine.hideAllOverlays()

        // Cancel coroutines
        serviceScope.cancel()

        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

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
        }
    }

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
            .setSmallIcon(R.drawable.ic_notification)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun showPermissionOnboarding() {
        val intent = Intent(this, OnboardingActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        startActivity(intent)
    }

    companion object {
        private const val NOTIFICATION_ID = 1001

        fun start(context: Context) {
            val intent = Intent(context, RealityService::class.java)
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                context.startForegroundService(intent)
            } else {
                context.startService(intent)
            }
        }

        fun stop(context: Context) {
            val intent = Intent(context, RealityService::class.java)
            context.stopService(intent)
        }
    }
}

fun PermissionState.allGranted() = systemAlertWindow && usageStats && notificationListener
```

---

## AndroidManifest.xml

```xml
<manifest xmlns:android="http://schemas.android.com/apk/res/android"
    package="com.realityskin">

    <!-- Permissions -->
    <uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
    <uses-permission android:name="android.permission.PACKAGE_USAGE_STATS"
        tools:ignore="ProtectedPermissions" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
    <uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
    <uses-permission android:name="android.permission.INTERNET" /> <!-- For downloading fonts -->

    <application
        android:name=".RealitySkinApplication"
        android:allowBackup="true"
        android:icon="@mipmap/ic_launcher"
        android:label="@string/app_name"
        android:theme="@style/Theme.RealitySkin">

        <!-- Main Activity -->
        <activity
            android:name=".MainActivity"
            android:exported="true"
            android:theme="@style/Theme.RealitySkin">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>

        <!-- Onboarding Activity -->
        <activity
            android:name=".OnboardingActivity"
            android:exported="false"
            android:theme="@style/Theme.RealitySkin" />

        <!-- Foreground Service -->
        <service
            android:name=".RealityService"
            android:enabled="true"
            android:exported="false"
            android:foregroundServiceType="specialUse">
            <property
                android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE"
                android:value="overlay" />
        </service>

        <!-- Notification Listener Service -->
        <service
            android:name=".ai.RealityNotificationListener"
            android:exported="true"
            android:permission="android.permission.BIND_NOTIFICATION_LISTENER_SERVICE">
            <intent-filter>
                <action android:name="android.service.notification.NotificationListenerService" />
            </intent-filter>
        </service>

        <!-- Boot Receiver (optional, for auto-start) -->
        <receiver
            android:name=".BootReceiver"
            android:enabled="true"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
            </intent-filter>
        </receiver>
    </application>
</manifest>
```

---

## MainActivity.kt

```kotlin
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            RealitySkinTheme {
                MainScreen()
            }
        }

        // Start service if not already running
        RealityService.start(this)
    }
}

@Composable
fun MainScreen() {
    val appState by StateStore.appState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("RealitySkin") })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
        ) {
            Text("Service Status: Active", style = MaterialTheme.typography.h6)

            Spacer(modifier = Modifier.height(16.dp))

            Button(onClick = {
                // Navigate to settings
            }) {
                Text("Settings")
            }

            Spacer(modifier = Modifier.height(16.dp))

            PermissionStatusCard(appState.permissions)
        }
    }
}

@Composable
fun PermissionStatusCard(permissions: PermissionState) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text("Permissions", style = MaterialTheme.typography.h6)
            Spacer(modifier = Modifier.height(8.dp))

            PermissionRow("Draw over apps", permissions.systemAlertWindow)
            PermissionRow("Usage access", permissions.usageStats)
            PermissionRow("Notification access", permissions.notificationListener)
        }
    }
}

@Composable
fun PermissionRow(name: String, granted: Boolean) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(name)
        Text(if (granted) "✅" else "❌", color = if (granted) Color.Green else Color.Red)
    }
}
```

---

## OnboardingActivity.kt

```kotlin
class OnboardingActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            RealitySkinTheme {
                OnboardingScreen()
            }
        }
    }
}

@Composable
fun OnboardingScreen() {
    val appState by StateStore.appState.collectAsState()
    val permissions = appState.permissions

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Setup RealitySkin") })
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp)
        ) {
            Text(
                "RealitySkin needs these permissions to work:",
                style = MaterialTheme.typography.h6
            )

            Spacer(modifier = Modifier.height(16.dp))

            PermissionCard(
                name = "Draw over other apps",
                description = "Show overlays on top of other apps",
                granted = permissions.systemAlertWindow,
                onGrant = { PermissionManager.requestSystemAlertWindow() }
            )

            Spacer(modifier = Modifier.height(8.dp))

            PermissionCard(
                name = "Usage access",
                description = "Detect which app you're using",
                granted = permissions.usageStats,
                onGrant = { PermissionManager.requestUsageStats() }
            )

            Spacer(modifier = Modifier.height(8.dp))

            PermissionCard(
                name = "Notification access",
                description = "Read notifications for AI messages",
                granted = permissions.notificationListener,
                onGrant = { PermissionManager.requestNotificationListener() }
            )

            Spacer(modifier = Modifier.height(24.dp))

            if (permissions.allGranted()) {
                Text(
                    "✅ All permissions granted! You're ready to go.",
                    style = MaterialTheme.typography.body1,
                    color = Color.Green
                )

                Spacer(modifier = Modifier.height(16.dp))

                Button(
                    onClick = { finish() },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Done")
                }
            }
        }
    }
}

@Composable
fun PermissionCard(name: String, description: String, granted: Boolean, onGrant: () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier
                .padding(16.dp)
                .fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(name, style = MaterialTheme.typography.subtitle1)
                Text(description, style = MaterialTheme.typography.body2, color = Color.Gray)
            }

            if (granted) {
                Text("✅", fontSize = 24.sp)
            } else {
                Button(onClick = onGrant) {
                    Text("Grant")
                }
            }
        }
    }
}
```

---

## BootReceiver.kt (Optional)

Auto-start service on device boot:

```kotlin
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED) {
            RealityService.start(context)
        }
    }
}
```

**Manifest permission**:
```xml
<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />
```

---

## Application Class

```kotlin
class RealitySkinApplication : Application() {
    override fun onCreate() {
        super.onCreate()

        // Initialize any app-wide singletons here
        // DataRepository.init() will be called by RealityService
    }
}
```

---

## Service Lifecycle

### Start Flow
```
1. User opens app → MainActivity.onCreate()
2. MainActivity calls RealityService.start()
3. System calls RealityService.onCreate()
4. Service starts as foreground with notification
5. Service initializes all modules
6. Service restores persisted state
7. Modules begin subscribing to StateStore
8. Overlays appear (if permissions granted)
```

### Stop Flow
```
1. User stops service (Settings or MainActivity button)
2. System calls RealityService.onDestroy()
3. Service persists current state
4. Service hides all overlays
5. Service cancels coroutines
6. Service stops
```

### Crash Recovery
```
1. Service crashes unexpectedly
2. Android restarts service (START_STICKY)
3. Service.onCreate() called again
4. Service restores last persisted state
5. Modules reinitialize with restored state
6. Overlays reappear
```

---

## Testing

### Manual Test: Service Start
1. Install app
2. Open app
3. Verify notification appears
4. Verify service shows in Settings → Running Services

### Manual Test: Permission Flow
1. Open app (permissions not granted)
2. Verify OnboardingActivity opens
3. Grant all permissions
4. Verify overlays appear

### Manual Test: Service Restart
1. Force stop app from Settings
2. Re-open app
3. Verify previous state restored (font, avatar mood, etc.)

---

## Dependencies

- Jetpack Compose
- Kotlin Coroutines
- Android Foreground Service
- NotificationCompat
- All module dependencies

---

## Files in This Module

- `RealityService.kt` — Foreground service
- `MainActivity.kt` — Main app entry point
- `OnboardingActivity.kt` — Permission setup screen
- `BootReceiver.kt` — Auto-start on boot
- `RealitySkinApplication.kt` — Application class
- `CLAUDE.md` — This file
