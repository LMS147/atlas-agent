package com.atlas.ai.feature.monitoring

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.atlas.ai.navigation.AtlasViewModel
import com.atlas.ai.domain.model.UiState
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import kotlinx.coroutines.launch

import com.atlas.ai.ui.theme.*

@Composable internal fun MonitoringScreen(s: UiState, vm: AtlasViewModel) {
 Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) { Heading("Server health", "A snapshot from the last health check"); AtlasCard { Icon(Icons.Default.Dns, null, tint = Cyan); Text(if(s.demo) "Demo mode" else s.health?.status ?: "Unavailable", fontSize = 24.sp); Text(if(s.demo) "No server is connected. Metrics are not simulated." else "Version: ${s.health?.version ?: "—"}\nUptime: ${s.health?.uptime_seconds ?: "—"} seconds", color = Muted) }; Button(enabled = !s.busy, onClick = { vm.navigate("Server setup") }) { Text("Server setup") } }
}
