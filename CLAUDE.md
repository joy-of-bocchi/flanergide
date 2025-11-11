# RealitySkin — Architecture Overview

## High-Level Design Philosophy

**Hybrid Event-Driven + State Management Architecture**

- **EventBus (SharedFlow)**: Decoupled communication between modules
- **StateStore (StateFlow)**: Single source of truth for global app state
- **Module Isolation**: No direct inter-module dependencies
- **Reactive UI**: Compose subscribes to StateFlow for automatic recomposition

---

## Core Flow Pattern

```
Module A → emits Event → EventBus → StateStore updates global state
                                          ↓
                                    StateFlow emission
                                          ↓
                                    Module B subscribes → reacts to state change
```

**Key Principle**: Modules emit events describing **what happened**. StateStore decides **what changes**. Other modules react to **new state**.

---

## System Architecture

### 1️⃣ RealityService (Foreground Service)

**Role**: Orchestrator and lifecycle manager

**Responsibilities**:
- Keeps app alive as foreground service
- Initializes all modules on startup
- Coordinates permission checks via PermissionManager
- Ensures overlays remain active
- Handles service lifecycle (start/stop/restart)

**Does NOT**: Perform business logic or UI rendering

---

### 2️⃣ EventBus (Central Communication Hub)

**Implementation**: Kotlin `SharedFlow`

**Purpose**: Asynchronous, decoupled communication between modules

**Event Types** (sealed class hierarchy):
```kotlin
sealed class AppEvent {
    data class NewMessage(val message: String, val source: String)
    data class AvatarMoodChange(val mood: AvatarMood)
    data class MiniGameTrigger(val gameType: MiniGameType, val targetApp: String)
    data class MiniGameComplete(val success: Boolean, val targetApp: String)
    data class PermissionStateChange(val permission: Permission, val granted: Boolean)
}
```

**Usage**:
- Modules emit events: `EventBus.emit(AvatarMoodChange(mood = "happy"))`
- Modules subscribe: `EventBus.events.collect { event -> ... }`

---

### 3️⃣ StateStore (Single Source of Truth)

**Implementation**: Kotlin `StateFlow`

**Purpose**: Holds all global application state

**State Schema**:
```kotlin
data class AppState(
    val avatarMood: AvatarMood = AvatarMood.Neutral,
    val activeMiniGame: MiniGame? = null,
    val permissions: PermissionState = PermissionState(),
    val recentMessages: List<Message> = emptyList(),
    val overlayVisibility: Map<OverlayType, Boolean> = emptyMap()
)
```

**How It Works**:
1. EventBus emits event
2. StateStore subscribes to EventBus
3. StateStore applies event to current state (reducer pattern)
4. StateStore emits new state via StateFlow
5. Modules subscribing to StateFlow get updated state

**State Persistence**:
- On service stop: Serialize StateStore to DataStore/SharedPreferences
- On service restart: Restore from storage or use defaults

**Why This Matters**:
- Late subscribers always get current state (no missed events)
- Debuggable: Single place to inspect entire app state
- Testable: Pure functions transform state

---

### 4️⃣ PermissionManager (Permission State Tracker)

**Responsibilities**:
- Tracks status of required Android permissions:
  - `SYSTEM_ALERT_WINDOW` (draw overlays)
  - `PACKAGE_USAGE_STATS` (detect app launches)
  - `BIND_NOTIFICATION_LISTENER_SERVICE` (read notifications)
- Emits `PermissionStateChange` events when permissions granted/revoked
- Provides UI helpers to request permissions via Settings deep links

**Communication**:
- Emits events → EventBus → StateStore updates `permissions` field
- Other modules subscribe to `appState.permissions` to pause/resume

---

### 5️⃣ FontProvider (Per-Message Random Fonts)

**Responsibilities**:
- Provides random font selection for each message
- Loads fonts from `assets/fonts/` directory
- Simple utility - no state management needed

**Usage**:
- Each message independently calls `FontProvider.getRandomFontFamily(context)`
- No EventBus or StateStore involvement
- No global font state

---

### 6️⃣ OverlayEngine (UI Rendering Layer)

**Implementation**: Jetpack Compose + `WindowManager.addView()`

**Responsibilities**:
- Draws all system overlays:
  - Scrolling Nico-style messages
  - AI avatar animations
  - Mini-game UI
  - Status indicators
- Handles animations, touch events, z-indexing
- Manages overlay lifecycle (show/hide/remove)

**Communication**:
- Subscribes to `appState` StateFlow
- On `activeMiniGame` != null → shows mini-game overlay
- On `recentMessages` update → scrolls new message
- Each message independently gets random font via FontProvider

**Does NOT**: Directly call other modules or emit business logic events

---

### 7️⃣ AIOrchestrator (AI Persona Engine)

**Responsibilities**:
- Generates AI persona messages, moods, behaviors
- Processes incoming notifications from NotificationListenerService
- Runs on-device ML/LLM inference
- Decides avatar mood based on context

**Communication**:
- Receives notification → generates response → emits `NewMessage` event
- Determines mood shift → emits `AvatarMoodChange` event
- StateStore updates → OverlayEngine displays new message + avatar

**Does NOT**: Directly manipulate overlays

---

### 8️⃣ AppGuardianService (App Gating System)

**Implementation**: `UsageStatsManager` polling + overlay hijacking

**Responsibilities**:
- Monitors foreground app changes via `UsageStatsManager.queryEvents()`
- When gated app detected → emits `MiniGameTrigger` event
- StateStore updates `activeMiniGame`
- OverlayEngine sees state change → draws fullscreen mini-game overlay
- User completes game → emits `MiniGameComplete` event
- StateStore clears `activeMiniGame` → OverlayEngine removes overlay

**Why Not AccessibilityService**:
- UsageStatsManager + overlay hijacking is Play Store compliant
- AccessibilityService risks policy violations
- Achieves same UX: blocks app until mini-game complete

**Required Permission**: `PACKAGE_USAGE_STATS` (granted via Settings)

---

### 9️⃣ Storage / Data Layer

**Implementation**: Jetpack DataStore (or Room for complex data)

**Responsibilities**:
- Persists user preferences, font cache, AI persona state
- Stores mini-game progress, message history
- Serializes/deserializes StateStore on service restart

**Communication**:
- StateStore periodically writes state to DataStore
- On service start, StateStore reads persisted state or uses defaults

---

## Key Design Decisions

### ✅ Why EventBus + StateStore (Not Just Events)?

**Problem with pure EventBus**:
- Late subscribers miss events
- No single source of truth
- Hard to debug: "What's the current avatar mood?" requires tracing event history

**Solution**:
- EventBus for **decoupling** (loose coupling between modules)
- StateStore for **truth** (always know current state)
- Modules subscribe to state, not just events

---

### ✅ When to Use Global State vs. Local State

**Global State (in StateStore)**:
- Avatar mood (affects multiple overlays)
- Active mini-game (blocks app, shown by overlay)
- Permission status (multiple modules need to check)

**Local State (module-internal)**:
- OverlayEngine's current animation frame
- AIOrchestrator's LLM inference buffer
- Per-message font selection (random, independent)

**Rule of Thumb**: If 2+ modules need it → global state. Otherwise → local.

---

### ✅ Error Handling Strategy

**Module-Level Errors**:
- Catch exceptions within module
- Emit error event: `AppEvent.Error(module = "AIOrchestrator", message = "...")`
- StateStore updates `appState.lastError`
- OverlayEngine can show error toast

**Critical Errors** (e.g., service crash):
- Android restarts RealityService
- StateStore loads persisted state or defaults
- Modules reinitialize with safe fallback behavior

---

### ✅ Testing Strategy

**Unit Tests**:
- StateStore reducer logic (given event + state → new state)
- Pure functions in AIOrchestrator

**Integration Tests**:
- Emit event → verify StateStore updates correctly
- Update StateStore → verify OverlayEngine recomposes

**Manual Tests**:
- Revoke permission mid-session → verify graceful degradation
- Kill service → verify state restoration

---

## Event Flow Examples

### Example 1: Notification Arrives

```
1. NotificationListenerService receives notification
2. AIOrchestrator processes notification → emits NewMessage("Hey, you got mail!", "gmail")
3. EventBus forwards event to StateStore
4. StateStore updates appState.recentMessages (prepend new message)
5. OverlayEngine subscribes to appState.recentMessages → recomposes scrolling overlay
6. User sees new message scroll across screen
```

---

### Example 2: User Opens Gated App

```
1. AppGuardianService polls UsageStatsManager → detects Instagram launch
2. AppGuardianService emits MiniGameTrigger(gameType = "QuickMath", targetApp = "instagram")
3. StateStore updates appState.activeMiniGame = MiniGame("QuickMath", "instagram")
4. OverlayEngine subscribes to appState.activeMiniGame → draws fullscreen math game
5. User solves 3 + 5 = ?
6. OverlayEngine emits MiniGameComplete(success = true, targetApp = "instagram")
7. StateStore clears appState.activeMiniGame = null
8. OverlayEngine removes overlay → Instagram is now visible
```

---

### Example 3: Random Font Per Message

```
1. AIOrchestrator emits NewMessage("Hello", "ai")
2. StateStore updates appState.recentMessages
3. OverlayEngine creates new message overlay
4. Message overlay calls FontProvider.getRandomFontFamily(context)
5. Message renders in randomly selected font (independent of other messages)
```

---

## Technology Stack

- **Language**: Kotlin
- **UI**: Jetpack Compose (for overlays)
- **Concurrency**: Coroutines + Flow
- **DI**: Manual (or Hilt if complexity grows)
- **Storage**: Jetpack DataStore
- **Overlays**: `WindowManager.addView()` with `TYPE_APPLICATION_OVERLAY`
- **App Detection**: `UsageStatsManager`
- **Notifications**: `NotificationListenerService`
- **On-Device ML**: GGUF format (Phi-2 quantized to Q4_K_M, 1.6GB)

---

## ML Model Management

### On-Device LLM: Phi-2 (GGUF Format)

**Model Location**:
```
app/src/main/assets/models/phi-2-q4_k_m.gguf (1.6 GB)
```

**Source Model**:
- Original: `microsoft/phi-2` (Hugging Face)
- Converted to GGUF FP16: `models/phi-2-gguf/phi-2-f16.gguf` (5.18 GB)
- Quantized to Q4_K_M: `models/phi-2-gguf/phi-2-q4_k_m.gguf` (1.62 GB)

**Why Q4_K_M**:
- 68% smaller than FP16 (5.18 GB → 1.62 GB)
- Suitable for mobile devices
- Good quality/size trade-off

### Converting Models (Mac Development)

**Prerequisites**:
1. **Conda Environment**: `RealitySkin`
2. **llama.cpp**: Already cloned and built in project root

**Activate Conda Environment**:
```bash
conda activate RealitySkin
```

**Required Python Packages** (already installed in `RealitySkin` env):
```
gguf
transformers
torch
sentencepiece
mistral-common
```

**Convert Phi-2 to GGUF**:
```bash
# Activate conda environment first
source ~/anaconda3/etc/profile.d/conda.sh
conda activate RealitySkin

# Run conversion script
python convert_phi2_to_gguf.py
```

**Script Output**:
- Downloads Phi-2 from Hugging Face (if not present)
- Converts to FP16 GGUF format
- Quantizes to Q4_K_M (4-bit)
- Outputs to `models/phi-2-gguf/`

**Test Model Locally**:
```bash
./llama.cpp/build/bin/llama-cli -m models/phi-2-gguf/phi-2-q4_k_m.gguf -p "Hello, I am"
```

**Copy to Android Assets** (already done):
```bash
cp models/phi-2-gguf/phi-2-q4_k_m.gguf app/src/main/assets/models/
```

**⚠️ IMPORTANT: Prevent Asset Compression**

Add this to `app/build.gradle.kts` to prevent Android from compressing the GGUF file:

```kotlin
android {
    // ... other config ...

    // Prevent compression of GGUF model files
    androidResources {
        noCompress += "gguf"
    }
}
```

Without this, the model will be compressed in the APK and fail to load with:
```
"This file can not be opened as a file descriptor; it is probably compressed"
```

### Integration with AIOrchestrator

See `app/src/main/java/com/realityskin/ai/CLAUDE.md` for details on:
- Loading GGUF model from assets
- Running inference with llama.cpp Android bindings
- Generating AI persona messages

---

## Module Communication Rules

### ✅ DO

- Emit events to EventBus when your module's internal state changes
- Subscribe to StateStore's `appState` to react to global state changes
- Keep local state internal to your module
- Use sealed classes for type-safe events

### ❌ DON'T

- Call methods on other modules directly
- Share mutable state between modules
- Emit events for internal module logic
- Block the main thread in event handlers

---

## File Structure

```
RealitySkin/
├── CLAUDE.md (this file)
├── app/
│   ├── manifests/
│   │   └── AndroidManifest.xml
│   ├── kotlin/
│   │   └── com.realityskin/
│   │       ├── RealityService.kt (foreground service)
│   │       ├── core/
│   │       │   ├── EventBus.kt (SharedFlow hub)
│   │       │   ├── StateStore.kt (StateFlow store)
│   │       │   └── AppState.kt (data classes)
│   │       ├── permissions/
│   │       │   └── PermissionManager.kt
│   │       ├── fonts/
│   │       │   └── FontProvider.kt
│   │       ├── overlay/
│   │       │   ├── OverlayEngine.kt
│   │       │   └── composables/ (UI components)
│   │       ├── ai/
│   │       │   └── AIOrchestrator.kt
│   │       ├── guardian/
│   │       │   └── AppGuardianService.kt
│   │       └── storage/
│   │           └── DataRepository.kt
└── README.md (user-facing docs)
```

---

## Current Implementation Status

**Implemented (Phases 1-5)**:
- ✅ Core Module (EventBus, StateStore, Events, AppState)
- ✅ AI Module (GGUFModel, AIOrchestrator, MessageGenerator)
- ✅ Overlay Module (OverlayEngine, ScrollingMessageOverlay)
- ✅ Permissions Module (PermissionManager)
- ✅ RealityService (foreground service, module initialization)
- ✅ MainActivity (launcher, permission UI)

**Implemented (Phase 6)**:
- ✅ FontProvider (random font utility)
- ❌ AppGuardianService (mini-game gating)
- ❌ Storage/DataRepository (state persistence)
- ❌ Avatar overlay
- ❌ Mini-game overlays

**Current Features**:
- Nico-nico style scrolling messages (random direction, speed, size, position)
- On-device AI (Phi-2 Q4_K_M, 1.6 GB)
- Random prompt generation (30+ prompts)
- Message interval: 10-30 seconds
- Max concurrent messages: 5

See `README.md` and `BUILD_VERIFICATION.md` for build/test instructions.

---

## Notes for AI Agent

- **Always emit events through EventBus**, never direct calls
- **Subscribe to `appState` StateFlow**, not raw events
- **Keep business logic out of OverlayEngine** (it's just a renderer)
- **Test state transitions** with unit tests (event → state → new state)
- **Persist state** on service stop, restore on start
- **Gracefully degrade** when permissions are missing (don't crash)

---

**Target Users**: Technical Android users comfortable with aggressive permissions
**Distribution**: Sideload / F-Droid (Play Store optional, not required)
**Battery Impact**: Expected moderate drain (foreground service + overlays)
**Android Version**: Target API 31+ (Android 12+), min API 29 (Android 10)
