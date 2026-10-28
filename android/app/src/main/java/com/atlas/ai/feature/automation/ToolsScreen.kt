package com.atlas.ai.feature.automation

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

@Composable internal fun ToolsScreen(s: UiState, vm: AtlasViewModel) {
 Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(20.dp)) { Heading("A little more capable", "Tools for your Atlas workspace"); AtlasCard { Text("Memory & conversations", fontWeight = FontWeight.Bold); Text("Search saved facts or start a fresh local chat.", color = Muted); OutlinedButton(onClick = { vm.navigate("Memory") }, enabled = !s.busy) { Text("Open memory") }; Text("Remote command execution is not available in this version.", color = Muted) } }
}
