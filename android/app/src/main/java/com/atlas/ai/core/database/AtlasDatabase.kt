package com.atlas.ai.core.database

import androidx.room.*
import com.atlas.ai.data.local.*

@Database(entities = [Message::class, Memory::class], version = 1, exportSchema = false)
abstract class AtlasDatabase : RoomDatabase() { abstract fun dao(): AtlasDao }
