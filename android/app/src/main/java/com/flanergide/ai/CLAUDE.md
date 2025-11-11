# AIOrchestrator Module

## Status: ✅ IMPLEMENTED (Phase 2)

## Current Implementation
- **Model**: GGUFModel wraps llama.cpp Android library
- **Location**: `app/src/main/assets/models/phi-2-q4_k_m.gguf` (1.6 GB)
- **Generation**: Random prompts from MessageGenerator (30+ prompts)
- **Interval**: 10-30 seconds between messages
- **Fallback**: Mock responses if model loading fails
- **Validation**: Auto-detects and re-copies corrupted model files
- **Compression**: Requires `noCompress += "gguf"` in build.gradle.kts
- **NotificationListener**: Not yet implemented

## Purpose
Generate AI persona messages, moods, and behaviors based on system events and notifications.

## Features
- ✅ Run on-device LLM inference (Phi-2 Q4_K_M via llama.cpp)
- ✅ Random prompt generation and periodic message generation
- ❌ Process incoming notifications (not implemented)
- ❌ Determine avatar mood (not implemented)

---

## Architecture

### AIOrchestrator.kt
**Type**: Singleton object

**Responsibilities**:
- Subscribe to notification events
- Analyze notification content
- Generate persona messages
- Determine avatar mood
- Emit NewMessage and AvatarMoodChange events

**API**:
```kotlin
object AIOrchestrator {
    private lateinit var context: Context
    private var mlModel: MLModel? = null

    fun init(appContext: Context, scope: CoroutineScope) {
        context = appContext.applicationContext

        // Load on-device ML model (optional)
        scope.launch {
            mlModel = loadMLModel()
        }

        // Subscribe to notification events
        scope.launch {
            NotificationEventBus.notifications.collect { notification ->
                processNotification(notification)
            }
        }

        // Periodic idle messages (AI talks even without notifications)
        scope.launch {
            while (isActive) {
                delay(60_000) // Every 60 seconds
                generateIdleMessage()
            }
        }
    }

    private suspend fun processNotification(notification: StatusBarNotification) {
        val content = notification.notification.extras.getString(Notification.EXTRA_TEXT) ?: return
        val appName = notification.packageName

        // Generate AI response
        val message = generateResponse(content, appName)
        EventBus.emit(AppEvent.NewMessage(message, appName))

        // Determine mood based on content
        val mood = analyzeSentiment(content)
        EventBus.emit(AppEvent.AvatarMoodChange(mood))
    }

    private suspend fun generateResponse(notificationContent: String, appName: String): String {
        return when {
            mlModel != null -> {
                // Use on-device model
                mlModel!!.generate("Notification from $appName: $notificationContent")
            }
            else -> {
                // Fallback to rule-based responses
                generateMockResponse(notificationContent, appName)
            }
        }
    }

    private fun generateMockResponse(content: String, appName: String): String {
        return when {
            appName.contains("gmail") -> "You've got mail! 📧"
            appName.contains("instagram") -> "Someone's living their best life 📸"
            appName.contains("slack") -> "Work never sleeps 💼"
            content.contains("meeting", ignoreCase = true) -> "Time to pretend you're listening 🎧"
            content.contains("payment", ignoreCase = true) -> "Money moves 💸"
            else -> "Something happened! 🤷"
        }
    }

    private fun analyzeSentiment(content: String): AvatarMood {
        return when {
            content.contains("congratulations", ignoreCase = true) -> AvatarMood.Excited
            content.contains("error", ignoreCase = true) -> AvatarMood.Sad
            content.contains("alert", ignoreCase = true) -> AvatarMood.Thinking
            content.contains("like", ignoreCase = true) -> AvatarMood.Happy
            else -> AvatarMood.Neutral
        }
    }

    private suspend fun generateIdleMessage() {
        val messages = listOf(
            "Just vibing...",
            "Nothing to see here",
            "Still alive!",
            "Bored yet?",
            "👀",
            "..."
        )
        EventBus.emit(AppEvent.NewMessage(messages.random(), "system"))
    }

    private suspend fun loadMLModel(): MLModel? = withContext(Dispatchers.IO) {
        try {
            // Load GGUF model from assets
            GGUFModel(context)
        } catch (e: Exception) {
            Log.e("AIOrchestrator", "Failed to load GGUF model, using mock responses", e)
            null
        }
    }
}

interface MLModel {
    suspend fun generate(prompt: String): String
    fun cleanup() {} // Optional cleanup method
}
```

---

## NotificationListenerService Integration

### RealityNotificationListener.kt
```kotlin
class RealityNotificationListener : NotificationListenerService() {

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        super.onNotificationPosted(sbn)

        // Filter out system/unimportant notifications
        if (shouldIgnore(sbn)) return

        // Emit notification to internal event bus
        lifecycleScope.launch {
            NotificationEventBus.emit(sbn)
        }
    }

    private fun shouldIgnore(sbn: StatusBarNotification): Boolean {
        return when {
            sbn.packageName == packageName -> true // Ignore own notifications
            sbn.notification.flags and Notification.FLAG_ONGOING_EVENT != 0 -> true // Ignore persistent
            sbn.notification.group == "silent" -> true
            else -> false
        }
    }
}

object NotificationEventBus {
    private val _notifications = MutableSharedFlow<StatusBarNotification>(
        replay = 0,
        extraBufferCapacity = 16
    )
    val notifications: SharedFlow<StatusBarNotification> = _notifications.asSharedFlow()

    suspend fun emit(notification: StatusBarNotification) {
        _notifications.emit(notification)
    }
}
```

---

## Event Flow

### Notification → AI Message
```
1. User receives Gmail notification
2. RealityNotificationListener.onNotificationPosted() triggered
3. Listener emits notification to NotificationEventBus
4. AIOrchestrator subscribes, receives notification
5. AIOrchestrator.generateResponse() → "You've got mail! 📧"
6. AIOrchestrator emits NewMessage("You've got mail! 📧", "gmail")
7. StateStore updates appState.recentMessages
8. OverlayEngine subscribes → shows scrolling message
```

### Sentiment → Mood Change
```
1. AIOrchestrator.analyzeSentiment("Congratulations!") → AvatarMood.Excited
2. AIOrchestrator emits AvatarMoodChange(AvatarMood.Excited)
3. StateStore updates appState.avatarMood
4. OverlayEngine subscribes → avatar scales up with excitement animation
```

---

## On-Device ML Options

### Option 1: GGUF + llama.cpp (RECOMMENDED)
- **Model**: Phi-2 quantized to Q4_K_M (1.6 GB)
- **Format**: GGUF (GPT-Generated Unified Format)
- **Performance**: ~100-300ms inference on modern devices
- **Quality**: High-quality 2.7B parameter model

**Model Location**:
```
app/src/main/assets/models/phi-2-q4_k_m.gguf
```

**Setup**:
```kotlin
class GGUFModel(context: Context) : MLModel {
    private var llamaCppContext: Long = 0
    private val modelPath: String

    init {
        // Copy model from assets to internal storage if needed
        modelPath = copyAssetToInternal(context, "models/phi-2-q4_k_m.gguf")

        // Initialize llama.cpp context
        llamaCppContext = llamaCppInit(modelPath)
    }

    override suspend fun generate(prompt: String): String = withContext(Dispatchers.Default) {
        if (llamaCppContext == 0L) {
            return "Model not loaded"
        }

        // Run inference using llama.cpp JNI bindings
        val fullPrompt = buildPrompt(prompt)
        val response = llamaCppGenerate(llamaCppContext, fullPrompt, maxTokens = 100)

        return response.trim()
    }

    private fun buildPrompt(userInput: String): String {
        // Phi-2 prompt format
        return """Instruct: You are a sarcastic AI assistant. Generate a short, witty response.
User: $userInput
Output:"""
    }

    private fun copyAssetToInternal(context: Context, assetPath: String): String {
        val outputFile = File(context.filesDir, assetPath)
        if (!outputFile.exists()) {
            outputFile.parentFile?.mkdirs()
            context.assets.open(assetPath).use { input ->
                outputFile.outputStream().use { output ->
                    input.copyTo(output)
                }
            }
        }
        return outputFile.absolutePath
    }

    // JNI bindings to llama.cpp (implement in C++)
    private external fun llamaCppInit(modelPath: String): Long
    private external fun llamaCppGenerate(ctx: Long, prompt: String, maxTokens: Int): String
    private external fun llamaCppFree(ctx: Long)

    fun cleanup() {
        if (llamaCppContext != 0L) {
            llamaCppFree(llamaCppContext)
            llamaCppContext = 0L
        }
    }
}
```

**JNI Implementation** (C++ side):
```cpp
// src/main/cpp/llama_jni.cpp
#include <jni.h>
#include "llama.h"

extern "C" JNIEXPORT jlong JNICALL
Java_com_flanergide_ai_GGUFModel_llamaCppInit(JNIEnv* env, jobject, jstring modelPath) {
    const char* path = env->GetStringUTFChars(modelPath, nullptr);

    llama_model_params model_params = llama_model_default_params();
    llama_model* model = llama_load_model_from_file(path, model_params);

    env->ReleaseStringUTFChars(modelPath, path);
    return reinterpret_cast<jlong>(model);
}

extern "C" JNIEXPORT jstring JNICALL
Java_com_flanergide_ai_GGUFModel_llamaCppGenerate(JNIEnv* env, jobject, jlong ctx, jstring prompt, jint maxTokens) {
    llama_model* model = reinterpret_cast<llama_model*>(ctx);
    const char* promptStr = env->GetStringUTFChars(prompt, nullptr);

    // Run inference (simplified)
    // ... (see llama.cpp examples for full implementation)

    std::string response = "Generated response from Phi-2";

    env->ReleaseStringUTFChars(prompt, promptStr);
    return env->NewStringUTF(response.c_str());
}
```

**CMakeLists.txt**:
```cmake
cmake_minimum_required(VERSION 3.18.1)
project("flanergide")

add_library(flanergide SHARED llama_jni.cpp)

# Link llama.cpp
add_subdirectory(llama.cpp)
target_link_libraries(flanergide llama)
```

**Alternative: Use llama.cpp-java Wrapper**:
Instead of writing JNI, use existing wrapper:
```gradle
dependencies {
    implementation 'de.kherud:llama:2.0.0' // llama.cpp Java wrapper
}
```

```kotlin
class GGUFModel(context: Context) : MLModel {
    private val model: LlamaModel

    init {
        val modelPath = copyAssetToInternal(context, "models/phi-2-q4_k_m.gguf")
        model = LlamaModel(modelPath)
    }

    override suspend fun generate(prompt: String): String = withContext(Dispatchers.Default) {
        val params = InferenceParameters()
            .setNPredict(100)
            .setTemperature(0.7f)

        val fullPrompt = "Instruct: $prompt\nOutput:"
        return model.generate(fullPrompt, params)
    }
}
```

---

### Option 2: TensorFlow Lite
- Small language models (< 100MB)
- GPT-2 or DistilGPT variants
- Inference latency: 100-500ms

**Setup**:
```kotlin
class TFLiteModel(context: Context) : MLModel {
    private val interpreter: Interpreter

    init {
        val model = FileUtil.loadMappedFile(context, "model.tflite")
        interpreter = Interpreter(model)
    }

    override suspend fun generate(prompt: String): String = withContext(Dispatchers.Default) {
        // Tokenize input
        // Run inference
        // Decode output
        "Generated response"
    }
}
```

### Option 3: Gemini Nano (On-Device)
- Google's on-device LLM (if available)
- Requires Android 14+ and compatible device

### Option 4: Rule-Based + Templates
- No ML, just pattern matching + response templates
- Fast, lightweight, predictable
- Good for MVP

**Example**:
```kotlin
fun generateRuleBasedResponse(notification: String): String {
    return when {
        notification.matches(Regex(".*\\d{6}.*")) -> "That's your OTP code, don't share it!"
        notification.contains("delivery") -> "Package incoming! 📦"
        notification.contains("battery") -> "Charge me up! 🔋"
        else -> "Interesting... 🤔"
    }
}
```

---

## Persona Customization

### User-Defined Personality
```kotlin
data class PersonaConfig(
    val name: String = "Reality",
    val personality: Personality = Personality.Sarcastic,
    val responseFrequency: ResponseFrequency = ResponseFrequency.Medium
)

enum class Personality {
    Friendly, Sarcastic, Professional, Chaotic
}

enum class ResponseFrequency {
    Low, // Only important notifications
    Medium, // Most notifications
    High // Every notification + idle messages
}

fun generatePersonalizedResponse(content: String, config: PersonaConfig): String {
    return when (config.personality) {
        Personality.Friendly -> "Hey friend! $content"
        Personality.Sarcastic -> "Oh wow, $content. Riveting."
        Personality.Professional -> "Notification received: $content"
        Personality.Chaotic -> "${content.uppercase()} !!! 🔥🔥🔥"
    }
}
```

---

## Advanced Features

### Contextual Awareness
```kotlin
suspend fun generateContextualMessage(notification: StatusBarNotification): String {
    val timeOfDay = Calendar.getInstance().get(Calendar.HOUR_OF_DAY)
    val appName = notification.packageName

    return when {
        timeOfDay in 0..5 && appName.contains("slack") -> "Working at 3am? You good?"
        timeOfDay in 12..13 -> "Lunch break notification? Priorities."
        else -> generateResponse(notification.content, appName)
    }
}
```

### Learning from User Behavior
```kotlin
// Track which messages user dismisses quickly vs. reads
suspend fun logUserInteraction(message: Message, interactionTime: Long) {
    // Store in database
    // Adjust future message generation based on preferences
}
```

### Multi-Modal Input
```kotlin
// Process notification images/icons
fun analyzeNotificationImage(bitmap: Bitmap): String {
    // Use image classification model
    // Generate message based on visual content
    return "I see a cat! 🐱"
}
```

---

## Settings UI Integration

```kotlin
@Composable
fun AIPersonaSettings() {
    var personaConfig by remember { mutableStateOf(PersonaConfig()) }

    Column {
        TextField(
            value = personaConfig.name,
            onValueChange = { personaConfig = personaConfig.copy(name = it) },
            label = { Text("Persona Name") }
        )

        Text("Personality:")
        Personality.values().forEach { personality ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                RadioButton(
                    selected = personaConfig.personality == personality,
                    onClick = { personaConfig = personaConfig.copy(personality = personality) }
                )
                Text(personality.name)
            }
        }

        Button(onClick = {
            lifecycleScope.launch {
                savePersonaConfig(personaConfig)
            }
        }) {
            Text("Save")
        }
    }
}
```

---

## Error Handling

### Model Loading Failure
```kotlin
init {
    scope.launch {
        mlModel = try {
            loadMLModel()
        } catch (e: Exception) {
            Log.e("AIOrchestrator", "Failed to load ML model, using mock responses", e)
            null
        }
    }
}
```

### Notification Processing Error
```kotlin
private suspend fun processNotification(notification: StatusBarNotification) {
    try {
        val content = extractContent(notification)
        val message = generateResponse(content, notification.packageName)
        EventBus.emit(AppEvent.NewMessage(message, notification.packageName))
    } catch (e: Exception) {
        Log.e("AIOrchestrator", "Failed to process notification", e)
        // Don't crash, just skip this notification
    }
}
```

---

## Performance Considerations

### Async Processing
- Run ML inference on background thread (`Dispatchers.Default`)
- Don't block notification processing

### Model Warm-Up
```kotlin
fun warmUpModel() {
    lifecycleScope.launch(Dispatchers.Default) {
        mlModel?.generate("warmup prompt")
    }
}
```

### Rate Limiting
```kotlin
private var lastMessageTime = 0L
private val minMessageInterval = 3000L // 3 seconds

suspend fun generateIdleMessage() {
    val now = System.currentTimeMillis()
    if (now - lastMessageTime < minMessageInterval) return

    lastMessageTime = now
    EventBus.emit(AppEvent.NewMessage("...", "system"))
}
```

---

## Testing

### Unit Test: Sentiment Analysis
```kotlin
@Test
fun `analyzeSentiment returns Happy for positive content`() {
    val mood = AIOrchestrator.analyzeSentiment("You got a like!")
    assertEquals(AvatarMood.Happy, mood)
}
```

### Integration Test: Notification → Message
```kotlin
@Test
fun `processNotification emits NewMessage event`() = runTest {
    val events = mutableListOf<AppEvent>()
    launch {
        EventBus.events.collect { events.add(it) }
    }

    val notification = mockNotification("Test message", "com.test")
    AIOrchestrator.processNotification(notification)

    advanceUntilIdle()
    assertTrue(events.any { it is AppEvent.NewMessage })
}
```

---

## Privacy Considerations

### Notification Content
- Don't log notification content to external servers
- Keep all processing on-device
- Allow user to blacklist sensitive apps (banking, messaging)

### User Control
```kotlin
data class PrivacySettings(
    val blacklistedApps: Set<String> = emptySet(),
    val enableLogging: Boolean = false
)

fun shouldProcessNotification(sbn: StatusBarNotification, settings: PrivacySettings): Boolean {
    return sbn.packageName !in settings.blacklistedApps
}
```

---

## Future Enhancements

### Voice Output
- Text-to-speech for AI messages
- Different voices per personality

### Proactive Suggestions
- "You've been on Instagram for 2 hours, maybe take a break?"

### Multi-Agent Conversations
- Multiple AI personas with different personalities
- They talk to each other in overlays

---

## Dependencies

- NotificationListenerService (Android framework)
- Kotlin Coroutines
- **llama.cpp** (for GGUF model inference) - RECOMMENDED
  - Option A: Direct JNI bindings to llama.cpp (C++)
  - Option B: `de.kherud:llama:2.0.0` (Java wrapper)
- Optional: TensorFlow Lite
- Optional: Google ML Kit
- EventBus (core module)
- StateStore (core module)

**Model Asset**:
- `app/src/main/assets/models/phi-2-q4_k_m.gguf` (1.6 GB)
- Phi-2 quantized to Q4_K_M format
- See top-level `CLAUDE.md` for model conversion instructions

---

## GGUFModel Implementation Details

### File Validation and Auto-Recovery

The current `GGUFModel.kt` implementation includes:

1. **Size Validation**: Checks if model file is ~1620 MB (±5%)
2. **Corruption Detection**: Auto-detects incomplete/corrupted files
3. **Auto-Recovery**: Deletes and re-copies corrupted files automatically
4. **Progress Logging**: Logs copy progress every 100 MB

**Example logs**:
```
✅ Model file exists, size: 769.25 MB
❌ File size mismatch! Expected ~1620 MB, got 769.25 MB (52.5% difference)
🗑️ Deleting corrupted file and re-copying from assets...
📊 Copied 100 MB / 1620 MB (6.2%)
✅ Copy verification passed
```

### Token Limit Configuration

The `LLamaAndroid.send()` method accepts a `maxTokens` parameter to control response length:

**Default Configuration**:
```kotlin
llama.send(prompt, formatChat = false, maxTokens = 128)
```

**Token Limits**:
- **Default**: 256 tokens (set in `LLamaAndroid.kt`)
- **RealitySkin**: 128 tokens (used in `GGUFModel.kt`)
  - ~1-2 sentences for Jill Stingray responses
  - Faster inference (~3-5 seconds on modern devices)
  - Lower memory usage

**Adjusting Token Limit**:
```kotlin
// For longer responses (3-4 sentences)
llama.send(prompt, formatChat = false, maxTokens = 256)

// For very short responses (1 sentence)
llama.send(prompt, formatChat = false, maxTokens = 64)
```

**Performance Impact**:
- 64 tokens: ~2-3 seconds
- 128 tokens: ~3-5 seconds
- 256 tokens: ~5-10 seconds
- 512 tokens: ~10-20 seconds

**Note**: The original hardcoded limit was 64 tokens, which was too short and caused empty responses. This has been fixed.

### Build Configuration Requirement

**CRITICAL**: Add to `app/build.gradle.kts`:

```kotlin
android {
    // Prevent compression of GGUF model files
    androidResources {
        noCompress += "gguf"
    }
}
```

Without this, you'll see:
```
❌ This file can not be opened as a file descriptor; it is probably compressed
```

### Error Handling

- **Asset missing**: Throws `IllegalStateException` with clear error message
- **Corrupted file**: Auto-deletes and re-copies from assets
- **Load failure**: Falls back to mock message generation
- **Comprehensive logging**: All steps logged with emojis for easy debugging

---

## Files in This Module

- `AIOrchestrator.kt` — Main AI logic
- `RealityNotificationListener.kt` — Notification listener service
- `NotificationEventBus.kt` — Internal notification event bus
- `PersonaConfig.kt` — Persona configuration data classes
- `MLModel.kt` — ML model interface
- `GGUFModel.kt` — GGUF/llama.cpp implementation (RECOMMENDED)
- `TFLiteModel.kt` — TensorFlow Lite implementation (optional)
- `CLAUDE.md` — This file

**Native Code** (if using JNI):
- `src/main/cpp/llama_jni.cpp` — JNI bindings to llama.cpp
- `src/main/cpp/CMakeLists.txt` — Build configuration
