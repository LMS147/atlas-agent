package com.atlas.ai.feature.dashboard

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

@Composable internal fun Welcome(vm: AtlasViewModel, busy: Boolean) {
 Column(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Navy, Color(0xFF102D50), Navy))).padding(28.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
  AtlasMark(Modifier.size(130.dp)); Spacer(Modifier.height(24.dp)); Text("Atlas", fontSize = 48.sp, fontWeight = FontWeight.Bold)
  Text("Your personal AI companion", color = Cyan, fontSize = 18.sp); Spacer(Modifier.height(12.dp)); Text("Chat. Remember. Build.\nYour assistant, wherever you are.", color = Muted, lineHeight = 24.sp)
  Spacer(Modifier.height(64.dp)); Button(enabled = !busy, onClick = { vm.navigate("Server setup") }, modifier = Modifier.fillMaxWidth().height(54.dp)) { Text("Get started") }
  TextButton(enabled = !busy, onClick = vm::demo) { Text("Explore demo") }; Text("Connect securely to your own Atlas server", fontSize = 12.sp, color = Muted)
 }
}
