package com.realityskin.core

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.channels.BufferOverflow

/**
 * Central event bus for inter-module communication.
 * Uses SharedFlow for asynchronous, decoupled event broadcasting.
 */
object EventBus {
    private val _events = MutableSharedFlow<AppEvent>(
        replay = 0,                         // No replay - new subscribers don't get past events
        extraBufferCapacity = 64,           // Buffer up to 64 events
        onBufferOverflow = BufferOverflow.DROP_OLDEST  // Drop oldest if buffer full
    )

    /**
     * Public event flow for subscribers.
     */
    val events: SharedFlow<AppEvent> = _events.asSharedFlow()

    /**
     * Emit an event to all subscribers.
     * Non-blocking suspend function.
     */
    suspend fun emit(event: AppEvent) {
        _events.emit(event)
    }
}
