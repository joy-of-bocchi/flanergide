package com.flanergide.core

/**
 * Global application state.
 * Immutable data class - updates create new instances via .copy()
 */
data class AppState(
    val avatarMood: AvatarMood = AvatarMood.Neutral,
    val activeMiniGame: MiniGame? = null,
    val permissions: PermissionState = PermissionState(),
    val recentMessages: List<Message> = emptyList(),
    val overlayVisibility: Map<OverlayType, Boolean> = mapOf(
        OverlayType.SCROLLING_MESSAGE to true,
        OverlayType.AVATAR to false,
        OverlayType.MINI_GAME to false
    )
)

/**
 * Avatar mood states.
 */
enum class AvatarMood {
    Happy, Neutral, Sad, Excited, Angry, Thinking
}

/**
 * Mini-game instance.
 */
data class MiniGame(
    val type: MiniGameType,
    val targetApp: String
)

/**
 * Available mini-game types.
 */
enum class MiniGameType {
    QuickMath, MemoryMatch, ReactionTime
}

/**
 * Message data class.
 */
data class Message(
    val content: String,
    val source: String,
    val timestamp: Long = System.currentTimeMillis()
)

/**
 * Permission state tracker.
 */
data class PermissionState(
    val systemAlertWindow: Boolean = false,
    val usageStats: Boolean = false,
    val notificationListener: Boolean = false,
    val accessibilityService: Boolean = false
) {
    fun update(permission: Permission, granted: Boolean): PermissionState {
        return when (permission) {
            Permission.SYSTEM_ALERT_WINDOW -> copy(systemAlertWindow = granted)
            Permission.USAGE_STATS -> copy(usageStats = granted)
            Permission.NOTIFICATION_LISTENER -> copy(notificationListener = granted)
            Permission.ACCESSIBILITY_SERVICE -> copy(accessibilityService = granted)
        }
    }

    fun allGranted() = systemAlertWindow && usageStats && notificationListener && accessibilityService
}

/**
 * System permissions.
 */
enum class Permission {
    SYSTEM_ALERT_WINDOW, USAGE_STATS, NOTIFICATION_LISTENER, ACCESSIBILITY_SERVICE
}

/**
 * Overlay types.
 */
enum class OverlayType {
    SCROLLING_MESSAGE, AVATAR, MINI_GAME
}
