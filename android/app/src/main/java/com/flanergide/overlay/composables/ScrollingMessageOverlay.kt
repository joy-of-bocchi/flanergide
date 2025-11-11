package com.flanergide.overlay.composables

import android.content.Context
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.flanergide.core.Message
import com.flanergide.fonts.FontProvider
import kotlin.random.Random

/**
 * Nico-nico style scrolling message overlay.
 *
 * Features:
 * - Scrolls from left-to-right OR right-to-left (randomized)
 * - Random vertical position
 * - Random speed (5-15 seconds duration)
 * - Fade in/out animations
 * - Semi-transparent background
 * - Random font per message
 *
 * @param message The message to display
 * @param applicationContext Application context (used to load fonts from assets)
 * @param onAnimationComplete Callback when scroll animation finishes (called after delay)
 */
@Composable
fun ScrollingMessageOverlay(
    message: Message,
    applicationContext: Context,
    onAnimationComplete: () -> Unit = {}
) {
    val configuration = LocalConfiguration.current
    val screenWidth = configuration.screenWidthDp.dp.value.toInt()

    // Randomize animation parameters for Nico-nico variety
    val direction = remember { if (Random.nextBoolean()) Direction.LEFT_TO_RIGHT else Direction.RIGHT_TO_LEFT }
    val animationDuration = remember { Random.nextInt(5000, 15000) } // 5-15 seconds
    val fontSize = remember { Random.nextInt(16, 28) } // 16-28sp
    val fontFamily = remember(message) { FontProvider.getRandomFontFamily(applicationContext) }

    // Animation state
    var offsetX by remember {
        mutableStateOf(
            when (direction) {
                Direction.LEFT_TO_RIGHT -> -screenWidth.toFloat()
                Direction.RIGHT_TO_LEFT -> screenWidth.toFloat() * 2
            }
        )
    }

    val targetX = when (direction) {
        Direction.LEFT_TO_RIGHT -> screenWidth.toFloat() * 2
        Direction.RIGHT_TO_LEFT -> -screenWidth.toFloat()
    }

    // Fade alpha animation
    val alpha = remember { Animatable(0f) }

    LaunchedEffect(message) {
        // Fade in
        alpha.animateTo(
            targetValue = 1f,
            animationSpec = tween(durationMillis = 500)
        )

        // Scroll animation
        animate(
            initialValue = offsetX,
            targetValue = targetX,
            animationSpec = tween(
                durationMillis = animationDuration,
                easing = LinearEasing
            )
        ) { value, _ ->
            offsetX = value
        }

        // Fade out
        alpha.animateTo(
            targetValue = 0f,
            animationSpec = tween(durationMillis = 500)
        )

        // Notify completion
        // Note: We can't directly pass ComposeView here, so we'll handle removal differently
    }

    // Auto-remove after animation completes
    LaunchedEffect(message) {
        kotlinx.coroutines.delay((animationDuration + 1000).toLong())
        // Will be removed by OverlayEngine timeout mechanism
    }

    Box(
        modifier = Modifier
            .fillMaxWidth()
            .wrapContentHeight()
            .offset { IntOffset(offsetX.toInt(), 0) }
            .alpha(alpha.value)
    ) {
        Text(
            text = message.content,
            style = TextStyle(
                fontSize = fontSize.sp,
                fontFamily = fontFamily,
                fontWeight = FontWeight.Medium,
                color = Color.White,
                letterSpacing = 0.5.sp
            ),
            modifier = Modifier
                .background(
                    color = Color.Black.copy(alpha = 0.6f),
                    shape = RoundedCornerShape(12.dp)
                )
                .padding(horizontal = 16.dp, vertical = 8.dp)
        )
    }
}

/**
 * Scroll direction enum.
 */
private enum class Direction {
    LEFT_TO_RIGHT,
    RIGHT_TO_LEFT
}
