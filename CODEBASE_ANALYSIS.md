# Flanergide Android App - Codebase Analysis

## Executive Summary

**Flanergide** is an on-device LLM Android overlay app that displays AI-generated "Nico-nico style" scrolling messages across the user's screen. The app uses a **Phi-2 Q4_K_M quantized language model (1.6 GB)** running locally via llama.cpp, eliminating the need for cloud connectivity.

**Key Architecture**: Hybrid event-driven + state management using Kotlin Coroutines, with decoupled modules communicating via an EventBus and StateStore pattern.

---

## 1. PROJECT STRUCTURE

### Directory Layout
```
Flanergide/
├── android/                          # Main Android module
│   ├── app/                          # Application module (APK)
│   ├── llama.cpp/                    # llama.cpp submodule (C++ LLM inference)
│   ├── models/                       # Local ML model storage
│   ├── settings.gradle.kts
│   └── local.properties
├── settings.gradle.kts               # Root monorepo configuration
└── README.md
```

### Module Breakdown
- **Monorepo Structure**: Root settings.gradle.kts includes `android` build
- **Backend Placeholder**: `backend/` directory prepared for future server integration
- **Android SDK Target**: API 33-34 (Android 13-14)
- **Kotlin Compiler**: 2.0.21

---

## 2. ANDROID PERMISSIONS & CAPABILITIES

### Declared Permissions (AndroidManifest.xml)

```xml
<!-- Core Overlay Permissions -->
<uses-permission android:name="android.permission.SYSTEM_ALERT_WINDOW" />
<!-- Allows drawing over other apps (required for scrolling messages) -->

<!-- Foreground Service -->
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_SPECIAL_USE" />
<!-- Keeps service alive even when app backgrounded -->

<!-- Notification -->
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
<!-- Displays persistent notification (Android 13+) -->
```

### Key Capabilities Configured

| Capability | Status | Purpose |
|-----------|--------|---------|
| System Overlays (WindowManager) | ✅ Enabled | Draw floating messages over apps |
| Foreground Service | ✅ Enabled | Keep AI generation alive |
| Special Use FGS | ✅ Enabled | Declared as "overlay" type |
| Notifications | ✅ Enabled | Persistent notification for FGS |
| Jetpack Compose | ✅ Enabled | Modern UI rendering |
| llama.cpp Android | ✅ Integrated | On-device LLM inference |

### Permissions NOT Currently Used
- **USAGE_STATS** - Placeholder for detecting app context (Phase 2)
- **NOTIFICATION_LISTENER_SERVICE** - Placeholder for notification sniffing (Phase 2)
- **INTERNET** - None (fully offline-capable)

---

## 3. SERVICES, RECEIVERS & INTEGRATIONS

### Core Services

#### 1. **RealityService** (Foreground Service)
- **Package**: `com.flanergide`
- **Type**: `FOREGROUND_SERVICE_SPECIAL_USE` (overlay)
- **Purpose**: Main orchestrator that keeps app alive
- **Responsibilities**:
  - Runs as persistent foreground service with notification
  - Initializes all modules in sequence
  - Coordinates lifecycle of StateStore, PermissionManager, OverlayEngine, AIOrchestrator
  - Handles cleanup on shutdown

**Service Startup Flow**:
```kotlin
RealityService.start(context) 
  → onCreate()
  → createNotificationChannel()
  → startForeground()
  → initializeModules()
    ├── StateStore.init()
    ├── PermissionManager.init()
    ├── OverlayEngine.init()
    └── AIOrchestrator.init()
```

**Lifecycle Modes**:
- START_STICKY (restarts if killed by system)
- Non-exported (only accessible internally)

---

### Activities

#### 1. **MainActivity** (Launcher)
- **Type**: ComponentActivity (Jetpack Compose)
- **Purpose**: Minimal UI showing app status
- **Responsibilities**:
  - Launch RealityService on app start
  - Display permission status
  - Show UI status cards
  - Request SYSTEM_ALERT_WINDOW permission

**UI Features**:
- Service status indicator
- Permissions status display
- Permission request button
- Info section explaining how the app works

---

### Broadcast Receivers

**Profile Installer Receiver** (from androidx.profileinstaller)
- Handles app performance profile installation
- Actions: INSTALL_PROFILE, SKIP_FILE, SAVE_PROFILE, BENCHMARK_OPERATION

**Custom Permission Receiver** (Signature-level)
```xml
<permission
    android:name="com.flanergide.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
    android:protectionLevel="signature" />
```

---

### Providers

#### **InitializationProvider** (androidx.startup)
Initializes various libraries on app start:
- **EmojiCompatInitializer** - Emoji rendering support
- **ProcessLifecycleInitializer** - App lifecycle tracking
- **ProfileInstallerInitializer** - Performance profile installation

---

## 4. DATA SOURCES & ACCESSIBILITY

### Currently Implemented Data Sources

#### 1. **Local LLM (Phi-2 Q4_K_M)**
- **Source**: On-device quantized language model
- **Size**: 1.6 GB GGUF format
- **Access Method**: llama.cpp Android library
- **Data Flow**: 
  ```
  Random Prompt 
    → LLM Inference 
    → Generated Text 
    → EventBus 
    → UI Display
  ```
- **Frequency**: Every 10-30 seconds (randomized)
- **Privacy**: ✅ 100% local, no data leaves device

#### 2. **System Time**
- **Access**: `System.currentTimeMillis()`
- **Usage**: Message timestamps

#### 3. **Device Configuration**
- **Access**: `LocalConfiguration` (Jetpack Compose)
- **Data**: Screen dimensions, font sizes

---

### Readily Available Data Sources (Not Yet Implemented)

#### ⭐ High Priority (Already Declared)

**1. App Context Detection**
- **Permission**: USAGE_STATS (not yet requested)
- **API**: `UsageStatsManager` 
- **Available Data**:
  - Currently running app package
  - App usage frequency/patterns
  - Time spent in each app
- **Potential Use**: Contextual message generation, app-gating mini-games

**2. Notifications**
- **Permission**: NOTIFICATION_LISTENER_SERVICE (not yet declared)
- **API**: `NotificationListenerService`
- **Available Data**:
  - Incoming notifications (SMS, messaging apps, social media)
  - Notification text and metadata
  - App package generating notification
- **Potential Use**: Reactive message generation based on events

---

#### ⭐ Medium Priority (Easily Declarable)

**3. Calendar Events**
- **Permission**: READ_CALENDAR
- **API**: `CalendarContract` ContentProvider
- **Available Data**:
  - Event titles and descriptions
  - Event timing (upcoming, in-progress)
  - Event organizers and attendees
- **Potential Use**: Time-aware message generation

**4. Contacts**
- **Permission**: READ_CONTACTS
- **API**: `ContactsContract` ContentProvider
- **Available Data**:
  - Contact names
  - Phone numbers
  - Email addresses
- **Potential Use**: Personalized messages

**5. Messages/SMS**
- **Permission**: READ_SMS
- **API**: `Telephony.Sms` ContentProvider
- **Available Data**:
  - SMS text content
  - Sender information
  - Timestamps
- **Potential Use**: SMS context-aware responses

**6. Call Log**
- **Permission**: READ_CALL_LOG
- **API**: `CallLog.Calls` ContentProvider
- **Available Data**:
  - Call duration and timestamps
  - Phone numbers called
- **Potential Use**: Communication pattern analysis

---

#### ⭐ Lower Priority (Modern Android)

**7. Device Info**
- **No special permission needed**
- **API**: `Build`, `Settings`
- **Available Data**:
  - Device model, OS version
  - Display metrics
  - Battery status (if added)
- **Potential Use**: Device-specific optimizations

**8. Location**
- **Permissions**: ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION
- **APIs**: `FusedLocationProviderClient` (Google Play Services)
- **Available Data**:
  - GPS coordinates
  - Approximate location (from network)
- **Potential Use**: Location-aware messages

**9. Clipboard**
- **Permission**: READ_CLIPBOARD_CONTENT (Android 13+)
- **API**: `ClipboardManager`
- **Available Data**:
  - Recently copied text
- **Potential Use**: Contextual comments on clipboard content

**10. Phone State**
- **Permission**: READ_PHONE_STATE
- **API**: `TelephonyManager`
- **Available Data**:
  - Call state (ringing, off-hook)
  - Phone number
  - Network type/signal strength
- **Potential Use**: Call-aware message suppression

---

### Data Collection Patterns Observed

#### 1. **Event-Based Architecture**
App uses **sealed class event hierarchy** (`AppEvent`) with specific event types:
```kotlin
sealed class AppEvent {
    data class NewMessage(val content: String, val source: String)
    data class PermissionStateChange(val permission: Permission, val granted: Boolean)
    data class MiniGameTrigger(val gameType: MiniGameType, val targetApp: String)
    // More...
}
```

**Events flow**: `EventBus.emit()` → `StateStore.reduce()` → UI updates

#### 2. **Permission State Tracking**
- **Polling Interval**: 5 seconds (configurable in PermissionManager)
- **Tracked Permissions**:
  - SYSTEM_ALERT_WINDOW (currently active)
  - USAGE_STATS (placeholder)
  - NOTIFICATION_LISTENER (placeholder)

#### 3. **Logging Infrastructure**
- **Pattern**: TAG-based logging on every major operation
- **Log Levels**: Info (I), Debug (D), Warning (W), Error (E)
- **Data Logged**:
  - Initialization steps (verbose)
  - State changes
  - Permission checks
  - Message generation progress
  - Error details
- **Note**: Logs could be captured by logcat without special permission

---

## 5. DATA INGESTION ARCHITECTURE

### Current Data Flow

```
┌─────────────────────────────────────────┐
│         AIOrchestrator                  │
│  (On-device LLM Message Generation)     │
└──────────────┬──────────────────────────┘
               │ (generates NewMessage event)
               ↓
┌─────────────────────────────────────────┐
│           EventBus                      │
│  (MutableSharedFlow - event broadcast)  │
│  - capacity: 64                         │
│  - replay: 0 (no history)               │
│  - overflow: DROP_OLDEST                │
└──────────────┬──────────────────────────┘
               │ (observes events)
               ↓
┌─────────────────────────────────────────┐
│         StateStore                      │
│  (StateFlow - centralized state)        │
│  - applies reducer function             │
│  - maintains app state                  │
└──────────────┬──────────────────────────┘
               │ (state changes)
               ↓
┌─────────────────────────────────────────┐
│       OverlayEngine + UI                │
│  (Jetpack Compose window overlay)       │
│  - monitors recentMessages              │
│  - detects permission changes           │
└─────────────────────────────────────────┘
```

### Permission State Data Flow

```
PermissionManager (polling every 5s)
  ├─ hasSystemAlertWindow()
  │   └─ Settings.canDrawOverlays()
  ├─ emit(PermissionStateChange event)
  └─ StateStore updates permissions
      └─ OverlayEngine checks before showing
```

---

## 6. MODEL & INFERENCE INTEGRATION

### LLM Setup

**Model Details**:
- **Name**: Phi-2 Q4_K_M
- **Size**: 1.6 GB (quantized to 4-bit)
- **Type**: GGUF format (inference-optimized)
- **Framework**: llama.cpp Android library

**Load Process**:
1. Copy model from APK assets to internal storage (first run only)
2. Validate file integrity (size checks with tolerance)
3. Load into memory via `LLamaAndroid.instance().load(modelPath)`
4. Takes 5-10 seconds

**Generation Process**:
```kotlin
val prompt = MessageGenerator.getRandomPrompt()
val response = llama.send(
    formattedPrompt = formatPromptWithPersona(prompt),
    maxTokens = 128,  // ~1-2 sentences
    formatChat = false
)
```

**Persona System**:
- Wraps all prompts with Jill Stingray (VA-11 Hall-A bartender) context
- Maintains character consistency in responses

---

## 7. ARCHITECTURE PATTERNS

### 1. **Module Isolation**
- No direct dependencies between modules
- All communication via EventBus (decoupled)
- Each module manages own lifecycle

### 2. **Kotlin Coroutines**
- Scope: `serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)`
- Dispatchers: Main (UI), IO (file I/O), Default (CPU-intensive)
- Cancellation: Clean shutdown via `scope.cancel()`

### 3. **Flow-Based Reactivity**
- **SharedFlow**: EventBus for one-way events (no history replay)
- **StateFlow**: StateStore for reactive state (always has current value)
- **distinctUntilChanged()**: Optimizes redundant updates

### 4. **Reducer Pattern**
```kotlin
private fun reduce(state: AppState, event: AppEvent): AppState {
    return when (event) {
        is AppEvent.NewMessage -> state.copy(/* update */)
        is AppEvent.PermissionStateChange -> state.copy(/* update */)
        // ...
    }
}
```

---

## 8. BUILD CONFIGURATION

### Key Dependencies

```kotlin
// Core Android
androidx-core-ktx: 1.10.1
androidx-appcompat: 1.6.1
material: 1.10.0

// Jetpack Compose (2024.02.00)
androidx-compose-bom
androidx-compose-ui
androidx-compose-material3
androidx-activity-compose: 1.8.2

// Coroutines
kotlinx-coroutines-android: 1.8.0
kotlinx-coroutines-core: 1.8.0

// Lifecycle
androidx-lifecycle-runtime-ktx: 2.7.0
androidx-lifecycle-viewmodel-compose: 2.7.0
androidx-savedstate: 1.2.1

// ML
llama.cpp Android (local project integration)

// Testing
junit: 4.13.2
androidx-junit: 1.1.5
androidx-espresso-core: 3.5.1
```

### Special Build Settings

```gradle
// Prevent GGUF model compression in APK
androidResources {
    noCompress += "gguf"
}
```

---

## 9. SECURITY & PRIVACY CONSIDERATIONS

### Privacy Protections ✅
- **No Internet Permission**: App cannot make network requests
- **No Cloud Data**: All processing 100% on-device
- **No Data Sharing**: No external ContentProviders exposed
- **Minimal Permissions**: Only SYSTEM_ALERT_WINDOW + notification
- **Signature-Level Permissions**: Custom permission uses signature protection level

### Potential Data Exposure Risks
1. **Logcat Access**: Anyone with adb/logcat access can read verbose logs
   - Solution: Strip debug logs in release builds
2. **App Memory**: Debugger could inspect model responses in RAM
   - Solution: Proguard/R8 obfuscation (currently disabled)
3. **File System**: Model file stored in internal storage (readable by other apps if obtained)
   - Solution: Already in app-private directory by default

---

## 10. WHAT DATA CAN BE ACCESSED & HOW

### Current Access (Phase 1)
| Data | Source | Access Method | Used |
|------|--------|----------------|------|
| Generated prompts | Array in code | In-memory selection | ✅ |
| LLM responses | On-device inference | llama.cpp library | ✅ |
| Time | System API | System.currentTimeMillis() | ✅ |
| Permissions state | Settings API | Settings.canDrawOverlays() | ✅ |
| Screen dimensions | LocalConfiguration | Jetpack Compose | ✅ |

### Immediate Access (With Current Permissions)
| Data | Permission | API | Status |
|------|-----------|-----|--------|
| Draw permissions | Implicit | Settings API | ✅ |
| Device build info | None needed | Build class | ✅ |
| System fonts | None needed | Resources | ✅ |

### Accessible With Permission Requests (Phase 2+)
| Data | New Permission | API | Use Case |
|------|---------------|-----|----------|
| Running app | USAGE_STATS | UsageStatsManager | Context detection |
| Notifications | NOTIFICATION_LISTENER | NotificationListenerService | Reactive messages |
| Calendar | READ_CALENDAR | CalendarContract | Time-aware messages |
| Contacts | READ_CONTACTS | ContactsContract | Personalization |
| SMS/Messages | READ_SMS | Telephony.Sms | Message context |
| Call log | READ_CALL_LOG | CallLog.Calls | Communication analysis |
| Location | ACCESS_FINE_LOCATION | FusedLocationProvider | Location-aware |
| Clipboard | READ_CLIPBOARD (API 33+) | ClipboardManager | Content context |
| Phone state | READ_PHONE_STATE | TelephonyManager | Call detection |

---

## 11. DEPLOYMENT & VERSIONING

**Current Build Version**:
- Version Code: 1
- Version Name: 1.0
- Target SDK: 34 (Android 14)
- Min SDK: 33 (Android 13)

**Package Name**: `com.flanergide` (rebranded from com.realityskin)

**Debug Mode**: Currently enabled (debuggable=true in manifest)

---

## 12. TESTING & MONITORING

### Existing Test Stubs
- `ExampleInstrumentedTest.kt` (AndroidTest)
- `ExampleUnitTest.kt` (Unit Test)
- **Status**: Boilerplate only, no tests implemented

### Monitoring/Analytics
- **Logging**: Extensive TAG-based logging throughout
- **No Built-in Analytics**: No Firebase, Mixpanel, etc.
- **No Remote Telemetry**: No cloud reporting

---

## 13. FUTURE EXPANSION POINTS

### Backend Integration Ready
- Monorepo structure supports future `backend/` integration
- `includeBuild("backend")` commented out, ready to enable

### App Guardian Service (Placeholder)
- Structure references "AppGuardianService" in docs
- Not yet implemented
- Purpose: Mini-games to gate app access

### Mini-Game System
- Event structure defined: `MiniGameTrigger`, `MiniGameComplete`
- State support: `activeMiniGame: MiniGame?`
- UI overlay support: `OverlayType.MINI_GAME`
- Implementation: Pending

---

## SUMMARY TABLE: Data Ingestion Capabilities

| Category | Current | Available | Phase |
|----------|---------|-----------|-------|
| **Core LLM** | Phi-2 local inference | - | 1 ✅ |
| **Logging** | Extensive logging | Logcat analysis | 1 ✅ |
| **Permissions** | SYSTEM_ALERT_WINDOW check | 5sec polling | 1 ✅ |
| **App Context** | Prompts only | USAGE_STATS API | 2 |
| **Notifications** | None | NotificationListener | 2 |
| **Calendar** | None | CalendarContract | 2+ |
| **Contacts** | None | ContactsContract | 2+ |
| **Messages** | None | SMS/MMS APIs | 2+ |
| **Location** | None | FusedLocationProvider | 3+ |
| **Clipboard** | None | ClipboardManager | 2+ |
| **Calls** | None | CallLog API | 2+ |

---

## KEY FINDINGS

1. **Architecture is Clean & Modular**: Event-based communication eliminates tight coupling
2. **Privacy-First Design**: No network, no cloud, 100% local processing
3. **Extensible Permission Model**: Placeholder structure ready for Phase 2+ features
4. **Logging is Verbose**: Risk of sensitive data exposure via logcat
5. **No Analytics Built-in**: Good for privacy, but requires custom monitoring
6. **Model Storage**: 1.6 GB model file takes up significant app storage
7. **Performance**: LLM loading (5-10s), generation (varies), overlay rendering (real-time)
8. **Scalability Ready**: EventBus + StateStore can handle adding new data sources
