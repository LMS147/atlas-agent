package com.atlas.ai.feature.settings

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

@Composable internal fun Settings(s: UiState, vm: AtlasViewModel) {
 var clear by rememberSaveable { mutableStateOf(false) }
 Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
  Heading("Make it yours", "Connection and conversation preferences")
  AtlasCard { Text("Server", fontWeight = FontWeight.Bold); Text(if(s.demo) "Demo mode · no server connected" else "Authenticated HTTPS connection", color = Muted); OutlinedButton(enabled = !s.busy, onClick = { vm.navigate("Server setup") }) { Text("Change server") } }
  AtlasCard { Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) { Text("Show timestamps"); Switch(s.timestamps, { vm.toggleTimestamps() }) }; Text("Conversations are cached on this device.", color = Muted); TextButton(enabled = !s.busy, onClick = { clear = true }) { Text("Clear local chat") } }
  TextButton(enabled = !s.busy, onClick = vm::disconnect) { Text("Disconnect & forget credentials") }
  Text("Atlas for Android · 0.4.0\nPersonal AI companion", color = Muted, fontSize = 12.sp)
 }
 if(clear) AlertDialog(onDismissRequest = { clear = false }, title = { Text("Clear local chat?") }, text = { Text("This removes the current conversation’s chat cache from this device. Server conversation history and memories remain on the server.") }, confirmButton = { TextButton(onClick = { vm.clearChat(); clear = false }) { Text("Clear") } }, dismissButton = { TextButton(onClick = { clear = false }) { Text("Cancel") } })
}
