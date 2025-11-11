# FontProvider Utility

## Status: ✅ IMPLEMENTED (Phase 6)

## Purpose
Simple utility for randomly selecting fonts for each scrolling message. No global state, no event system - just a straightforward helper.

## Design Decision

Each message gets a **random font independently** for Nico-nico style variety. This means:
- ✅ Simple utility function: `getRandomFontFamily(context)`
- ✅ No global font state needed
- ✅ No events or state management required

---

## Implementation

### FontProvider.kt

```kotlin
object FontProvider {
    private const val FONTS_DIR = "fonts"

    // Automatically discovers fonts from assets/fonts directory
    private fun getAvailableFontPaths(context: Context): List<String> {
        return try {
            val fontFiles = context.assets.list(FONTS_DIR) ?: emptyArray()
            fontFiles
                .filter { it.endsWith(".ttf", ignoreCase = true) || it.endsWith(".otf", ignoreCase = true) }
                .map { "$FONTS_DIR/$it" }
        } catch (e: Exception) {
            emptyList()
        }
    }

    fun getRandomTypeface(context: Context): Typeface {
        val fontPaths = getAvailableFontPaths(context)
        return if (fontPaths.isEmpty()) {
            Typeface.DEFAULT
        } else {
            val fontPath = fontPaths.random()
            try {
                Typeface.createFromAsset(context.assets, fontPath)
            } catch (e: Exception) {
                Typeface.DEFAULT
            }
        }
    }

    fun getRandomFontFamily(context: Context): FontFamily {
        val fontPaths = getAvailableFontPaths(context)
        return if (fontPaths.isEmpty()) {
            FontFamily.Default
        } else {
            val fontPath = fontPaths.random()
            try {
                val typeface = Typeface.createFromAsset(context.assets, fontPath)
                FontFamily(ComposeTypeface(typeface))
            } catch (e: Exception) {
                FontFamily.Default
            }
        }
    }

    fun getAvailableFonts(context: Context): List<String> = getAvailableFontPaths(context)
}
```

---

## Usage

### In Overlay Composable

```kotlin
@Composable
fun ScrollingMessageOverlay(message: Message) {
    val context = LocalContext.current

    // Each message gets its own random font
    val fontFamily = remember(message) {
        FontProvider.getRandomFontFamily(context)
    }

    Text(
        text = message.content,
        fontFamily = fontFamily,
        fontSize = 24.sp,
        color = Color.White
    )
}
```

**Key Points**:
- Use `remember(message)` to pick a font once per message
- Each new message gets a different random font
- No state coordination needed

---

## Adding New Fonts

Simply drop `.ttf` or `.otf` files into the `assets/fonts/` directory:

```
app/src/main/assets/fonts/
├── CyberpunkWaifus.ttf
├── ComicSans.ttf
├── Impact.ttf
└── ...
```

**That's it!** FontProvider automatically discovers all fonts in the directory at runtime.

No code changes needed, no manifest changes, no resource IDs, no rebuild complexity.

---

## Font Formats

**Supported**:
- TTF (TrueType Font) ✅
- OTF (OpenType Font) ✅

**Not Supported**:
- WOFF/WOFF2 (web fonts) ❌
- Variable fonts (partial support, depends on Android version) ⚠️

---

## Error Handling

FontProvider gracefully falls back to `Typeface.DEFAULT` / `FontFamily.Default` if:
- Font file not found in assets
- Font file is corrupted
- Font format unsupported

No crashes, no exceptions thrown.

---

## Performance Considerations

### Font Loading

- **First Time**: `Typeface.createFromAsset()` loads font from disk
- **Subsequent Calls**: Android may cache internally (not guaranteed)
- **Recommendation**: Keep font files reasonably sized (< 500KB each)

### Memory

- Each `Typeface` object consumes memory proportional to font file size
- If you have 10 messages on screen with different fonts, memory = ~10x font size
- **Mitigation**: Limit concurrent messages (already done: max 5 messages)

### Font Caching (Optional Future Enhancement)

If performance becomes an issue, you can cache loaded Typefaces:

```kotlin
private val typefaceCache = mutableMapOf<String, Typeface>()

fun getRandomFontFamily(context: Context): FontFamily {
    val fontPath = fontPaths.random()
    val typeface = typefaceCache.getOrPut(fontPath) {
        Typeface.createFromAsset(context.assets, fontPath)
    }
    return FontFamily(ComposeTypeface(typeface))
}
```

---

## Testing

### Manual Test

1. Add 2-3 different fonts to `assets/fonts/`
2. Run app, trigger multiple messages
3. Verify each message has a different random font
4. Check logcat for "Found N fonts" message to confirm discovery

### Unit Test (Optional)

```kotlin
@Test
fun `getAvailableFonts discovers fonts from assets`() {
    val fonts = FontProvider.getAvailableFonts(context)
    assertTrue(fonts.isNotEmpty())
    assertTrue(fonts.all { it.startsWith("fonts/") })
    assertTrue(fonts.all { it.endsWith(".ttf") || it.endsWith(".otf") })
}
```

---

## Where to Get Fonts

### Free Font Sources

- **Google Fonts**: https://fonts.google.com (open source, free for commercial use)
- **DaFont**: https://www.dafont.com (check license per font)
- **Font Squirrel**: https://www.fontsquirrel.com (100% free for commercial use)

### License Compliance

- **Check License**: Ensure font license allows embedding in apps
- **Include License File**: Place `LICENSE.txt` in `assets/fonts/` if required
- **Attribution**: Some fonts require attribution in app credits

---

## Future Enhancements (Optional)

### 1. Per-Font Weights
Support different weights (bold, light) from same font family:

```kotlin
data class FontInfo(
    val basePath: String,
    val weights: Map<Int, String> // 400 -> "Regular.ttf", 700 -> "Bold.ttf"
)
```

### 2. Font Pairing
Ensure visually compatible fonts are selected:

```kotlin
private val fontGroups = listOf(
    listOf("fonts/serif1.ttf", "fonts/serif2.ttf"), // Group 1: Serif fonts
    listOf("fonts/sans1.ttf", "fonts/sans2.ttf")    // Group 2: Sans fonts
)

fun getRandomFontFromGroup(groupIndex: Int) { ... }
```

### 3. User-Added Fonts
Allow users to place fonts in external storage:

```kotlin
fun scanUserFonts(): List<String> {
    val fontDir = File(context.getExternalFilesDir(null), "fonts")
    return fontDir.listFiles { it.extension in listOf("ttf", "otf") }
        ?.map { it.absolutePath } ?: emptyList()
}
```

---

## Dependencies

- Android Typeface API (built-in)
- Jetpack Compose UI (for FontFamily)
- No external libraries needed

---

## Files in This Module

- `FontProvider.kt` — Font utility object
- `CLAUDE.md` — This file

---

## Notes

- **No EventBus**: FontProvider doesn't emit events
- **No StateStore**: FontProvider doesn't read/write global state
- **Thread-Safe**: `random()` and `createFromAsset()` are thread-safe
- **Context**: Always pass `applicationContext`, not Activity context
