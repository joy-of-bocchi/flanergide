# PermissionManager Module

## Status: ✅ IMPLEMENTED (Phase 4)

## Current Implementation
- ✅ SYSTEM_ALERT_WINDOW checking (5-second polling)
- ❌ PACKAGE_USAGE_STATS checking (not implemented)
- ❌ BIND_NOTIFICATION_LISTENER_SERVICE checking (not implemented)
- Emits PermissionStateChange events to EventBus
- Provides requestSystemAlertWindow() helper

## Purpose
Centralized management of Android system permissions required by RealitySkin.

## Required Permissions

### 1. SYSTEM_ALERT_WINDOW ✅
**Purpose**: Draw overlays over other apps

**How to Request**:
```kotlin
val intent = Intent(
    Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
    Uri.parse("package:$packageName")
)
startActivity(intent)
```

**How to Check**:
```kotlin
Settings.canDrawOverlays(context)
```

**Failure Impact**: Cannot show scrolling messages, avatar, or mini-game overlays

---

### 2. PACKAGE_USAGE_STATS
**Purpose**: Detect which app is currently in foreground

**How to Request**:
```kotlin
val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS)
startActivity(intent)
```

**How to Check**:
```kotlin
val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
val mode = appOps.checkOpNoThrow(
    AppOpsManager.OPSTR_GET_USAGE_STATS,
    android.os.Process.myUid(),
    context.packageName
)
mode == AppOpsManager.MODE_ALLOWED
```

**Failure Impact**: AppGuardianService cannot detect app launches, no mini-game gating

---

### 3. BIND_NOTIFICATION_LISTENER_SERVICE
**Purpose**: Read incoming notifications for AI persona processing

**How to Request**:
```kotlin
val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
startActivity(intent)
```

**How to Check**:
```kotlin
val enabledListeners = Settings.Secure.getString(
    contentResolver,
    "enabled_notification_listeners"
)
enabledListeners?.contains(componentName.flattenToString()) == true
```

**Failure Impact**: AI cannot generate messages from notifications

---

## Architecture

### PermissionManager.kt
**Type**: Singleton object

**Responsibilities**:
- Check current status of all permissions
- Emit `PermissionStateChange` events when permissions change
- Provide helpers to launch Settings screens
- Poll permission status periodically (since Android doesn't broadcast changes)

**API**:
```kotlin
object PermissionManager {
    private lateinit var context: Context

    fun init(appContext: Context, scope: CoroutineScope) {
        context = appContext.applicationContext

        // Check permissions on startup
        scope.launch {
            checkAllPermissions()
        }

        // Poll permission status every 5 seconds
        scope.launch {
            while (isActive) {
                delay(5000)
                checkAllPermissions()
            }
        }
    }

    private suspend fun checkAllPermissions() {
        val systemAlertWindow = hasSystemAlertWindow()
        val usageStats = hasUsageStats()
        val notificationListener = hasNotificationListener()

        // Emit events if state changed
        EventBus.emit(AppEvent.PermissionStateChange(
            Permission.SYSTEM_ALERT_WINDOW,
            systemAlertWindow
        ))
        EventBus.emit(AppEvent.PermissionStateChange(
            Permission.USAGE_STATS,
            usageStats
        ))
        EventBus.emit(AppEvent.PermissionStateChange(
            Permission.NOTIFICATION_LISTENER,
            notificationListener
        ))
    }

    fun hasSystemAlertWindow(): Boolean {
        return Settings.canDrawOverlays(context)
    }

    fun hasUsageStats(): Boolean {
        val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
        val mode = appOps.checkOpNoThrow(
            AppOpsManager.OPSTR_GET_USAGE_STATS,
            android.os.Process.myUid(),
            context.packageName
        )
        return mode == AppOpsManager.MODE_ALLOWED
    }

    fun hasNotificationListener(): Boolean {
        val enabledListeners = Settings.Secure.getString(
            context.contentResolver,
            "enabled_notification_listeners"
        ) ?: return false
        val componentName = ComponentName(
            context,
            RealityNotificationListener::class.java
        )
        return enabledListeners.contains(componentName.flattenToString())
    }

    fun requestSystemAlertWindow() {
        val intent = Intent(
            Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
            Uri.parse("package:${context.packageName}")
        ).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        context.startActivity(intent)
    }

    fun requestUsageStats() {
        val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        context.startActivity(intent)
    }

    fun requestNotificationListener() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        context.startActivity(intent)
    }

    fun hasAllPermissions(): Boolean {
        return hasSystemAlertWindow() && hasUsageStats() && hasNotificationListener()
    }
}
```

---

## Event Flow

### Permission Granted Flow
```
1. User navigates to Settings and grants permission
2. PermissionManager polling detects permission granted
3. PermissionManager emits PermissionStateChange(SYSTEM_ALERT_WINDOW, true)
4. StateStore updates appState.permissions.systemAlertWindow = true
5. OverlayEngine subscribes to appState.permissions → sees permission granted
6. OverlayEngine starts showing overlays
```

### Permission Revoked Flow
```
1. User revokes permission in Settings
2. PermissionManager polling detects permission revoked
3. PermissionManager emits PermissionStateChange(SYSTEM_ALERT_WINDOW, false)
4. StateStore updates appState.permissions.systemAlertWindow = false
5. OverlayEngine sees permission lost → gracefully hides overlays
6. Optional: Show notification asking user to re-enable
```

---

## Integration with RealityService

```kotlin
class RealityService : Service() {
    override fun onCreate() {
        super.onCreate()

        // Initialize PermissionManager
        PermissionManager.init(applicationContext, serviceScope)

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

    private fun showPermissionOnboarding() {
        // Launch onboarding Activity or show persistent notification
        val intent = Intent(this, OnboardingActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        startActivity(intent)
    }
}
```

---

## Onboarding UI Example

```kotlin
@Composable
fun PermissionOnboardingScreen() {
    val appState by StateStore.appState.collectAsState()
    val permissions = appState.permissions

    Column(modifier = Modifier.padding(16.dp)) {
        Text("RealitySkin needs these permissions to work:")

        PermissionItem(
            name = "Draw over other apps",
            granted = permissions.systemAlertWindow,
            onRequest = { PermissionManager.requestSystemAlertWindow() }
        )

        PermissionItem(
            name = "Usage access",
            granted = permissions.usageStats,
            onRequest = { PermissionManager.requestUsageStats() }
        )

        PermissionItem(
            name = "Notification access",
            granted = permissions.notificationListener,
            onRequest = { PermissionManager.requestNotificationListener() }
        )

        if (permissions.allGranted()) {
            Text("✅ All permissions granted! You're ready to go.")
        }
    }
}

@Composable
fun PermissionItem(name: String, granted: Boolean, onRequest: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        horizontalArrangement = Arrangement.SpaceBetween
    ) {
        Text(name)
        if (granted) {
            Text("✅", color = Color.Green)
        } else {
            Button(onClick = onRequest) {
                Text("Grant")
            }
        }
    }
}

fun PermissionState.allGranted() = systemAlertWindow && usageStats && notificationListener
```

---

## Graceful Degradation

Modules should check permissions before performing sensitive actions:

### OverlayEngine Example
```kotlin
lifecycleScope.launch {
    StateStore.appState.collect { state ->
        if (state.permissions.systemAlertWindow) {
            // Safe to show overlays
            showScrollingMessage(state.recentMessages.first())
        } else {
            // Hide overlays gracefully
            hideAllOverlays()
        }
    }
}
```

### AppGuardianService Example
```kotlin
fun startMonitoring() {
    lifecycleScope.launch {
        StateStore.appState
            .map { it.permissions.usageStats }
            .distinctUntilChanged()
            .collect { granted ->
                if (granted) {
                    startPollingUsageStats()
                } else {
                    stopPollingUsageStats()
                }
            }
    }
}
```

---

## Testing

### Unit Test: Permission Checking
```kotlin
@Test
fun `hasSystemAlertWindow returns true when granted`() {
    // Mock Settings.canDrawOverlays() to return true
    assertTrue(PermissionManager.hasSystemAlertWindow())
}
```

### Integration Test: Permission Change Event
```kotlin
@Test
fun `emits event when permission state changes`() = runTest {
    val events = mutableListOf<AppEvent>()
    launch {
        EventBus.events.collect { events.add(it) }
    }

    PermissionManager.checkAllPermissions()

    advanceUntilIdle()
    assertTrue(events.any { it is AppEvent.PermissionStateChange })
}
```

---

## Edge Cases

### User Grants Then Immediately Revokes
- Polling interval (5s) means delay in detection
- Modules should handle permission loss gracefully (overlays may crash, catch SecurityException)

### Battery Optimization Kills Service
- On restart, PermissionManager re-checks all permissions
- StateStore restores last known state, then updates with current reality

### Permission Already Granted on Install
- First poll detects permission, emits event
- StateStore updates from default `false` to `true`

---

## Dependencies

- Android Settings API
- Android AppOpsManager
- Kotlin Coroutines
- EventBus (core module)
- StateStore (core module)

---

## Files in This Module

- `PermissionManager.kt` — Permission checker and requester
- `RealityNotificationListener.kt` — NotificationListenerService implementation
- `CLAUDE.md` — This file
