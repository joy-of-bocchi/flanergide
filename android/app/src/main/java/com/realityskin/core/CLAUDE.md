# Core Module — EventBus + StateStore

## Status: ✅ IMPLEMENTED (Phase 1)

## Purpose
The foundational layer for all inter-module communication and global state management.

## Implementation Notes
- EventBus: SharedFlow with replay=0, buffer=64
- StateStore: StateFlow with reducer pattern
- State persistence/restoration not yet implemented

## Components

### 1. EventBus.kt
**Type**: Singleton object with `SharedFlow`

**Responsibilities**:
- Provides a central `SharedFlow` for emitting events
- Allows modules to subscribe to all app events
- Ensures decoupled, asynchronous communication

**API**:
```kotlin
object EventBus {
    private val _events = MutableSharedFlow<AppEvent>(
        replay = 0,
        extraBufferCapacity = 64,
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )
    val events: SharedFlow<AppEvent> = _events.asSharedFlow()

    suspend fun emit(event: AppEvent) {
        _events.emit(event)
    }
}
```

**Usage**:
- **Emit**: `EventBus.emit(AvatarMoodChange(mood = AvatarMood.Happy))`
- **Subscribe**: `EventBus.events.collect { event -> handleEvent(event) }`

**Configuration**:
- `replay = 0`: New subscribers don't get past events (StateStore provides current state)
- `extraBufferCapacity = 64`: Handles burst events without blocking
- `DROP_OLDEST`: Prevents memory issues if subscribers are slow

---

### 2. StateStore.kt
**Type**: Singleton object with `StateFlow`

**Responsibilities**:
- Holds single source of truth for global app state
- Subscribes to EventBus and applies events to update state
- Emits new state via StateFlow when state changes
- Handles state persistence and restoration

**API**:
```kotlin
object StateStore {
    private val _appState = MutableStateFlow(AppState())
    val appState: StateFlow<AppState> = _appState.asStateFlow()

    fun init(scope: CoroutineScope) {
        scope.launch {
            EventBus.events.collect { event ->
                _appState.update { currentState ->
                    reduce(currentState, event)
                }
            }
        }
    }

    private fun reduce(state: AppState, event: AppEvent): AppState {
        return when (event) {
            is AppEvent.AvatarMoodChange -> state.copy(avatarMood = event.mood)
            is AppEvent.NewMessage -> state.copy(
                recentMessages = (listOf(event.toMessage()) + state.recentMessages).take(10)
            )
            is AppEvent.MiniGameTrigger -> state.copy(
                activeMiniGame = MiniGame(event.gameType, event.targetApp)
            )
            is AppEvent.MiniGameComplete -> state.copy(
                activeMiniGame = null
            )
            is AppEvent.PermissionStateChange -> state.copy(
                permissions = state.permissions.update(event.permission, event.granted)
            )
        }
    }

    suspend fun persistState(repository: DataRepository) {
        repository.saveAppState(_appState.value)
    }

    suspend fun restoreState(repository: DataRepository) {
        repository.loadAppState()?.let { saved ->
            _appState.value = saved
        }
    }
}
```

**State Reducer Pattern**:
- Pure function: `(currentState, event) → newState`
- Easy to test and reason about
- Exhaustive `when` ensures all events are handled

---

### 3. AppState.kt
**Type**: Data classes defining global state schema

**Schema**:
```kotlin
data class AppState(
    val avatarMood: AvatarMood = AvatarMood.Neutral,
    val activeMiniGame: MiniGame? = null,
    val permissions: PermissionState = PermissionState(),
    val recentMessages: List<Message> = emptyList(),
    val overlayVisibility: Map<OverlayType, Boolean> = mapOf(
        OverlayType.SCROLLING_MESSAGE to true,
        OverlayType.AVATAR to true,
        OverlayType.MINI_GAME to false
    )
)

enum class AvatarMood {
    Happy, Neutral, Sad, Excited, Angry, Thinking
}

data class MiniGame(
    val type: MiniGameType,
    val targetApp: String
)

enum class MiniGameType {
    QuickMath, MemoryMatch, ReactionTime
}

data class Message(
    val content: String,
    val source: String,
    val timestamp: Long = System.currentTimeMillis()
)

data class PermissionState(
    val systemAlertWindow: Boolean = false,
    val usageStats: Boolean = false,
    val notificationListener: Boolean = false
) {
    fun update(permission: Permission, granted: Boolean): PermissionState {
        return when (permission) {
            Permission.SYSTEM_ALERT_WINDOW -> copy(systemAlertWindow = granted)
            Permission.USAGE_STATS -> copy(usageStats = granted)
            Permission.NOTIFICATION_LISTENER -> copy(notificationListener = granted)
        }
    }
}

enum class Permission {
    SYSTEM_ALERT_WINDOW, USAGE_STATS, NOTIFICATION_LISTENER
}

enum class OverlayType {
    SCROLLING_MESSAGE, AVATAR, MINI_GAME
}
```

---

### 4. Events.kt
**Type**: Sealed class hierarchy defining all app events

**Event Types**:
```kotlin
sealed class AppEvent {
    data class NewMessage(
        val content: String,
        val source: String
    ) : AppEvent() {
        fun toMessage() = Message(content, source)
    }

    data class AvatarMoodChange(val mood: AvatarMood) : AppEvent()

    data class MiniGameTrigger(
        val gameType: MiniGameType,
        val targetApp: String
    ) : AppEvent()

    data class MiniGameComplete(
        val success: Boolean,
        val targetApp: String
    ) : AppEvent()

    data class PermissionStateChange(
        val permission: Permission,
        val granted: Boolean
    ) : AppEvent()
}
```

**Why Sealed Classes**:
- Type-safe event handling
- Exhaustive `when` expressions (compiler enforces handling all cases)
- Easy to add new events (just add to sealed class)

---

## Initialization Flow

Called from `RealityService.onCreate()`:

```kotlin
class RealityService : Service() {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    override fun onCreate() {
        super.onCreate()

        // 1. Restore persisted state
        serviceScope.launch {
            StateStore.restoreState(dataRepository)
        }

        // 2. Initialize StateStore to listen to EventBus
        StateStore.init(serviceScope)

        // 3. Initialize all other modules (they will subscribe to appState)
        // ...
    }

    override fun onDestroy() {
        // Persist state before service dies
        serviceScope.launch {
            StateStore.persistState(dataRepository)
        }
        serviceScope.cancel()
        super.onDestroy()
    }
}
```

---

## Usage Patterns

### Module Emitting Event
```kotlin
// Inside AIOrchestrator
lifecycleScope.launch {
    val mood = determineMoodFromNotification(notification)
    EventBus.emit(AppEvent.AvatarMoodChange(mood))
}
```

### Module Subscribing to State
```kotlin
// Inside OverlayEngine
lifecycleScope.launch {
    StateStore.appState.collect { state ->
        // Recompose UI based on new state
        when {
            state.activeMiniGame != null -> showMiniGameOverlay(state.activeMiniGame)
            state.recentMessages.isNotEmpty() -> showScrollingMessage(state.recentMessages.first())
        }
    }
}
```

### Module Reacting to Specific State Change
```kotlin
// Inside OverlayEngine (Compose)
val appState by StateStore.appState.collectAsState()
val context = LocalContext.current

// Each message gets random font via FontProvider
val fontFamily = remember(appState.recentMessages.firstOrNull()) {
    FontProvider.getRandomFontFamily(context)
}

Text(
    text = appState.recentMessages.firstOrNull()?.content ?: "",
    fontFamily = fontFamily
)
```

---

## Testing

### Unit Test: State Reducer
```kotlin
@Test
fun `reduce handles AvatarMoodChange event`() {
    val initialState = AppState()
    val event = AppEvent.AvatarMoodChange(AvatarMood.Happy)

    val newState = StateStore.reduce(initialState, event)

    assertEquals(AvatarMood.Happy, newState.avatarMood)
}
```

### Integration Test: EventBus → StateStore
```kotlin
@Test
fun `emitting event updates StateStore`() = runTest {
    StateStore.init(this)

    EventBus.emit(AppEvent.AvatarMoodChange(AvatarMood.Happy))

    advanceUntilIdle()
    assertEquals(AvatarMood.Happy, StateStore.appState.value.avatarMood)
}
```

---

## Key Principles

✅ **Single Responsibility**: EventBus only routes events. StateStore only manages state.

✅ **Immutability**: AppState is immutable. Always create new state with `.copy()`.

✅ **Testability**: Pure reducer functions are easy to test.

✅ **Type Safety**: Sealed classes ensure compile-time checking.

✅ **No Business Logic**: Core module has no domain logic, only infrastructure.

---

## Dependencies

- Kotlin Coroutines
- Kotlin Flow
- No external libraries needed

---

## Files in This Module

- `EventBus.kt` — SharedFlow event hub
- `StateStore.kt` — StateFlow state manager + reducer
- `AppState.kt` — Data classes for global state
- `Events.kt` — Sealed class event definitions
- `CLAUDE.md` — This file
