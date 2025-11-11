package com.flanergide.ai

import kotlin.random.Random

/**
 * Generates random prompts for the AI to respond to.
 * Creates variety in scrolling messages.
 */
object MessageGenerator {
    private val prompts = listOf(
        // Funny/witty prompts
        "Say something funny about cats in one sentence",
        "Give me a weird conspiracy theory in one sentence",
        "Tell me a random shower thought",
        "What's a funny observation about everyday life?",
        "Say something sarcastic about technology",
        "Give me a dad joke",
        "What's something absurd to say right now?",

        // Life tips
        "Give a random life tip in one sentence",
        "Share a piece of unconventional wisdom",
        "What's something people should know?",
        "Give advice about nothing in particular",

        // Random facts
        "Tell me a weird fact in one sentence",
        "What's something most people don't know?",
        "Share an interesting piece of trivia",
        "What's a random thing you know?",

        // Inspirational
        "Say something inspiring in one sentence",
        "Give me motivation to keep going",
        "What would you tell someone having a bad day?",

        // Abstract/creative
        "Complete this: 'The secret to happiness is...'",
        "If you were a fortune cookie, what would you say?",
        "Give me a one-sentence story",
        "What's the meaning of life? (wrong answers only)",

        // Meta
        "Say hello to the person reading this",
        "What are you thinking right now?",
        "Why are you here?",
        "Tell me something I don't know"
    )

    /**
     * Get a random prompt from the list.
     */
    fun getRandomPrompt(): String {
        return prompts.random()
    }

    /**
     * Get a prompt with a specific style/category.
     */
    fun getPromptByStyle(style: PromptStyle): String {
        return when (style) {
            PromptStyle.FUNNY -> prompts.filter { it.contains("funny") || it.contains("joke") }.random()
            PromptStyle.WISDOM -> prompts.filter { it.contains("tip") || it.contains("wisdom") }.random()
            PromptStyle.FACT -> prompts.filter { it.contains("fact") || it.contains("know") }.random()
            PromptStyle.INSPIRING -> prompts.filter { it.contains("inspir") || it.contains("motivat") }.random()
            PromptStyle.RANDOM -> prompts.random()
        }
    }

    /**
     * Generate interval for next message (in milliseconds).
     * Random between 10-30 seconds.
     */
    fun getRandomInterval(): Long {
        return Random.nextLong(10_000, 30_000)
    }
}

enum class PromptStyle {
    FUNNY, WISDOM, FACT, INSPIRING, RANDOM
}
