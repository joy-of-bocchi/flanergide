# Storage Module

## Status: ❌ NOT IMPLEMENTED

No state persistence currently. State resets on service restart. DataRepository not yet implemented.

## Purpose
Persistent storage for app state, user preferences, fonts, and AI persona data.

## Storage Solutions

### 1. Jetpack DataStore (Preferences)
**Use for**: Simple key-value pairs, user settings

**Examples**:
- Current font selection
- Gated apps list
- Persona configuration
- Overlay visibility preferences

### 2. Room Database (Optional)
**Use for**: Complex relational data (if needed)

**Examples**:
- Message history
- Mini-game scores/stats
- App usage analytics

### 3. File System
**Use for**: Large binary data

**Examples**:
- Downloaded fonts (.ttf files)
- Avatar images/animations
- Cached ML models

---

## Architecture

### DataRepository.kt
**Type**: Singleton object

**Responsibilities**:
- Provide unified interface for all storage operations
- Handle DataStore read/write
- Serialize/deserialize AppState
- Manage file system operations for fonts/assets

**API**:
```kotlin
object DataRepository {
    private lateinit var context: Context
    private lateinit var dataStore: DataStore<Preferences>

    fun init(appContext: Context) {
        context = appContext.applicationContext
        dataStore = context.createDataStore(name = "reality_skin_prefs")
    }

    // AppState persistence
    suspend fun saveAppState(state: AppState) {
        dataStore.edit { prefs ->
            prefs[stringPreferencesKey("avatar_mood")] = state.avatarMood.name
            prefs[booleanPreferencesKey("overlay_scrolling_message")] =
                state.overlayVisibility[OverlayType.SCROLLING_MESSAGE] ?: true
            prefs[booleanPreferencesKey("overlay_avatar")] =
                state.overlayVisibility[OverlayType.AVATAR] ?: true
        }
    }

    suspend fun loadAppState(): AppState? {
        return dataStore.data.map { prefs ->
            AppState(
                avatarMood = prefs[stringPreferencesKey("avatar_mood")]?.let {
                    AvatarMood.valueOf(it)
                } ?: AvatarMood.Neutral,
                overlayVisibility = mapOf(
                    OverlayType.SCROLLING_MESSAGE to (prefs[booleanPreferencesKey("overlay_scrolling_message")] ?: true),
                    OverlayType.AVATAR to (prefs[booleanPreferencesKey("overlay_avatar")] ?: true),
                    OverlayType.MINI_GAME to false
                )
            )
        }.first()
    }

    // Gated apps
    suspend fun saveGatedApps(apps: Set<String>) {
        dataStore.edit { prefs ->
            prefs[stringPreferencesKey("gated_apps")] = apps.joinToString(",")
        }
    }

    suspend fun loadGatedApps(): Set<String> {
        return dataStore.data.map { prefs ->
            prefs[stringPreferencesKey("gated_apps")]
                ?.split(",")
                ?.filter { it.isNotEmpty() }
                ?.toSet() ?: emptySet()
        }.first()
    }

    // Persona config
    suspend fun savePersonaConfig(config: PersonaConfig) {
        dataStore.edit { prefs ->
            prefs[stringPreferencesKey("persona_name")] = config.name
            prefs[stringPreferencesKey("persona_personality")] = config.personality.name
            prefs[stringPreferencesKey("persona_frequency")] = config.responseFrequency.name
        }
    }

    suspend fun loadPersonaConfig(): PersonaConfig {
        return dataStore.data.map { prefs ->
            PersonaConfig(
                name = prefs[stringPreferencesKey("persona_name")] ?: "Reality",
                personality = prefs[stringPreferencesKey("persona_personality")]?.let {
                    Personality.valueOf(it)
                } ?: Personality.Sarcastic,
                responseFrequency = prefs[stringPreferencesKey("persona_frequency")]?.let {
                    ResponseFrequency.valueOf(it)
                } ?: ResponseFrequency.Medium
            )
        }.first()
    }

    // Font file management
    fun getFontsDirectory(): File {
        val dir = File(context.filesDir, "fonts")
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    suspend fun saveFontFile(fontData: ByteArray, fileName: String): String = withContext(Dispatchers.IO) {
        val fontFile = File(getFontsDirectory(), fileName)
        fontFile.writeBytes(fontData)
        fontFile.absolutePath
    }

    fun listFontFiles(): List<File> {
        return getFontsDirectory().listFiles { file ->
            file.extension in listOf("ttf", "otf")
        }?.toList() ?: emptyList()
    }

    // User external fonts directory
    fun getUserFontsDirectory(): File {
        val dir = File(Environment.getExternalStorageDirectory(), "RealitySkin/fonts")
        if (!dir.exists()) dir.mkdirs()
        return dir
    }

    fun listUserFontFiles(): List<File> {
        return getUserFontsDirectory().listFiles { file ->
            file.extension in listOf("ttf", "otf")
        }?.toList() ?: emptyList()
    }
}
```

---

## DataStore Keys Organization

### Preferences Keys
```kotlin
object PreferenceKeys {
    // AppState
    val CURRENT_FONT_FAMILY = stringPreferencesKey("current_font_family")
    val CURRENT_FONT_WEIGHT = intPreferencesKey("current_font_weight")
    val CURRENT_FONT_PATH = stringPreferencesKey("current_font_path")
    val AVATAR_MOOD = stringPreferencesKey("avatar_mood")
    val OVERLAY_SCROLLING_MESSAGE = booleanPreferencesKey("overlay_scrolling_message")
    val OVERLAY_AVATAR = booleanPreferencesKey("overlay_avatar")

    // Gated apps
    val GATED_APPS = stringPreferencesKey("gated_apps")

    // Persona
    val PERSONA_NAME = stringPreferencesKey("persona_name")
    val PERSONA_PERSONALITY = stringPreferencesKey("persona_personality")
    val PERSONA_FREQUENCY = stringPreferencesKey("persona_frequency")

    // Privacy
    val BLACKLISTED_APPS = stringPreferencesKey("blacklisted_apps")
    val ENABLE_LOGGING = booleanPreferencesKey("enable_logging")
}
```

---

## State Persistence Strategy

### When to Persist
1. **On service stop**: `RealityService.onDestroy()`
2. **Periodically**: Every 60 seconds (auto-save)
3. **On state change**: Debounced writes (avoid writing on every event)

### Auto-Save Implementation
```kotlin
class RealityService : Service() {
    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)

    override fun onCreate() {
        super.onCreate()

        // Periodic auto-save
        serviceScope.launch {
            while (isActive) {
                delay(60_000) // Every 60 seconds
                StateStore.persistState(DataRepository)
            }
        }
    }

    override fun onDestroy() {
        runBlocking {
            StateStore.persistState(DataRepository)
        }
        serviceScope.cancel()
        super.onDestroy()
    }
}
```

### Debounced Writes
```kotlin
object StateStore {
    private var saveJob: Job? = null

    fun scheduleStateSave(scope: CoroutineScope) {
        saveJob?.cancel()
        saveJob = scope.launch {
            delay(2000) // Wait 2 seconds of inactivity
            persistState(DataRepository)
        }
    }
}
```

---

## Message History (Optional Room Database)

If you want to persist message history for analytics/review:

### MessageEntity.kt
```kotlin
@Entity(tableName = "messages")
data class MessageEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val content: String,
    val source: String,
    val timestamp: Long,
    val displayed: Boolean
)
```

### MessageDao.kt
```kotlin
@Dao
interface MessageDao {
    @Query("SELECT * FROM messages ORDER BY timestamp DESC LIMIT :limit")
    suspend fun getRecentMessages(limit: Int): List<MessageEntity>

    @Insert
    suspend fun insertMessage(message: MessageEntity)

    @Query("DELETE FROM messages WHERE timestamp < :cutoffTime")
    suspend fun deleteOldMessages(cutoffTime: Long)
}
```

### RealitySkinDatabase.kt
```kotlin
@Database(entities = [MessageEntity::class], version = 1)
abstract class RealitySkinDatabase : RoomDatabase() {
    abstract fun messageDao(): MessageDao

    companion object {
        @Volatile
        private var INSTANCE: RealitySkinDatabase? = null

        fun getInstance(context: Context): RealitySkinDatabase {
            return INSTANCE ?: synchronized(this) {
                val instance = Room.databaseBuilder(
                    context.applicationContext,
                    RealitySkinDatabase::class.java,
                    "reality_skin_db"
                ).build()
                INSTANCE = instance
                instance
            }
        }
    }
}
```

---

## Font Storage Strategy

### Bundled Fonts (Assets)
```
app/src/main/assets/fonts/
├── roboto_regular.ttf
├── comic_sans.ttf
└── neon_glow.ttf
```

**Access**:
```kotlin
fun loadBundledFont(assetPath: String): Typeface {
    return Typeface.createFromAsset(context.assets, "fonts/$assetPath")
}
```

### Downloaded Fonts (Internal Storage)
```
/data/data/com.flanergide/files/fonts/
├── font_12345.ttf
└── font_67890.ttf
```

**Save**:
```kotlin
suspend fun downloadAndSaveFont(url: String): String {
    val fontData = downloadFont(url)
    val fileName = "font_${url.hashCode()}.ttf"
    return DataRepository.saveFontFile(fontData, fileName)
}
```

### User Fonts (External Storage)
```
/sdcard/Flanergide/fonts/
├── my_cool_font.ttf
└── pixel_art.ttf
```

**Scan**:
```kotlin
fun scanUserFonts(): List<File> {
    return DataRepository.listUserFontFiles()
}
```

---

## Data Migration

### Version 1 → Version 2
If you change data schema:

```kotlin
suspend fun migrateDataIfNeeded() {
    val version = dataStore.data.map { it[intPreferencesKey("schema_version")] ?: 1 }.first()

    if (version < 2) {
        // Perform migration
        dataStore.edit { prefs ->
            // Migrate old keys to new keys
            val oldValue = prefs[stringPreferencesKey("old_key")]
            prefs[stringPreferencesKey("new_key")] = oldValue ?: "default"
            prefs.remove(stringPreferencesKey("old_key"))

            prefs[intPreferencesKey("schema_version")] = 2
        }
    }
}
```

---

## Backup & Restore

### Export Settings
```kotlin
suspend fun exportSettings(): String {
    val state = StateStore.appState.value
    val json = Json.encodeToString(state)
    return json
}

suspend fun saveBackup(fileName: String) {
    val json = exportSettings()
    val file = File(context.getExternalFilesDir(null), fileName)
    file.writeText(json)
}
```

### Import Settings
```kotlin
suspend fun importSettings(json: String) {
    val state = Json.decodeFromString<AppState>(json)
    StateStore.restoreState(state)
    DataRepository.saveAppState(state)
}

suspend fun loadBackup(fileName: String) {
    val file = File(context.getExternalFilesDir(null), fileName)
    val json = file.readText()
    importSettings(json)
}
```

---

## Privacy: Secure Storage

For sensitive data (if needed in future):

### EncryptedSharedPreferences
```kotlin
val masterKey = MasterKey.Builder(context)
    .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
    .build()

val encryptedPrefs = EncryptedSharedPreferences.create(
    context,
    "secret_prefs",
    masterKey,
    EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
    EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
)

encryptedPrefs.edit {
    putString("api_key", "secret_value")
}
```

---

## Testing

### Unit Test: Save/Load AppState
```kotlin
@Test
fun `saveAppState and loadAppState preserves state`() = runTest {
    val originalState = AppState(
        avatarMood = AvatarMood.Happy
    )

    DataRepository.saveAppState(originalState)
    val loadedState = DataRepository.loadAppState()

    assertEquals(originalState.avatarMood, loadedState?.avatarMood)
}
```

### Integration Test: Persistence After Restart
```kotlin
@Test
fun `state persists across service restarts`() = runTest {
    // Save state
    val state = AppState(avatarMood = AvatarMood.Excited)
    StateStore.persistState(DataRepository)

    // Simulate service restart
    StateStore.restoreState(DataRepository)

    assertEquals(AvatarMood.Excited, StateStore.appState.value.avatarMood)
}
```

---

## Performance Considerations

### Async Operations
- All DataStore operations are suspend functions (naturally async)
- Run on Dispatchers.IO for file operations

### Caching
```kotlin
object DataRepository {
    private var cachedPersonaConfig: PersonaConfig? = null

    suspend fun loadPersonaConfig(): PersonaConfig {
        return cachedPersonaConfig ?: loadPersonaConfigFromStore().also {
            cachedPersonaConfig = it
        }
    }
}
```

### Batching Writes
Instead of writing individual preferences, batch them:

```kotlin
dataStore.edit { prefs ->
    prefs[KEY_1] = value1
    prefs[KEY_2] = value2
    prefs[KEY_3] = value3
    // All written in single transaction
}
```

---

## Data Cleanup

### Delete Old Messages
```kotlin
suspend fun cleanupOldMessages() {
    val cutoffTime = System.currentTimeMillis() - TimeUnit.DAYS.toMillis(7)
    database.messageDao().deleteOldMessages(cutoffTime)
}

// Run periodically
scope.launch {
    while (isActive) {
        delay(TimeUnit.DAYS.toMillis(1))
        cleanupOldMessages()
    }
}
```

### Clear All Data
```kotlin
suspend fun clearAllData() {
    dataStore.edit { it.clear() }
    getFontsDirectory().deleteRecursively()
    database.clearAllTables()
}
```

---

## Dependencies

- Jetpack DataStore (Preferences)
- Jetpack Room (optional, for message history)
- Kotlin Serialization (for JSON export/import)
- Kotlin Coroutines
- Optional: EncryptedSharedPreferences (for sensitive data)

---

## Files in This Module

- `DataRepository.kt` — Main storage interface
- `PreferenceKeys.kt` — DataStore key definitions
- `MessageEntity.kt` — Room entity (if using Room)
- `MessageDao.kt` — Room DAO (if using Room)
- `RealitySkinDatabase.kt` — Room database (if using Room)
- `CLAUDE.md` — This file
