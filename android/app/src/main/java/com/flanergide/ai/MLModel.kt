package com.flanergide.ai

/**
 * Interface for on-device ML models.
 * Allows swapping between different model implementations (GGUF, TFLite, etc.)
 */
interface MLModel {
    /**
     * Generate text based on a prompt.
     * Runs on background thread automatically.
     *
     * @param prompt The input prompt
     * @return Generated text response
     */
    suspend fun generate(prompt: String): String

    /**
     * Optional cleanup method for releasing resources.
     */
    fun cleanup() {}
}
