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

@Composable internal fun Setup(vm: AtlasViewModel, busy: Boolean) {
 var url by rememberSaveable { mutableStateOf(vm.state.value.serverUrl.ifBlank { "https://atlas-api-a9s1.onrender.com" }) }; var token by remember { mutableStateOf("") }; var remember by rememberSaveable { mutableStateOf(true) }
 LazyColumn(Modifier.fillMaxSize().imePadding().padding(24.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) {
  item { AtlasMark(); Spacer(Modifier.height(24.dp)); Heading("Connect to Atlas", "Enter your authenticated HTTPS endpoint. Your Groq key stays on the server.") }
  item { OutlinedTextField(value = url, onValueChange = { url = it }, label = { Text("Server URL") }, placeholder = { Text("https://atlas.example.com") }, singleLine = true, enabled = !busy, modifier = Modifier.fillMaxWidth()) }
  item { OutlinedTextField(value = token, onValueChange = { token = it }, label = { Text("Atlas access token") }, visualTransformation = PasswordVisualTransformation(), singleLine = true, enabled = !busy, modifier = Modifier.fillMaxWidth()) }
  item { Row(verticalAlignment = Alignment.CenterVertically) { Switch(checked = remember, onCheckedChange = { remember = it }, enabled = !busy); Spacer(Modifier.width(12.dp)); Text("Remember this server securely") } }
  item { Button(onClick = { vm.connect(url, token, remember) }, enabled = !busy && url.isNotBlank() && token.isNotBlank(), modifier = Modifier.fillMaxWidth().height(52.dp)) { Text("Connect") } }
  item { Text("Your Render server URL is filled in. Enter your Atlas access token to connect, or change the URL to use another server.", color = Muted); TextButton(enabled = !busy, onClick = vm::demo) { Text("Explore demo instead") } }
 }
}
