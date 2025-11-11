package com.realityskin.ai

import android.content.Context
import android.llama.cpp.LLamaAndroid
import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.fold
import kotlinx.coroutines.withContext
import java.io.File
import java.io.FileNotFoundException

/**
 * GGUF model implementation using llama.cpp Android library.
 * Wraps the Phi-2 Q4_K_M quantized model.
 */
class GGUFModel(context: Context) : MLModel {
    private val tag = "GGUFModel"
    private val llama = LLamaAndroid.instance()
    private val modelPath: String

    init {
        Log.i(tag, "🔧 Initializing GGUFModel")

        // Copy model from assets to internal storage
        modelPath = copyModelFromAssets(context)

        Log.i(tag, "✅ Model path ready: $modelPath")

        // Verify file exists
        val modelFile = File(modelPath)
        if (modelFile.exists()) {
            val sizeInMB = modelFile.length() / (1024.0 * 1024.0)
            Log.i(tag, "✅ Model file exists, size: %.2f MB".format(sizeInMB))
        } else {
            Log.e(tag, "❌ Model file NOT found at $modelPath")
        }
    }

    /**
     * Load the model into memory.
     * Call this once during initialization (can take 5-10 seconds).
     */
    suspend fun load() {
        withContext(Dispatchers.IO) {
            try {
                Log.i(tag, "🚀 Starting model load...")
                Log.i(tag, "📂 Model path: $modelPath")

                // Verify file still exists before loading
                val modelFile = File(modelPath)
                if (!modelFile.exists()) {
                    Log.e(tag, "❌ Model file disappeared before load!")
                    throw IllegalStateException("Model file not found at $modelPath")
                }

                Log.i(tag, "📊 Model file size: ${modelFile.length() / (1024 * 1024)} MB")
                Log.i(tag, "⏳ Loading model into memory (this may take 5-10 seconds)...")

                val startTime = System.currentTimeMillis()
                llama.load(modelPath)
                val duration = System.currentTimeMillis() - startTime

                Log.i(tag, "✅ Model loaded successfully in ${duration}ms (${duration / 1000.0}s)")
            } catch (e: Exception) {
                Log.e(tag, "❌ Failed to load model: ${e.javaClass.simpleName}", e)
                Log.e(tag, "❌ Error message: ${e.message}")
                Log.e(tag, "❌ Stack trace:", e)
                throw e
            }
        }
    }

    /**
     * Generate text from a prompt.
     * Returns the complete generated text (collects the entire flow).
     */
    override suspend fun generate(prompt: String): String {
        return withContext(Dispatchers.IO) {
            try {
                Log.i(tag, "🎯 Generating response for prompt: ${prompt.take(50)}...")
                val startTime = System.currentTimeMillis()

                // Format prompt with Jill Stingray persona
                val formattedPrompt = formatPromptWithPersona(prompt)

                // Collect the entire flow of generated tokens
                // maxTokens=128 is enough for 1-2 sentences
                val response = llama.send(formattedPrompt, formatChat = false, maxTokens = 128)
                    .catch { e ->
                        Log.e(tag, "❌ Error during generation stream", e)
                        emit("Error: ${e.message}")
                    }
                    .fold("") { acc, token -> acc + token }

                val duration = System.currentTimeMillis() - startTime
                Log.i(tag, "✅ Generation complete in ${duration}ms (${duration / 1000.0}s)")
                Log.d(tag, "📝 Response preview: ${response.take(100)}...")

                response.trim()
            } catch (e: Exception) {
                Log.e(tag, "❌ Failed to generate text: ${e.javaClass.simpleName}", e)
                Log.e(tag, "❌ Error message: ${e.message}")
                "Error generating response"
            }
        }
    }

    /**
     * Format the input prompt with the Jill Stingray persona.
     * Wraps the input string in character context and instructions.
     *
     * Uses Phi-2 compatible format with clear completion trigger.
     */
    private fun formatPromptWithPersona(inputString: String): String {
        return """Instruct: You are Jill Stingray, a 27-year-old bartender at VA-11 Hall-A in Glitch City. You have dry wit, measured calm, and weary kindness. You've seen strange things and strange people. You keep conversations light with sarcasm, but listen when things get real. React to this in 1-2 short sentences as Jill: $inputString
Output:"""
    }

    /**
     * Unload the model and free resources.
     */
    override fun cleanup() {
        Log.i(tag, "Cleaning up GGUF model")
        // Note: Unload is suspend, but cleanup is not
        // Will be called from a coroutine context by AIOrchestrator
    }

    suspend fun unload() {
        llama.unload()
    }

    /**
     * Copy the GGUF model from assets to internal storage.
     * Only copies if file doesn't already exist.
     *
     * @return Path to the copied model file
     */
    private fun copyModelFromAssets(context: Context): String {
        val assetPath = "models/phi-2-q4_k_m.gguf"
        val outputFile = File(context.filesDir, assetPath)
        val expectedSizeInMB = 1620.0 // ~1.6 GB

        Log.i(tag, "📂 Target file path: ${outputFile.absolutePath}")

        // Check if existing file is corrupted (wrong size)
        if (outputFile.exists()) {
            val existingSizeInMB = outputFile.length() / (1024.0 * 1024.0)
            Log.i(tag, "✅ Model file exists at ${outputFile.absolutePath}")
            Log.i(tag, "📊 Existing file size: %.2f MB".format(existingSizeInMB))

            // Validate file size (should be close to expected size)
            val sizeDiffPercent = Math.abs(existingSizeInMB - expectedSizeInMB) / expectedSizeInMB * 100
            if (sizeDiffPercent > 5) { // More than 5% difference
                Log.e(tag, "❌ File size mismatch! Expected ~%.0f MB, got %.2f MB (%.1f%% difference)".format(
                    expectedSizeInMB, existingSizeInMB, sizeDiffPercent))
                Log.w(tag, "🗑️ Deleting corrupted file and re-copying from assets...")
                outputFile.delete()
            } else {
                Log.i(tag, "✅ File size validation passed")
                return outputFile.absolutePath
            }
        }

        if (!outputFile.exists()) {
            Log.i(tag, "📥 Model not found in internal storage, copying from assets...")
            Log.i(tag, "📦 Asset path: $assetPath")
            Log.i(tag, "⏳ Copying 1.6 GB model (this may take 1-2 minutes)...")

            try {
                // Create parent directories
                outputFile.parentFile?.let { parent ->
                    if (!parent.exists()) {
                        Log.i(tag, "📁 Creating directory: ${parent.absolutePath}")
                        val created = parent.mkdirs()
                        Log.i(tag, if (created) "✅ Directory created" else "⚠️ Directory already exists or failed to create")
                    }
                }

                // Check if asset exists and get its size
                val assetList = context.assets.list("models")
                Log.i(tag, "📋 Files in models/ directory: ${assetList?.joinToString()}")

                // Try to get asset file size (may fail if compressed)
                try {
                    val assetFd = context.assets.openFd(assetPath)
                    val assetSizeInMB = assetFd.length / (1024.0 * 1024.0)
                    assetFd.close()

                    Log.i(tag, "📦 Asset file size: %.2f MB".format(assetSizeInMB))

                    // Validate asset file size before copying
                    val assetSizeDiffPercent = Math.abs(assetSizeInMB - expectedSizeInMB) / expectedSizeInMB * 100
                    if (assetSizeDiffPercent > 5) {
                        Log.e(tag, "❌ Asset file size is incorrect! Expected ~%.0f MB, got %.2f MB".format(
                            expectedSizeInMB, assetSizeInMB))
                        Log.e(tag, "❌ The model file in assets is corrupted or incomplete!")
                        Log.e(tag, "💡 Please check app/src/main/assets/models/phi-2-q4_k_m.gguf")
                        throw IllegalStateException("Asset model file is corrupted (size: %.2f MB, expected: %.0f MB)".format(
                            assetSizeInMB, expectedSizeInMB))
                    }
                } catch (e: FileNotFoundException) {
                    // File is compressed, can't check size via openFd()
                    Log.w(tag, "⚠️ Asset file appears to be compressed, cannot pre-validate size")
                    Log.w(tag, "⚠️ If you see this, make sure build.gradle has: androidResources { noCompress += \"gguf\" }")
                    Log.i(tag, "📦 Will proceed with copy and validate after...")
                }

                val startTime = System.currentTimeMillis()
                var bytesCopied = 0L
                var lastLoggedMB = 0L

                context.assets.open(assetPath).use { input ->
                    outputFile.outputStream().use { output ->
                        val buffer = ByteArray(8192)
                        var bytes: Int
                        while (input.read(buffer).also { bytes = it } >= 0) {
                            output.write(buffer, 0, bytes)
                            bytesCopied += bytes

                            // Log progress every 100 MB
                            val currentMB = bytesCopied / (1024 * 1024)
                            if (currentMB - lastLoggedMB >= 100) {
                                Log.i(tag, "📊 Copied $currentMB MB / %.0f MB (%.1f%%)".format(
                                    expectedSizeInMB, (currentMB / expectedSizeInMB) * 100))
                                lastLoggedMB = currentMB
                            }
                        }
                    }
                }

                val duration = System.currentTimeMillis() - startTime
                val sizeInMB = bytesCopied / (1024.0 * 1024.0)

                Log.i(tag, "✅ Model copy complete: ${outputFile.absolutePath}")
                Log.i(tag, "✅ Copied %.2f MB in %.2f seconds".format(sizeInMB, duration / 1000.0))

                // Verify copied file size
                val copiedSizeInMB = outputFile.length() / (1024.0 * 1024.0)
                val copiedSizeDiffPercent = Math.abs(copiedSizeInMB - expectedSizeInMB) / expectedSizeInMB * 100
                if (copiedSizeDiffPercent > 5) {
                    Log.e(tag, "❌ Copy verification failed! Expected ~%.0f MB, got %.2f MB".format(
                        expectedSizeInMB, copiedSizeInMB))
                    outputFile.delete()
                    throw IllegalStateException("Model copy failed verification")
                } else {
                    Log.i(tag, "✅ Copy verification passed")
                }
            } catch (e: Exception) {
                Log.e(tag, "❌ Failed to copy model from assets", e)
                Log.e(tag, "❌ Error: ${e.message}")
                throw e
            }
        }

        return outputFile.absolutePath
    }
}
