package com.flanergide.core

/**
 * Sealed class hierarchy for all application events.
 * Events flow through EventBus to decouple modules.
 */
sealed class AppEvent {
    /**
     * Emitted when a new message is generated (e.g., from AI).
     * Triggers display of scrolling text overlay.
     */
    data class NewMessage(
        val content: String,
        val source: String
    ) : AppEvent() {
        fun toMessage() = Message(content, source)
    }

    /**
     * Emitted when avatar mood changes based on context.
     */
    data class AvatarMoodChange(val mood: AvatarMood) : AppEvent()

    /**
     * Emitted when a mini-game should be triggered (app gating).
     */
    data class MiniGameTrigger(
        val gameType: MiniGameType,
        val targetApp: String
    ) : AppEvent()

    /**
     * Emitted when mini-game is completed.
     */
    data class MiniGameComplete(
        val success: Boolean,
        val targetApp: String
    ) : AppEvent()

    /**
     * Emitted when a system permission state changes.
     */
    data class PermissionStateChange(
        val permission: Permission,
        val granted: Boolean
    ) : AppEvent()
}
