# OverlayEngine Module

## Status: ✅ PARTIAL (Phase 3)

## Current Implementation
- ✅ Scrolling Message Overlay (Nico-nico style)
  - Random direction (left-to-right or right-to-left)
  - Random speed (5-15 seconds)
  - Random Y position (0-800px)
  - Random font size (16-28sp)
  - Max concurrent: 5 messages
  - Fade in/out animations
- ❌ Avatar Overlay (not implemented)
- ❌ Mini-Game Overlay (not implemented)

## Purpose
Render all system overlays using Jetpack Compose and Android WindowManager.

## Overlay Types

### 1. Scrolling Message Overlay ✅
- Nico-style scrolling text across screen
- Shows recent messages from AI persona
- Animated entry/exit, smooth scrolling

### 2. Avatar Overlay ❌
- Not yet implemented

### 3. Mini-Game Overlay ❌
- Not yet implemented

---

## Architecture

### OverlayEngine.kt
**Type**: Singleton object managing all overlay windows

**Responsibilities**:
- Subscribe to StateStore for global state changes
- Create and destroy overlay windows
- Manage overlay lifecycle (show/hide/update)
- Handle touch events and animations
- Each overlay independently selects random fonts via FontProvider

**API**:
```kotlin
object OverlayEngine {
    private lateinit var windowManager: WindowManager
    private lateinit var context: Context

    private var scrollingMessageView: ComposeView? = null
    private var avatarView: ComposeView? = null
    private var miniGameView: ComposeView? = null

    fun init(appContext: Context, scope: CoroutineScope) {
        context = appContext.applicationContext
        windowManager = context.getSystemService(Context.WINDOW_SERVICE) as WindowManager

        // Subscribe to state changes
        scope.launch {
            StateStore.appState.collect { state ->
                updateOverlays(state)
            }
        }
    }

    private fun updateOverlays(state: AppState) {
        // Only show overlays if permission granted
        if (!state.permissions.systemAlertWindow) {
            hideAllOverlays()
            return
        }

        // Update scrolling message
        if (state.recentMessages.isNotEmpty() && state.overlayVisibility[OverlayType.SCROLLING_MESSAGE] == true) {
            showScrollingMessage(state.recentMessages.first())
        } else {
            hideScrollingMessage()
        }

        // Update avatar
        if (state.overlayVisibility[OverlayType.AVATAR] == true) {
            showAvatar(state.avatarMood)
        } else {
            hideAvatar()
        }

        // Update mini-game (fullscreen, blocks everything)
        if (state.activeMiniGame != null) {
            showMiniGame(state.activeMiniGame)
        } else {
            hideMiniGame()
        }
    }

    fun showScrollingMessage(message: Message) {
        if (scrollingMessageView == null) {
            scrollingMessageView = createOverlayView().apply {
                setContent {
                    ScrollingMessageOverlay(message)
                }
            }
            windowManager.addView(scrollingMessageView, createScrollingMessageParams())
        } else {
            // Update existing view
            scrollingMessageView?.setContent {
                ScrollingMessageOverlay(message)
            }
        }
    }

    fun hideScrollingMessage() {
        scrollingMessageView?.let {
            windowManager.removeView(it)
            scrollingMessageView = null
        }
    }

    fun showAvatar(mood: AvatarMood) {
        if (avatarView == null) {
            avatarView = createOverlayView().apply {
                setContent {
                    AvatarOverlay(mood)
                }
            }
            windowManager.addView(avatarView, createAvatarParams())
        } else {
            avatarView?.setContent {
                AvatarOverlay(mood)
            }
        }
    }

    fun hideAvatar() {
        avatarView?.let {
            windowManager.removeView(it)
            avatarView = null
        }
    }

    fun showMiniGame(miniGame: MiniGame) {
        if (miniGameView == null) {
            miniGameView = createOverlayView().apply {
                setContent {
                    MiniGameOverlay(miniGame)
                }
            }
            windowManager.addView(miniGameView, createMiniGameParams())
        } else {
            miniGameView?.setContent {
                MiniGameOverlay(miniGame)
            }
        }
    }

    fun hideMiniGame() {
        miniGameView?.let {
            windowManager.removeView(it)
            miniGameView = null
        }
    }

    fun hideAllOverlays() {
        hideScrollingMessage()
        hideAvatar()
        hideMiniGame()
    }

    private fun createOverlayView(): ComposeView {
        return ComposeView(context).apply {
            setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnDetachedFromWindow)
        }
    }

    private fun createScrollingMessageParams(): WindowManager.LayoutParams {
        return WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                or WindowManager.LayoutParams.FLAG_NOT_TOUCHABLE
                or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            y = 100 // Offset from top
        }
    }

    private fun createAvatarParams(): WindowManager.LayoutParams {
        return WindowManager.LayoutParams(
            200, // Width
            200, // Height
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.END
            x = 20
            y = 20
        }
    }

    private fun createMiniGameParams(): WindowManager.LayoutParams {
        return WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL
                or WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.CENTER
        }
    }
}
```

---

## Composable Overlays

### ScrollingMessageOverlay.kt
```kotlin
@Composable
fun ScrollingMessageOverlay(message: Message) {
    val context = LocalContext.current
    var offsetX by remember { mutableStateOf(0f) }

    // Each message gets random font independently
    val fontFamily = remember(message) {
        FontProvider.getRandomFontFamily(context)
    }

    // Animate scrolling from right to left
    LaunchedEffect(message) {
        offsetX = 1000f // Start off-screen right
        animate(
            initialValue = 1000f,
            targetValue = -1000f,
            animationSpec = tween(durationMillis = 8000, easing = LinearEasing)
        ) { value, _ ->
            offsetX = value
        }
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .wrapContentHeight()
            .offset { IntOffset(offsetX.toInt(), 0) }
    ) {
        Text(
            text = message.content,
            fontFamily = fontFamily,
            fontSize = 24.sp,
            color = Color.White,
            modifier = Modifier
                .background(Color.Black.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                .padding(16.dp)
        )
    }
}
```

---

### AvatarOverlay.kt
```kotlin
@Composable
fun AvatarOverlay(mood: AvatarMood) {
    val scale by animateFloatAsState(
        targetValue = when (mood) {
            AvatarMood.Excited -> 1.2f
            AvatarMood.Sad -> 0.8f
            else -> 1f
        },
        animationSpec = spring(dampingRatio = Spring.DampingRatioMediumBouncy)
    )

    Box(
        modifier = Modifier
            .size(200.dp)
            .scale(scale)
            .background(Color.Cyan.copy(alpha = 0.7f), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text = when (mood) {
                AvatarMood.Happy -> "😊"
                AvatarMood.Sad -> "😢"
                AvatarMood.Excited -> "🤩"
                AvatarMood.Angry -> "😠"
                AvatarMood.Thinking -> "🤔"
                AvatarMood.Neutral -> "😐"
            },
            fontSize = 80.sp
        )
    }
}
```

---

### MiniGameOverlay.kt
```kotlin
@Composable
fun MiniGameOverlay(miniGame: MiniGame) {
    when (miniGame.type) {
        MiniGameType.QuickMath -> QuickMathGame(miniGame.targetApp)
        MiniGameType.MemoryMatch -> MemoryMatchGame(miniGame.targetApp)
        MiniGameType.ReactionTime -> ReactionTimeGame(miniGame.targetApp)
    }
}

@Composable
fun QuickMathGame(targetApp: String) {
    var question by remember { mutableStateOf(generateMathQuestion()) }
    var userInput by remember { mutableStateOf("") }

    Box(
        modifier = Modifier
            .fillMaxSize()
            .background(Color.Black.copy(alpha = 0.9f)),
        contentAlignment = Alignment.Center
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Text(
                text = "Solve this to unlock $targetApp:",
                color = Color.White,
                fontSize = 20.sp,
                modifier = Modifier.padding(bottom = 16.dp)
            )

            Text(
                text = question.text,
                color = Color.White,
                fontSize = 40.sp,
                fontWeight = FontWeight.Bold,
                modifier = Modifier.padding(bottom = 32.dp)
            )

            TextField(
                value = userInput,
                onValueChange = { userInput = it },
                label = { Text("Your answer") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(onClick = {
                if (userInput.toIntOrNull() == question.answer) {
                    // Correct answer! Emit completion event
                    lifecycleScope.launch {
                        EventBus.emit(AppEvent.MiniGameComplete(true, targetApp))
                    }
                } else {
                    // Wrong answer, generate new question
                    question = generateMathQuestion()
                    userInput = ""
                }
            }) {
                Text("Submit")
            }
        }
    }
}

data class MathQuestion(val text: String, val answer: Int)

fun generateMathQuestion(): MathQuestion {
    val a = (1..20).random()
    val b = (1..20).random()
    val op = listOf("+", "-", "*").random()

    val answer = when (op) {
        "+" -> a + b
        "-" -> a - b
        "*" -> a * b
        else -> 0
    }

    return MathQuestion("$a $op $b = ?", answer)
}
```

---

## Touch Event Handling

### Draggable Avatar Example
```kotlin
@Composable
fun DraggableAvatarOverlay(mood: AvatarMood) {
    var offsetX by remember { mutableStateOf(0f) }
    var offsetY by remember { mutableStateOf(0f) }

    Box(
        modifier = Modifier
            .offset { IntOffset(offsetX.roundToInt(), offsetY.roundToInt()) }
            .pointerInput(Unit) {
                detectDragGestures { change, dragAmount ->
                    change.consume()
                    offsetX += dragAmount.x
                    offsetY += dragAmount.y
                }
            }
            .size(200.dp)
            .background(Color.Cyan.copy(alpha = 0.7f), CircleShape),
        contentAlignment = Alignment.Center
    ) {
        Text(text = moodToEmoji(mood), fontSize = 80.sp)
    }
}
```

---

## WindowManager.LayoutParams Flags Explained

### FLAG_NOT_FOCUSABLE
- Overlay doesn't steal focus from underlying apps
- Use for non-interactive overlays (scrolling messages, avatar)

### FLAG_NOT_TOUCHABLE
- Touch events pass through to underlying app
- Use for pure visual overlays

### FLAG_NOT_TOUCH_MODAL
- Touch events outside overlay bounds pass through
- Use for mini-games (allows tapping game UI but not underlying app)

### FLAG_LAYOUT_IN_SCREEN
- Overlay can extend into status bar / navigation bar area

---

## Overlay Lifecycle

### Creating Overlay
```
1. Check SYSTEM_ALERT_WINDOW permission granted
2. Create ComposeView with setContent { YourComposable() }
3. Create WindowManager.LayoutParams with appropriate flags
4. windowManager.addView(composeView, layoutParams)
```

### Updating Overlay
```
1. composeView.setContent { UpdatedComposable() }
   (Compose runtime handles recomposition)
```

### Destroying Overlay
```
1. windowManager.removeView(composeView)
2. composeView = null
```

---

## Error Handling

### SecurityException on addView
```kotlin
try {
    windowManager.addView(overlayView, params)
} catch (e: SecurityException) {
    // Permission revoked mid-session
    EventBus.emit(AppEvent.PermissionStateChange(Permission.SYSTEM_ALERT_WINDOW, false))
}
```

### View Already Added
```kotlin
try {
    windowManager.removeView(overlayView)
} catch (e: IllegalArgumentException) {
    // View wasn't added, ignore
}
```

---

## Performance Optimization

### Avoid Frequent Recomposition
- Use `remember` for stable state
- Use `derivedStateOf` for computed values
- Minimize Composable nesting depth

### Lazy Overlay Creation
- Don't create all overlays on startup
- Create on-demand when state requires them

### Dispose on Detach
```kotlin
composeView.setViewCompositionStrategy(
    ViewCompositionStrategy.DisposeOnDetachedFromWindow
)
```

---

## Testing

### Manual Test: Overlay Visibility
1. Grant SYSTEM_ALERT_WINDOW permission
2. Start RealityService
3. Verify scrolling message appears
4. Revoke permission via Settings
5. Verify overlay disappears gracefully

### Integration Test: State → Overlay Update
```kotlin
@Test
fun `overlay updates when new message arrives`() = runTest {
    OverlayEngine.init(context, this)

    EventBus.emit(AppEvent.NewMessage("Test message", "ai"))

    advanceUntilIdle()

    // Verify overlay shows new message (manual inspection or screenshot test)
}
```

---

## Future Enhancements

### Custom Overlay Positions
- User-configurable overlay placement (drag to reposition, save preferences)

### Overlay Themes
- Color schemes (dark mode, neon, minimal)

### Gesture Shortcuts
- Swipe to dismiss message
- Tap avatar to trigger action

### Overlay Layers
- Z-index management for multiple overlays
- Ensure mini-game always on top

---

## Dependencies

- Jetpack Compose (UI, Animation, Foundation)
- Android WindowManager
- Kotlin Coroutines
- EventBus (core module)
- StateStore (core module)
- FontProvider (fonts module)

---

## Files in This Module

- `OverlayEngine.kt` — Main overlay manager
- `composables/ScrollingMessageOverlay.kt` — Scrolling message UI
- `composables/AvatarOverlay.kt` — Avatar UI
- `composables/MiniGameOverlay.kt` — Mini-game UIs
- `composables/QuickMathGame.kt` — Math mini-game
- `composables/MemoryMatchGame.kt` — Memory mini-game
- `composables/ReactionTimeGame.kt` — Reaction mini-game
- `CLAUDE.md` — This file
