# AppGuardianService Module

## Status: ❌ NOT IMPLEMENTED

Mini-game app gating not yet implemented. Requires PACKAGE_USAGE_STATS permission implementation.

## Purpose
Monitor app launches and trigger mini-games for gated apps using UsageStatsManager + overlay hijacking.

## How It Works
1. Poll `UsageStatsManager` to detect foreground app changes
2. When gated app is detected → emit `MiniGameTrigger` event
3. OverlayEngine shows fullscreen mini-game overlay
4. User completes mini-game → emit `MiniGameComplete` event
5. OverlayEngine hides overlay → underlying app is accessible

---

## Architecture

### AppGuardianService.kt
**Type**: Singleton object (not an Android Service, just a manager)

**Responsibilities**:
- Poll UsageStatsManager for foreground app changes
- Maintain list of gated apps
- Emit MiniGameTrigger when gated app launched
- Subscribe to MiniGameComplete events to track unlock state
- Respect permission state (pause monitoring if permission revoked)

**API**:
```kotlin
object AppGuardianService {
    private lateinit var context: Context
    private lateinit var usageStatsManager: UsageStatsManager

    private val gatedApps = mutableSetOf<String>() // Package names
    private var currentBlockedApp: String? = null
    private var lastForegroundApp: String? = null

    fun init(appContext: Context, scope: CoroutineScope) {
        context = appContext.applicationContext
        usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager

        // Load gated apps from storage
        scope.launch {
            gatedApps.addAll(loadGatedApps())
        }

        // Subscribe to permission changes
        scope.launch {
            StateStore.appState
                .map { it.permissions.usageStats }
                .distinctUntilChanged()
                .collect { granted ->
                    if (granted) {
                        startMonitoring(scope)
                    } else {
                        stopMonitoring()
                    }
                }
        }

        // Subscribe to MiniGameComplete events
        scope.launch {
            EventBus.events
                .filterIsInstance<AppEvent.MiniGameComplete>()
                .collect { event ->
                    if (event.success) {
                        handleMiniGameSuccess(event.targetApp)
                    }
                }
        }
    }

    private fun startMonitoring(scope: CoroutineScope) {
        scope.launch {
            while (isActive) {
                delay(500) // Poll every 500ms
                checkForegroundApp()
            }
        }
    }

    private fun stopMonitoring() {
        // Monitoring stops when coroutine scope is cancelled
    }

    private suspend fun checkForegroundApp() {
        val foregroundApp = getForegroundApp() ?: return

        // Skip if same app as before
        if (foregroundApp == lastForegroundApp) return
        lastForegroundApp = foregroundApp

        // Check if app is gated and not already blocked
        if (foregroundApp in gatedApps && currentBlockedApp != foregroundApp) {
            triggerMiniGame(foregroundApp)
        }
    }

    private fun getForegroundApp(): String? {
        val now = System.currentTimeMillis()
        val events = usageStatsManager.queryEvents(now - 1000, now)

        var lastEvent: UsageEvents.Event? = null
        while (events.hasNextEvent()) {
            val event = UsageEvents.Event()
            events.getNextEvent(event)

            if (event.eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
                lastEvent = event
            }
        }

        return lastEvent?.packageName
    }

    private suspend fun triggerMiniGame(appPackage: String) {
        currentBlockedApp = appPackage

        // Randomly select mini-game type
        val gameType = MiniGameType.values().random()

        EventBus.emit(AppEvent.MiniGameTrigger(gameType, appPackage))
    }

    private fun handleMiniGameSuccess(appPackage: String) {
        if (appPackage == currentBlockedApp) {
            currentBlockedApp = null
            // App is now accessible (overlay removed by OverlayEngine)
        }
    }

    fun addGatedApp(packageName: String) {
        gatedApps.add(packageName)
        saveGatedApps()
    }

    fun removeGatedApp(packageName: String) {
        gatedApps.remove(packageName)
        saveGatedApps()
    }

    fun getGatedApps(): Set<String> = gatedApps.toSet()

    private suspend fun loadGatedApps(): Set<String> = withContext(Dispatchers.IO) {
        // Load from DataStore/SharedPreferences
        // For now, return default set
        setOf(
            "com.instagram.android",
            "com.twitter.android",
            "com.reddit.frontpage"
        )
    }

    private fun saveGatedApps() {
        // Save to DataStore/SharedPreferences
    }
}
```

---

## UsageStatsManager API

### Required Permission
**PACKAGE_USAGE_STATS** — granted via Settings, not runtime

### Checking Permission
```kotlin
fun hasUsageStatsPermission(context: Context): Boolean {
    val appOps = context.getSystemService(Context.APP_OPS_SERVICE) as AppOpsManager
    val mode = appOps.checkOpNoThrow(
        AppOpsManager.OPSTR_GET_USAGE_STATS,
        android.os.Process.myUid(),
        context.packageName
    )
    return mode == AppOpsManager.MODE_ALLOWED
}
```

### Requesting Permission
```kotlin
fun requestUsageStatsPermission(context: Context) {
    val intent = Intent(Settings.ACTION_USAGE_ACCESS_SETTINGS).apply {
        flags = Intent.FLAG_ACTIVITY_NEW_TASK
    }
    context.startActivity(intent)
}
```

### Querying Foreground App
```kotlin
fun getForegroundApp(context: Context): String? {
    val usageStatsManager = context.getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
    val now = System.currentTimeMillis()

    val events = usageStatsManager.queryEvents(now - 1000, now)
    var lastResumedApp: String? = null

    while (events.hasNextEvent()) {
        val event = UsageEvents.Event()
        events.getNextEvent(event)

        if (event.eventType == UsageEvents.Event.ACTIVITY_RESUMED) {
            lastResumedApp = event.packageName
        }
    }

    return lastResumedApp
}
```

---

## Event Flow

### App Launch → Mini-Game → Unlock
```
1. User opens Instagram
2. AppGuardianService polls UsageStatsManager → detects "com.instagram.android"
3. AppGuardianService checks if Instagram is in gatedApps → yes
4. AppGuardianService.triggerMiniGame("com.instagram.android")
5. AppGuardianService emits MiniGameTrigger(QuickMath, "com.instagram.android")
6. StateStore updates appState.activeMiniGame = MiniGame(QuickMath, "com.instagram.android")
7. OverlayEngine subscribes → shows fullscreen math game overlay (blocks Instagram)
8. User solves 3 + 5 = 8
9. MiniGameOverlay emits MiniGameComplete(success = true, "com.instagram.android")
10. StateStore clears appState.activeMiniGame = null
11. OverlayEngine removes overlay → Instagram is now visible
12. AppGuardianService subscribes to MiniGameComplete → clears currentBlockedApp
```

---

## Gated Apps Management

### Settings UI
```kotlin
@Composable
fun GatedAppsSettings() {
    val gatedApps by remember { mutableStateOf(AppGuardianService.getGatedApps()) }
    val installedApps by remember { mutableStateOf(getInstalledApps()) }

    Column {
        Text("Select apps to gate:")

        LazyColumn {
            items(installedApps) { app ->
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(8.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Checkbox(
                        checked = app.packageName in gatedApps,
                        onCheckedChange = { checked ->
                            if (checked) {
                                AppGuardianService.addGatedApp(app.packageName)
                            } else {
                                AppGuardianService.removeGatedApp(app.packageName)
                            }
                        }
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(app.name)
                }
            }
        }
    }
}

data class InstalledApp(val name: String, val packageName: String)

fun getInstalledApps(context: Context): List<InstalledApp> {
    val pm = context.packageManager
    return pm.getInstalledApplications(PackageManager.GET_META_DATA)
        .filter { it.flags and ApplicationInfo.FLAG_SYSTEM == 0 } // User apps only
        .map { InstalledApp(it.loadLabel(pm).toString(), it.packageName) }
        .sortedBy { it.name }
}
```

---

## Overlay Hijacking Strategy

### Why This Works
- UsageStatsManager detects app launch
- OverlayEngine immediately draws fullscreen overlay
- User can only interact with mini-game overlay (underlying app is covered)
- Once mini-game complete, overlay removed → app accessible

### Preventing Bypass
**Problem**: User presses Home button → escapes mini-game

**Solution**: Re-detect app launch when user returns
```kotlin
private suspend fun checkForegroundApp() {
    val foregroundApp = getForegroundApp() ?: return

    // If user is returning to blocked app without completing mini-game
    if (foregroundApp == currentBlockedApp) {
        // Re-trigger mini-game
        triggerMiniGame(foregroundApp)
    }
}
```

**Problem**: User force-stops RealitySkin service

**Solution**: Use persistent notification + restart on boot
- Not foolproof, but good enough for self-imposed restrictions

---

## Mini-Game Selection Strategy

### Random Selection
```kotlin
val gameType = MiniGameType.values().random()
```

### Difficulty Progression
```kotlin
data class GameDifficulty(val level: Int)

fun selectGameByDifficulty(appUsageCount: Int): MiniGameType {
    return when {
        appUsageCount < 5 -> MiniGameType.QuickMath // Easy
        appUsageCount < 10 -> MiniGameType.ReactionTime // Medium
        else -> MiniGameType.MemoryMatch // Hard
    }
}
```

### Contextual Selection
```kotlin
fun selectGameByTimeOfDay(): MiniGameType {
    val hour = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
    return when (hour) {
        in 6..11 -> MiniGameType.QuickMath // Morning brain exercise
        in 12..17 -> MiniGameType.ReactionTime // Afternoon energy
        else -> MiniGameType.MemoryMatch // Evening wind-down
    }
}
```

---

## Performance Optimization

### Polling Interval
- 500ms is responsive but may drain battery
- Adjust based on user preference:
  - Aggressive: 250ms
  - Balanced: 500ms
  - Battery-saver: 1000ms

### Debouncing
```kotlin
private var debounceJob: Job? = null

private suspend fun checkForegroundApp() {
    debounceJob?.cancel()
    debounceJob = coroutineScope.launch {
        delay(100) // Debounce rapid app switches
        val foregroundApp = getForegroundApp()
        // ... rest of logic
    }
}
```

### Pause Monitoring When Not Needed
```kotlin
// Pause monitoring when screen is off
fun onScreenOff() {
    stopMonitoring()
}

fun onScreenOn(scope: CoroutineScope) {
    startMonitoring(scope)
}
```

---

## Edge Cases

### Multiple Quick App Switches
- User switches Instagram → Twitter → Instagram in < 1 second
- Solution: Debounce + track last blocked app

### Service Restart Mid-Game
- Service crashes while mini-game is showing
- On restart, restore state from StateStore
- If `activeMiniGame != null`, re-initialize monitoring

### Permission Revoked Mid-Session
- UsageStatsManager throws SecurityException
- PermissionManager detects permission lost
- AppGuardianService stops monitoring gracefully

---

## Testing

### Manual Test: Gating Flow
1. Add Instagram to gated apps
2. Grant PACKAGE_USAGE_STATS permission
3. Open Instagram
4. Verify mini-game overlay appears
5. Complete mini-game
6. Verify Instagram is now accessible

### Integration Test: Detection
```kotlin
@Test
fun `triggerMiniGame emits MiniGameTrigger event`() = runTest {
    val events = mutableListOf<AppEvent>()
    launch {
        EventBus.events.collect { events.add(it) }
    }

    AppGuardianService.triggerMiniGame("com.instagram.android")

    advanceUntilIdle()
    assertTrue(events.any { it is AppEvent.MiniGameTrigger })
}
```

---

## Privacy Considerations

### What Data Is Collected?
- Foreground app package name (not app content)
- Timestamp of app launch

### User Control
- User explicitly selects which apps to gate
- No telemetry sent to external servers
- All processing on-device

---

## Future Enhancements

### Time-Based Gating
- Gate Instagram only between 9am-5pm (work hours)
- Allow unrestricted access at night

### Usage Quota
- Allow 30 minutes of Instagram per day
- After quota exhausted, show mini-game every time

### App Groups
- Gate all social media apps as a group
- Gate all games as a group

### Whitelist Times
- Don't gate apps during weekends
- Don't gate during lunch break

---

## Alternative Implementation: WorkManager

Instead of polling, use WorkManager for periodic checks:

```kotlin
class AppMonitorWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val foregroundApp = getForegroundApp(applicationContext)
        if (foregroundApp in AppGuardianService.getGatedApps()) {
            AppGuardianService.triggerMiniGame(foregroundApp)
        }
        return Result.success()
    }
}

// Schedule periodic work (minimum interval: 15 minutes)
val workRequest = PeriodicWorkRequestBuilder<AppMonitorWorker>(15, TimeUnit.MINUTES).build()
WorkManager.getInstance(context).enqueue(workRequest)
```

**Note**: 15-minute minimum makes this unsuitable for real-time gating. Polling is better for this use case.

---

## Dependencies

- UsageStatsManager (Android framework)
- AppOpsManager (Android framework)
- Kotlin Coroutines
- EventBus (core module)
- StateStore (core module)
- OverlayEngine (overlay module)

---

## Files in This Module

- `AppGuardianService.kt` — Main app monitoring logic
- `GatedAppsManager.kt` — Gated apps storage/retrieval
- `UsageStatsHelper.kt` — UsageStatsManager utility functions
- `CLAUDE.md` — This file
