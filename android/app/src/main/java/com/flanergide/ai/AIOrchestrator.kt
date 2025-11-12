package com.flanergide.ai

import android.app.Application
import android.content.Context
import android.util.Log
import com.flanergide.core.AppEvent
import com.flanergide.core.EventBus
import com.flanergide.core.StateStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

/**
 * AI Orchestrator - manages on-device LLM and generates scrolling messages.
 *
 * Responsibilities:
 * - Initialize and load GGUF model
 * - Generate messages from random prompts
 * - Emit NewMessage events via EventBus
 * - Manage generation timing and state
 */
object AIOrchestrator {
    private const val TAG = "AIOrchestrator"

    // Using Application instead of Context to avoid lint warning
    private lateinit var application: Application
    private var mlModel: MLModel? = null
    private var isGenerating = false
    private var isEnabled = false

    /**
     * Initialize AIOrchestrator.
     * Loads the GGUF model from assets (takes 5-10 seconds).
     *
     * @param appContext Application context
     * @param scope CoroutineScope for background tasks
     */
    fun init(appContext: Context, scope: CoroutineScope) {
        application = appContext.applicationContext as Application
        Log.i(TAG, "Initializing AIOrchestrator")

        // Subscribe to LLM enabled state changes
        scope.launch {
            StateStore.appState.collect { state ->
                isEnabled = state.llmEnabled
                Log.d(TAG, "LLM ${if (isEnabled) "enabled" else "disabled"}")
            }
        }

        // Load model asynchronously
        scope.launch {
            try {
                Log.i(TAG, "🔄 Starting GGUF model initialization...")
                Log.i(TAG, "📝 Step 1: Creating GGUFModel instance")
                val model = GGUFModel(application)

                Log.i(TAG, "📝 Step 2: Loading model into memory")
                model.load()

                Log.i(TAG, "📝 Step 3: Storing model reference")
                mlModel = model

                Log.i(TAG, "✅ GGUF model fully loaded and ready!")
                Log.i(TAG, "🎉 Will use real LLM for message generation")

                // Start periodic message generation
                startPeriodicGeneration(scope)
            } catch (e: Exception) {
                Log.e(TAG, "❌ Failed to load GGUF model: ${e.javaClass.simpleName}", e)
                Log.e(TAG, "❌ Error message: ${e.message}")
                Log.w(TAG, "⚠️ Falling back to mock message generation")
                mlModel = null

                // Start periodic mock messages as fallback
                startPeriodicGeneration(scope)
            }
        }
    }

    /**
     * Start generating messages on a timer.
     * Interval: 10-30 seconds (randomized).
     */
    private fun startPeriodicGeneration(scope: CoroutineScope) {
        Log.i(TAG, "Starting periodic message generation")

        scope.launch {
            // Wait a bit before first message
            delay(5000)

            while (isActive) {
                if (!isGenerating) {
                    generateAndEmitMessage()
                }

                // Wait random interval before next message
                val interval = MessageGenerator.getRandomInterval()
                Log.d(TAG, "Next message in ${interval / 1000}s")
                delay(interval)
            }
        }
    }

    /**
     * Generate a message from a random prompt and emit to EventBus.
     */
    private suspend fun generateAndEmitMessage() {
        // Skip generation if LLM is disabled
        if (!isEnabled) return

        isGenerating = true

        try {
            val prompt = MessageGenerator.getRandomPrompt()
            Log.d(TAG, "Generating message for prompt: $prompt")

            val message = if (mlModel != null) {
                // Use real LLM
                Log.i(TAG, "🤖 Using ML model to generate response")
                mlModel!!.generate(prompt)
            } else {
                // Fallback to mock responses
                Log.w(TAG, "⚠️ ML model not loaded, using mock response")
                generateMockResponse(prompt)
            }

            // Emit message event
            EventBus.emit(AppEvent.NewMessage(
                content = message,
                source = "ai"
            ))

            Log.i(TAG, "✅ Message emitted: ${message.take(50)}...")
        } catch (e: Exception) {
            Log.e(TAG, "❌ Failed to generate message", e)

            // Emit error message
            EventBus.emit(AppEvent.NewMessage(
                content = "🤖 AI brain fart...",
                source = "ai"
            ))
        } finally {
            isGenerating = false
        }
    }

    /**
     * Fallback mock responses when LLM is not available.
     */
    private fun generateMockResponse(prompt: String): String {
        return when {
            prompt.contains("funny") || prompt.contains("joke") -> {
                listOf(
                    "Why don't scientists trust atoms? Because they make up everything! 😄",
                    "Parallel lines have so much in common. It's a shame they'll never meet.",
                    "I told my wife she was drawing her eyebrows too high. She looked surprised.",
                    "Why don't cats play poker in the jungle? Too many cheetahs! 🐱"
                ).random()
            }

            prompt.contains("tip") || prompt.contains("advice") -> {
                listOf(
                    "💡 Pro tip: CTRL+Z works in real life if you move fast enough",
                    "Remember: Your vibe attracts your tribe ✨",
                    "Coffee first, adulting second ☕",
                    "Be yourself. Unless you can be a dinosaur. Then be a dinosaur. 🦖"
                ).random()
            }

            prompt.contains("fact") || prompt.contains("know") -> {
                listOf(
                    "🧠 Bananas are berries, but strawberries aren't. Wild.",
                    "Octopuses have three hearts and blue blood 🐙",
                    "A group of flamingos is called a 'flamboyance' 💅",
                    "Honey never spoils. You could eat 3000-year-old honey! 🍯"
                ).random()
            }

            prompt.contains("inspir") || prompt.contains("motivat") -> {
                listOf(
                    "✨ You're doing better than you think",
                    "🌟 Small progress is still progress",
                    "💪 You got this!",
                    "🚀 Dream big, start small, but most of all... start"
                ).random()
            }

            else -> {
                listOf(
                    "🤔 Interesting question...",
                    "🎲 Random thought incoming...",
                    "👀 Did you know...",
                    "💭 Here's a thing...",
                    "🌈 Life is weird, embrace it"
                ).random()
            }
        }
    }

    /**
     * Cleanup resources.
     */
    suspend fun cleanup() {
        Log.i(TAG, "Cleaning up AIOrchestrator")
        (mlModel as? GGUFModel)?.unload()
        mlModel = null
    }
}
