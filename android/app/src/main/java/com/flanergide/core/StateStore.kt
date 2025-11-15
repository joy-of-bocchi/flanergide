package com.flanergide.core

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/**
 * Central state store for global application state.
 * Subscribes to EventBus and applies events via reducer pattern.
 */
object StateStore {
    private const val TAG = "StateStore"

    private val _appState = MutableStateFlow(AppState())
    val appState: StateFlow<AppState> = _appState.asStateFlow()

    /**
     * Initialize StateStore to listen to EventBus events.
     * Call this once during app startup.
     */
    fun init(scope: CoroutineScope) {
        Log.d(TAG, "Initializing StateStore")
        scope.launch {
            EventBus.events.collect { event ->
                Log.d(TAG, "Received event: ${event::class.simpleName}")
                _appState.update { currentState ->
                    reduce(currentState, event)
                }
            }
        }
    }

    /**
     * Reducer function: (currentState, event) -> newState
     * Pure function for easy testing.
     */
    private fun reduce(state: AppState, event: AppEvent): AppState {
        return when (event) {
            is AppEvent.AvatarMoodChange -> {
                Log.d(TAG, "Updating avatar mood: ${event.mood}")
                state.copy(avatarMood = event.mood)
            }

            is AppEvent.NewMessage -> {
                val message = event.toMessage()
                Log.d(TAG, "Adding new message: ${message.content.take(50)}...")
                // Keep only last 10 messages
                state.copy(
                    recentMessages = (listOf(message) + state.recentMessages).take(10)
                )
            }

            is AppEvent.MiniGameTrigger -> {
                Log.d(TAG, "Triggering mini-game: ${event.gameType} for ${event.targetApp}")
                state.copy(
                    activeMiniGame = MiniGame(event.gameType, event.targetApp)
                )
            }

            is AppEvent.MiniGameComplete -> {
                Log.d(TAG, "Mini-game completed: success=${event.success}")
                state.copy(activeMiniGame = null)
            }

            is AppEvent.PermissionStateChange -> {
                Log.d(TAG, "Permission changed: ${event.permission} = ${event.granted}")
                state.copy(
                    permissions = state.permissions.update(event.permission, event.granted)
                )
            }

            is AppEvent.LLMToggle -> {
                Log.d(TAG, "LLM toggled: ${event.enabled}")
                state.copy(llmEnabled = event.enabled)
            }
        }
    }

    /**
     * Get current state value (non-reactive).
     */
    fun getCurrentState(): AppState = _appState.value
}
