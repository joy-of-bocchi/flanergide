# Flanergide - Quick Reference Guide

## App Overview
- **Type**: On-device LLM overlay app
- **Model**: Phi-2 Q4_K_M (1.6 GB quantized)
- **Architecture**: Event-driven + State management
- **Language**: Kotlin (100%)
- **Min SDK**: 33 (Android 13)
- **Target SDK**: 34 (Android 14)

---

## Core Components

### Services
1. **RealityService** - Foreground service orchestrator
   - Runs persistently in background
   - Initializes StateStore → PermissionManager → OverlayEngine → AIOrchestrator
   - Handles cleanup on shutdown

### Activities
1. **MainActivity** - Launcher UI
   - Shows service status
   - Displays permissions
   - Requests SYSTEM_ALERT_WINDOW permission

### Modules (Singleton Objects)
1. **StateStore** - Central state (StateFlow)
2. **EventBus** - Event broadcast (SharedFlow)
3. **AIOrchestrator** - LLM inference
4. **OverlayEngine** - Jetpack Compose overlay rendering
5. **PermissionManager** - Permission polling (5sec interval)
6. **FontProvider** - Random font selection per message

---

## Current Permissions (2024)

| Permission | Used | Why |
|-----------|------|-----|
| SYSTEM_ALERT_WINDOW | ✅ | Draw floating overlays |
| FOREGROUND_SERVICE | ✅ | Keep service alive |
| FOREGROUND_SERVICE_SPECIAL_USE | ✅ | Declare overlay use |
| POST_NOTIFICATIONS | ✅ | Foreground notification |

**Total Permissions**: 4

---

## Readily Accessible Data (Not Yet Implemented)

### Immediate (No New Permissions)
- Device model, OS version
- System time
- Display metrics
- System fonts

### High Priority (1-2 Permission Additions)
- **Running app** (USAGE_STATS) - Currently running foreground app
- **Notifications** (NOTIFICATION_LISTENER) - SMS, messages, social media
- **Clipboard** (READ_CLIPBOARD_CONTENT) - Recently copied text

### Medium Priority (ContentProvider Additions)
- **Contacts** (READ_CONTACTS) - Names, phone numbers
- **Calendar** (READ_CALENDAR) - Events, schedules
- **Messages** (READ_SMS) - SMS text and metadata
- **Call Log** (READ_CALL_LOG) - Call history

### Lower Priority (Complex Integration)
- **Location** (ACCESS_FINE_LOCATION) - GPS coordinates
- **Phone State** (READ_PHONE_STATE) - Call status, network info

---

## Data Flow Architecture

```
Prompts Array
     ↓
AIOrchestrator (LLM Inference)
     ↓
EventBus.emit(NewMessage)
     ↓
StateStore.reduce() [updates recentMessages]
     ↓
OverlayEngine (observes state)
     ↓
ScrollingMessageOverlay (Compose rendering)
     ↓
WindowManager.addView() (displays on screen)
     ↓
Auto-remove after 20 seconds
```

---

## Key File Structure

```
app/src/main/
├── java/com/realityskin/
│   ├── MainActivity.kt          ← Launcher activity
│   ├── RealityService.kt        ← Foreground service
│   ├── core/
│   │   ├── EventBus.kt          ← Event broadcast
│   │   ├── StateStore.kt        ← Central state
│   │   ├── Events.kt            ← Event definitions
│   │   └── AppState.kt          ← State models
│   ├── ai/
│   │   ├── AIOrchestrator.kt    ← LLM orchestration
│   │   ├── GGUFModel.kt         ← Model loading/inference
│   │   ├── MLModel.kt           ← Model interface
│   │   └── MessageGenerator.kt  ← Prompt generation
│   ├── overlay/
│   │   ├── OverlayEngine.kt     ← WindowManager integration
│   │   └── composables/
│   │       └── ScrollingMessageOverlay.kt  ← Compose UI
│   ├── permissions/
│   │   └── PermissionManager.kt ← Permission polling
│   └── fonts/
│       └── FontProvider.kt      ← Font loading
├── res/
│   ├── values/strings.xml
│   ├── values/colors.xml
│   └── ...
└── AndroidManifest.xml
```

---

## Integration Points for Data Sources

### Adding USAGE_STATS Permission
1. Add permission to AndroidManifest.xml
2. Create UsageStatsManager wrapper in PermissionManager
3. Create event: `AppEvent.AppContextChange(packageName: String)`
4. Emit on change, reduce in StateStore
5. Pass to AIOrchestrator for contextual prompts

### Adding NOTIFICATION_LISTENER_SERVICE
1. Extend NotificationListenerService
2. Create event: `AppEvent.NotificationReceived(title, text, packageName)`
3. Subscribe in StateStore
4. Trigger contextual message generation

### Adding Calendar Access
1. Add READ_CALENDAR permission
2. Query CalendarContract.Events
3. Create event: `AppEvent.CalendarEventDetected(title, time)`
4. Use for time-aware message triggers

---

## Module Initialization Order

```
RealityService.onCreate()
├─ createNotificationChannel()
├─ startForeground(notification)
└─ initializeModules()
   ├─1. StateStore.init(scope)
   │   └─ Starts listening to EventBus
   │
   ├─2. PermissionManager.init(context, scope)
   │   └─ Polls permissions every 5 seconds
   │
   ├─3. OverlayEngine.init(context, scope)
   │   └─ Subscribes to state changes
   │
   └─4. AIOrchestrator.init(context, scope)
       └─ Loads model and starts generation loop
           └─ Generates message every 10-30 seconds
```

**Critical**: Order matters! StateStore must initialize first.

---

## Logging & Debugging

All major operations log with TAG:
- `StateStore`: State changes
- `EventBus`: Event emissions
- `AIOrchestrator`: Model loading, generation
- `GGUFModel`: Model file operations
- `OverlayEngine`: Overlay lifecycle
- `PermissionManager`: Permission checks

**View logs**: `adb logcat | grep -E "StateStore|AIOrchestrator|OverlayEngine"`

---

## Performance Notes

| Operation | Time | Notes |
|-----------|------|-------|
| Model load | 5-10s | First time copy + load |
| Model load (cached) | 2-3s | Model already in storage |
| Inference | 2-5s | Varies with prompt complexity |
| Overlay render | <100ms | Jetpack Compose |
| Total startup | ~15-20s | First run includes model copy |

---

## Data Ingestion Checklist

### Phase 1 (Current - 2024)
- [x] On-device LLM inference
- [x] SYSTEM_ALERT_WINDOW permission
- [x] Foreground service persistence
- [x] EventBus messaging
- [x] StateStore state management

### Phase 2 (Ready to Implement)
- [ ] USAGE_STATS - App context detection
- [ ] NOTIFICATION_LISTENER - Reactive messages
- [ ] READ_CONTACTS - Personalization
- [ ] READ_CALENDAR - Time-aware messages

### Phase 3 (Future)
- [ ] Location integration
- [ ] SMS/Message context
- [ ] Machine learning on usage patterns
- [ ] Backend API integration

---

## Security & Privacy Status

✅ **Protected**:
- No internet access
- No cloud data
- No external API calls
- App-private storage for model
- Signature-level custom permissions

⚠️ **Monitor**:
- Verbose logging (strip in release)
- Debuggable flag enabled (disable in release)
- No obfuscation (enable ProGuard/R8)
- Logcat access by default (secure adb)

---

## Testing Notes

- Unit tests: `app/src/test/java/com/example/realityskin/ExampleUnitTest.kt` (stub)
- Integration tests: `app/src/androidTest/java/com/example/realityskin/ExampleInstrumentedTest.kt` (stub)
- No actual tests implemented yet
- No analytics integration

---

## References

- **Full Analysis**: See `CODEBASE_ANALYSIS.md`
- **Architecture Docs**: `android/CLAUDE.md` (in previous commit)
- **Build Verification**: `android/BUILD_VERIFICATION.md`
- **Root README**: `README.md`

---

## Quick Command Reference

```bash
# Build
cd android && ./gradlew build

# Run on device
./gradlew installDebug

# View logs
adb logcat | grep -E "RealityService|AIOrchestrator|OverlayEngine"

# Check manifest
aapt dump permissions app/build/outputs/apk/debug/*.apk

# Check model file location (device)
adb shell ls -lh /data/data/com.flanergide/files/models/
```

---

## File Size Breakdown

| Component | Size | Notes |
|-----------|------|-------|
| Phi-2 model file | 1.6 GB | Stored in internal storage after first copy |
| APK size | ~200 MB | Includes precompiled llama.cpp natives |
| Source code | ~50 KB | Kotlin source files only |
| Fonts | ~1 MB | Custom fonts for styling |
| Gradle cache | Variable | Build artifacts |

