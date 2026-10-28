package com.atlas.ai.feature.files

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

@Composable internal fun FilesScreen(s: UiState, vm: AtlasViewModel) {
 LazyColumn(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) { item { Heading("Your workspace", if(s.demo) "Sample files · read-only preview" else "Server files · read-only listing") }; items(s.files) { file -> AtlasCard { Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(16.dp)) { Icon(if(file.directory) Icons.Default.Folder else Icons.Default.Description, null, tint = if(file.directory) Color(0xFFFFC569) else Blue); Column { Text(file.name, fontWeight = FontWeight.SemiBold); Text(if(file.directory) "Folder" else "${file.size_bytes} bytes", color = Muted, fontSize = 12.sp) } } } }; if(s.files.isEmpty() && !s.busy) item { Text("No files loaded.", color = Muted) } }
}
