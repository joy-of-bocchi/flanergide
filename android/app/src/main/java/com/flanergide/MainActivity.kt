package com.flanergide

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.flanergide.core.StateStore
import com.flanergide.permissions.PermissionManager

/**
 * MainActivity - Simple launcher activity for RealitySkin.
 *
 * Responsibilities:
 * - Start RealityService on app launch
 * - Show permission status
 * - Request SYSTEM_ALERT_WINDOW permission if needed
 */
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Start the service
        RealityService.start(this)

        setContent {
            MaterialTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    MainScreen()
                }
            }
        }
    }
}

@Composable
fun MainScreen() {
    val appState by StateStore.appState.collectAsState()
    val permissions = appState.permissions

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        // App Title
        Text(
            text = "RealitySkin",
            style = MaterialTheme.typography.headlineLarge
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Nico-nico Style Scrolling Messages",
            style = MaterialTheme.typography.bodyMedium,
            color = Color.Gray
        )

        Spacer(modifier = Modifier.height(48.dp))

        // Service Status
        Card(
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Text(
                    text = "Service Status",
                    style = MaterialTheme.typography.titleMedium
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "✅ Active",
                    color = Color.Green
                )
            }
        }

        Spacer(modifier = Modifier.height(16.dp))

        // Permissions Status
        Card(
            modifier = Modifier.fillMaxWidth()
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Text(
                    text = "Permissions",
                    style = MaterialTheme.typography.titleMedium
                )
                Spacer(modifier = Modifier.height(8.dp))

                PermissionRow(
                    name = "Draw over other apps",
                    granted = permissions.systemAlertWindow
                )

                Spacer(modifier = Modifier.height(8.dp))

                PermissionRow(
                    name = "Text Capture (Accessibility)",
                    granted = permissions.accessibilityService
                )
            }
        }

        Spacer(modifier = Modifier.height(24.dp))

        // Request Permissions Buttons
        if (!permissions.systemAlertWindow) {
            Button(
                onClick = { PermissionManager.requestSystemAlertWindow() },
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Grant Overlay Permission")
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Required to show scrolling messages",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )

            Spacer(modifier = Modifier.height(16.dp))
        }

        if (!permissions.accessibilityService) {
            Button(
                onClick = { PermissionManager.requestAccessibilityService() },
                modifier = Modifier.fillMaxWidth(),
                colors = ButtonDefaults.buttonColors(
                    containerColor = MaterialTheme.colorScheme.secondary
                )
            ) {
                Text("Enable Text Capture")
            }

            Spacer(modifier = Modifier.height(8.dp))

            Text(
                text = "Required to capture your typing for AI context",
                style = MaterialTheme.typography.bodySmall,
                color = Color.Gray
            )
        }

        if (permissions.systemAlertWindow && permissions.accessibilityService) {
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "✨ All permissions granted! Ready to go",
                style = MaterialTheme.typography.bodyMedium,
                color = Color.Green
            )
        }

        Spacer(modifier = Modifier.height(32.dp))

        // Info Section
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(
                containerColor = MaterialTheme.colorScheme.secondaryContainer
            )
        ) {
            Column(
                modifier = Modifier.padding(16.dp)
            ) {
                Text(
                    text = "ℹ️ How it works",
                    style = MaterialTheme.typography.titleSmall
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "• On-device AI generates messages every 10-30 seconds\n" +
                            "• Messages scroll across your screen (Nico-nico style)\n" +
                            "• Random directions, speeds, and positions\n" +
                            "• Powered by Phi-2 quantized LLM (1.6 GB)",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }
    }
}

@Composable
fun PermissionRow(name: String, granted: Boolean) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(name)
        Text(
            text = if (granted) "✅" else "❌",
            color = if (granted) Color.Green else Color.Red
        )
    }
}
