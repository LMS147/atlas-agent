package com.atlas.ai.feature.monitoring

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.repeatOnLifecycle
import com.atlas.ai.navigation.AtlasViewModel
import com.atlas.ai.domain.model.UiState
import com.atlas.ai.ui.theme.*
import kotlinx.coroutines.delay
import java.text.DateFormat
import java.util.Date
import java.util.Locale

private fun bytes(value: Long?) = value?.let { String.format(Locale.US,"%.1f MiB",it / 1048576.0) } ?: "Unavailable"
private fun percent(value: Double?) = value?.let { String.format(Locale.US,"%.1f%%",it) } ?: "Unavailable"

@Composable internal fun MonitoringScreen(s: UiState, vm: AtlasViewModel) {
 val lifecycle=LocalLifecycleOwner.current
 LaunchedEffect(lifecycle,s.demo) {
  if(!s.demo) lifecycle.repeatOnLifecycle(Lifecycle.State.STARTED) {
   while(true) { delay(10000); vm.refreshMetrics() }
  }
 }
 LazyColumn(Modifier.fillMaxSize().padding(20.dp),verticalArrangement=Arrangement.spacedBy(16.dp)) {
  item { Heading("Server monitoring",if(s.demo) "Connect to view real metrics" else "Refreshes every 10 seconds while open") }
  if(s.demo) item { Text("Metrics are not simulated.",color=Muted) }
  s.monitoring?.let { m ->
   item { Text("Last sample: ${DateFormat.getTimeInstance().format(Date(m.sampled_at))}. Values remain from this sample if a refresh fails.",color=Muted) }
   item { AtlasCard {
    Text("CPU",style=MaterialTheme.typography.titleMedium)
    Text("Device: ${percent(m.device_cpu_percent)}\nAtlas process: ${percent(m.process_cpu_percent)}")
    Text("Process CPU uses 100% per busy core; sampled over 0.2 seconds.",color=Muted)
   } }
   item { AtlasCard {
    Text("Memory",style=MaterialTheme.typography.titleMedium)
    Text("Device used: ${bytes(m.ram?.used_bytes)}\nDevice available: ${bytes(m.ram?.available_bytes)}\nDevice total: ${bytes(m.ram?.total_bytes)}\nAtlas resident RAM: ${bytes(m.process_rss_bytes)}")
   } }
   item { AtlasCard {
    Text("Data storage filesystem",style=MaterialTheme.typography.titleMedium)
    Text("Used: ${bytes(m.storage?.used_bytes)}\nFree: ${bytes(m.storage?.free_bytes)}\nTotal: ${bytes(m.storage?.total_bytes)}")
   } }
   item { AtlasCard {
    Text("Atlas API service",style=MaterialTheme.typography.titleMedium)
    Text("PID: ${m.service.pid}\nService uptime: ${m.service.uptime_seconds} seconds\nDevice uptime: ${m.device_uptime_seconds?.let { "$it seconds" } ?: "Unavailable"}\nPython threads: ${m.service.threads}\nHTTP requests: ${m.service.requests}\nServer errors (5xx): ${m.service.errors}\nActive requests: ${m.service.active_requests}")
    Text("Counters reset on API restart. Active requests includes this metrics request.",color=Muted)
   } }
   if(m.unavailable.isNotEmpty()) item { Text("Unavailable on this device: ${m.unavailable.joinToString()}. Android may restrict /proc access.",color=Muted) }
  }
  item { Row(horizontalArrangement=Arrangement.spacedBy(8.dp)) {
   Button(enabled=!s.demo && !s.busy,onClick={vm.refreshMetrics()}){Text("Refresh")}
   TextButton(enabled=!s.busy,onClick={vm.navigate("Server setup")}){Text("Server setup")}
  } }
 }
}
