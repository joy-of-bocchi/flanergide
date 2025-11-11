package com.realityskin.data

/**
 * CapturedText - Immutable container for a captured text event.
 *
 * Represents a single text capture from any app, already redacted.
 */
data class CapturedText(
    val text: String,           // Redacted text content
    val appPackage: String,     // Source app (e.g., "com.instagram.android")
    val timestamp: Long         // System.currentTimeMillis()
)
