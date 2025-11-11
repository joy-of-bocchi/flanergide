# Data Capture Module

## Status: 🔄 IN PROGRESS (Phase 2 - Planning)

## Purpose
Real-time text capture from user input across all apps via AccessibilityService, with client-side redaction to remove sensitive data before storage.

---

## Current Implementation Plan

### Overview
This module captures what the user types in real-time, applies regex-based redaction to remove passwords/sensitive info, and stores it in memory for the AI module to pull from when generating contextual messages.

**Key principle**: Accumulate user activity data in the background; AI reads it on-demand (pull model, not push).

---

## Module Architecture

### Components

#### 1. SensitiveDataRedactor.kt
**Type**: Utility singleton object
**Purpose**: Regex-based redaction of sensitive patterns before storage

**Patterns redacted**:
- Passwords: `password=[REDACTED]`
- Credit cards: `\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}` → `[CREDIT_CARD]`
- API keys/tokens: `(api_key|token|auth|secret)=.*` → `[TOKEN_REDACTED]`
- Phone numbers: `\d{3}-\d{3}-\d{4}` → `[PHONE]`
- Emails: `[user]@[domain]` → `[EMAIL]`
- SSN: `\d{3}-\d{2}-\d{4}` → `[SSN]`
- URLs with credentials: `https://[user]:[pass]@` → `https://[REDACTED_CREDS]@`

**API**:
```kotlin
object SensitiveDataRedactor {
    fun redact(text: String): String
    fun redactForApp(text: String, appPackage: String): String  // App-aware redaction
}
```

#### 2. CapturedText.kt
**Type**: Data class
**Purpose**: Immutable container for a single captured text event

```kotlin
data class CapturedText(
    val text: String,           // Already redacted
    val appPackage: String,     // e.g., "com.instagram.android"
    val timestamp: Long         // System.currentTimeMillis()
)
```

#### 3. TextCaptureEngine.kt
**Type**: Singleton object
**Purpose**: Manage in-memory text log and coordinate accessibility service

**Responsibilities**:
- Maintain circular buffer of recent text (max 1000 entries)
- Apply redaction on incoming text
- Provide query API for AI module
- Enable/disable based on permission state
- Clean up on app restart

**API**:
```kotlin
@SuppressLint("StaticFieldLeak")
object TextCaptureEngine {
    fun init(appContext: Context, scope: CoroutineScope)
    fun addCapturedText(text: String, appPackage: String)
    fun getRecentText(limit: Int = 100): List<CapturedText>
    fun clear()
}
```

**Lifecycle**:
```
init() called by RealityService
  → Subscribe to PermissionManager events
  → When accessibility service enabled → start accepting text
  → When disabled → clear log
```

**Storage**:
```kotlin
private val capturedTextLog = mutableListOf<CapturedText>()

// Automatic cleanup: keep only last 1000 entries
if (capturedTextLog.size > 1000) {
    capturedTextLog.removeAt(0)
}
```

#### 4. KeyloggerAccessibilityService.kt
**Type**: Android AccessibilityService
**Purpose**: Hook into system accessibility events and route to TextCaptureEngine

**Lifecycle**:
- System enables service when user grants accessibility permission
- Routes accessibility events to TextCaptureEngine
- Minimal logic (just delegation)

**Implementation**:
```kotlin
class KeyloggerAccessibilityService : AccessibilityService() {
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType == AccessibilityEvent.TYPE_VIEW_TEXT_CHANGED) {
            val text = extractText(event) ?: return
            val appPackage = event.packageName?.toString() ?: "unknown"
            TextCaptureEngine.addCapturedText(text, appPackage)
        }
    }

    override fun onServiceConnected() {
        Log.i(TAG, "Accessibility service connected")
    }

    override fun onInterrupt() {
        Log.i(TAG, "Accessibility service interrupted")
    }

    private fun extractText(event: AccessibilityEvent): String? {
        return event.text.firstOrNull()?.toString()
    }
}
```

---

## Data Flow

### Text Capture Flow
```
1. User types in any app (e.g., Instagram)
2. AccessibilityService detects TYPE_VIEW_TEXT_CHANGED event
3. KeyloggerAccessibilityService.onAccessibilityEvent() fires
4. Extracts text from event: "hey how are you"
5. Calls TextCaptureEngine.addCapturedText("hey how are you", "com.instagram.android")
6. TextCaptureEngine:
   a. Passes text through SensitiveDataRedactor.redact()
   b. Creates CapturedText(text="hey how are you", appPackage="com.instagram.android", timestamp)
   c. Appends to capturedTextLog
   d. Removes oldest entry if > 1000
7. Text now available in memory for AI to read
```

### AI Integration Flow
```
1. AIOrchestrator timer fires (every 10-30 seconds)
2. Calls TextCaptureEngine.getRecentText(limit=100)
3. Gets List<CapturedText> from memory
4. Builds prompt context: "com.instagram.android: hey how are you\n..."
5. Feeds to Phi-2 model
6. Generates contextual message: "nice chatting with people! 💬"
7. Emits via EventBus.emit(NewMessage(...))
8. OverlayEngine displays message
```

---

## Integration Points

### 1. PermissionManager (permissions/)
- Already checks `hasAccessibilityServiceEnabled()`
- Already requests permission via `requestAccessibilityService()`
- Already emits `PermissionStateChange(ACCESSIBILITY_SERVICE, granted)` events
- **No changes needed**

### 2. AppState (core/)
- Add `ACCESSIBILITY_SERVICE` to `Permission` enum
- Add `accessibilityService: Boolean` to `PermissionState`
- **Minimal changes**

### 3. StateStore (core/)
- Add reducer case to handle `PermissionStateChange` for accessibility service
- **Minimal changes**

### 4. RealityService
- Call `TextCaptureEngine.init(applicationContext, serviceScope)` in `onCreate()`
- **One-line addition**

### 5. AIOrchestrator (ai/)
- Call `TextCaptureEngine.getRecentText(100)` when generating messages
- Use captured text to build prompt context
- **Enhances existing generateAndEmit() logic**

### 6. AndroidManifest
- Declare `KeyloggerAccessibilityService`
- Point to `accessibility_service_config.xml`
- **Standard service declaration**

---

## Storage Strategy

### Why In-Memory (Option 2)?
1. **Simple**: No file I/O, no database setup
2. **Fast**: Direct list access, no serialization overhead
3. **Scalable**: 1000-entry limit keeps memory bounded (~100KB)
4. **Migratable**: Easy to swap out for file/DB storage later

### Memory Safety
```kotlin
// Circular buffer pattern
if (capturedTextLog.size > 1000) {
    capturedTextLog.removeAt(0)  // Remove oldest
}
```

### Lifecycle
- **On app start**: `TextCaptureEngine.init()` creates empty list
- **During use**: Accumulates up to 1000 entries
- **On app restart**: List cleared (not persisted)
- **On disable**: `TextCaptureEngine.clear()` empties list

### Future: Migration to File Storage
```kotlin
// Later: swap in file-based storage
private val logFile = File(context.filesDir, "captured_text.jsonl")

fun addCapturedText(text: String, appPackage: String) {
    val entry = CapturedText(text, appPackage, System.currentTimeMillis())
    logFile.appendText(Json.encodeToString(entry) + "\n")
}

fun getRecentText(limit: Int): List<CapturedText> {
    return logFile.readLines().takeLast(limit).map { Json.decodeFromString(it) }
}
```

---

## Privacy & Security

### Redaction Strategy (Regex-based)
```kotlin
// Client-side redaction BEFORE storage
input:  "My password is P@ssw0rd123!"
output: "My password is [REDACTED]!"

input:  "Call me at 555-123-4567"
output: "Call me at [PHONE]"

input:  "API key: sk-abc123def456"
output: "API key: [TOKEN_REDACTED]"
```

### No Sensitive Data Stored
- Passwords never persisted
- Credit cards never persisted
- API keys never persisted
- Only user-readable message content stored

### Fail-Safe Design
- Redaction happens in TextCaptureEngine immediately on input
- No intermediate unredacted storage
- No bypassing redaction

---

## Testing Strategy

### Unit Tests
1. **SensitiveDataRedactor**
   - Test password redaction
   - Test credit card redaction
   - Test email redaction
   - Test false positives (don't redact legitimate text)

2. **TextCaptureEngine**
   - Test addCapturedText() adds to log
   - Test getRecentText() returns correct limit
   - Test circular buffer (max 1000)
   - Test clear() empties log

### Integration Tests
1. **Permission Flow**
   - Grant accessibility service permission
   - Verify KeyloggerAccessibilityService registered
   - Verify TextCaptureEngine initialized

2. **Text Capture**
   - Open Gmail, type message
   - Verify text captured in log
   - Verify redaction applied
   - Verify appPackage recorded

3. **AI Integration**
   - Type in Instagram
   - Wait for AI message generation
   - Verify message content reflects captured activity

### Manual Tests
1. Type in multiple apps → Verify all captured
2. Type password → Verify redacted
3. Disable service → Verify capture stops
4. Re-enable service → Verify capture resumes

---

## Dependencies

### Internal
- `core/StateStore.kt` (subscription to permission state)
- `permissions/PermissionManager.kt` (permission events)
- `ai/AIOrchestrator.kt` (pulls text data)

### External
- `android.accessibilityservice.AccessibilityService` (system framework)
- `android.view.accessibility.AccessibilityEvent` (system events)
- `android.content.Context` (application context)
- `kotlinx.coroutines` (lifecycle management)

---

## Implementation Order

1. Create `SensitiveDataRedactor.kt` (regex patterns)
2. Create `CapturedText.kt` (data class)
3. Create `TextCaptureEngine.kt` (core logic)
4. Create `KeyloggerAccessibilityService.kt` (system hook)
5. Create `accessibility_service_config.xml` (service config)
6. Update `AppState.kt` (add permission enum)
7. Update `StateStore.kt` (add permission reducer)
8. Update `AndroidManifest.xml` (register service)
9. Update `RealityService.kt` (initialize engine)
10. Update `AIOrchestrator.kt` (pull from engine)

---

## Open Questions / Decisions

1. **Redaction strategy**: Regex (current plan) or ML-based classification?
   - Decision: Regex for now (simple, fast)
   - Future: Add ML-based filtering if false positives too high

2. **Password field detection**: How to detect password fields?
   - Decision: Rely on redaction patterns + app-specific rules
   - Future: Check `event.isPassword` flag if available

3. **Storage persistence**: Keep in-memory only?
   - Decision: In-memory for Phase 2
   - Future: Migrate to file/DB when server sync needed

4. **Buffer size**: 1000 entries is good?
   - Decision: Yes, ~100KB max, keeps recent 1-2 hours of activity
   - Tunable via constant

5. **Event filtering**: Capture all TYPE_VIEW_TEXT_CHANGED?
   - Decision: Yes, filter sensitive apps in redaction if needed
   - Future: Add app-specific filtering rules

---

## Files in This Module

- `SensitiveDataRedactor.kt` — Regex-based redaction utility
- `CapturedText.kt` — Data class for captured text
- `TextCaptureEngine.kt` — In-memory store + coordination
- `KeyloggerAccessibilityService.kt` — System accessibility hook
- `CLAUDE.md` — This documentation file

---

## Related Documentation

- `permissions/CLAUDE.md` — Permission management and accessibility service enablement
- `ai/CLAUDE.md` — AI message generation (will be updated to use TextCaptureEngine)
- `core/CLAUDE.md` — State management and event bus (minimal changes)

