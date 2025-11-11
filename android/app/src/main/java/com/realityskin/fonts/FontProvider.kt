package com.realityskin.fonts

import android.content.Context
import android.graphics.Typeface
import android.util.Log
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.Typeface as ComposeTypeface

/**
 * Simple font utility for randomly selecting fonts per message.
 * Automatically discovers fonts in assets/fonts directory.
 * Each message gets an independent random font - no global state needed.
 */
object FontProvider {
    private const val TAG = "FontProvider"
    private const val FONTS_DIR = "fonts"

    /**
     * Get list of available font files from assets/fonts directory.
     * Filters for .ttf and .otf files only.
     */
    private fun getAvailableFontPaths(context: Context): List<String> {
        return try {
            val fontFiles = context.assets.list(FONTS_DIR) ?: emptyArray()
            fontFiles
                .filter { it.endsWith(".ttf", ignoreCase = true) || it.endsWith(".otf", ignoreCase = true) }
                .map { "$FONTS_DIR/$it" }
                .also { fonts ->
                    Log.d(TAG, "Found ${fonts.size} fonts: ${fonts.joinToString()}")
                }
        } catch (e: Exception) {
            Log.e(TAG, "Error listing fonts directory", e)
            emptyList()
        }
    }

    /**
     * Returns a random Android Typeface for use with View-based rendering.
     */
    fun getRandomTypeface(context: Context): Typeface {
        val fontPaths = getAvailableFontPaths(context)
        return if (fontPaths.isEmpty()) {
            Log.w(TAG, "No fonts found, using default")
            Typeface.DEFAULT
        } else {
            val fontPath = fontPaths.random()
            try {
                Typeface.createFromAsset(context.assets, fontPath)
            } catch (e: Exception) {
                Log.e(TAG, "Error loading font: $fontPath", e)
                Typeface.DEFAULT
            }
        }
    }

    /**
     * Returns a random Compose FontFamily for use with Jetpack Compose Text.
     */
    fun getRandomFontFamily(context: Context): FontFamily {
        val fontPaths = getAvailableFontPaths(context)
        return if (fontPaths.isEmpty()) {
            Log.w(TAG, "No fonts found, using default")
            FontFamily.Default
        } else {
            val fontPath = fontPaths.random()
            try {
                val typeface = Typeface.createFromAsset(context.assets, fontPath)
                FontFamily(ComposeTypeface(typeface))
            } catch (e: Exception) {
                Log.e(TAG, "Error loading font: $fontPath", e)
                FontFamily.Default
            }
        }
    }

    /**
     * Returns all available font paths (useful for testing/debugging).
     */
    fun getAvailableFonts(context: Context): List<String> = getAvailableFontPaths(context)
}
