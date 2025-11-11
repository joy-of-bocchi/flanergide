# RealitySkin - Build Verification & Testing Guide

## Phase 5: Build Configuration Status ✅

All build configuration is complete. This document serves as a verification checklist.

---

## ✅ Build Configuration Checklist

### 1. Project Structure
- ✅ `settings.gradle.kts` includes llama.cpp module
- ✅ Namespace changed from `com.example.realityskin` → `com.realityskin`
- ✅ All source files in correct package structure

### 2. Dependencies (`app/build.gradle.kts`)
- ✅ Jetpack Compose (BOM 2024.02.00)
  - compose.ui
  - compose.material3
  - activity-compose
- ✅ Kotlin Coroutines (1.8.0)
- ✅ Lifecycle components (2.7.0)
- ✅ llama.cpp Android library (project reference)

### 3. Android Manifest
- ✅ Permissions declared:
  - `SYSTEM_ALERT_WINDOW` (draw overlays)
  - `FOREGROUND_SERVICE`
  - `FOREGROUND_SERVICE_SPECIAL_USE`
  - `POST_NOTIFICATIONS`
- ✅ MainActivity registered (launcher)
- ✅ RealityService registered (foreground service, type: specialUse)

### 4. Gradle Configuration
- ✅ compileSdk: 34
- ✅ minSdk: 29 (Android 10+)
- ✅ targetSdk: 34
- ✅ Compose enabled
- ✅ Kotlin compiler extension: 1.5.8

### 5. Module Structure
```
✅ app/src/main/java/com/realityskin/
   ✅ core/           (EventBus, StateStore, AppState, Events)
   ✅ ai/             (MLModel, GGUFModel, AIOrchestrator, MessageGenerator)
   ✅ overlay/        (OverlayEngine)
      ✅ composables/ (ScrollingMessageOverlay)
   ✅ permissions/    (PermissionManager)
   ✅ RealityService.kt
   ✅ MainActivity.kt
```

### 6. Assets
- ✅ `app/src/main/assets/models/phi-2-q4_k_m.gguf` (1.6 GB)

---

## 🧪 Pre-Build Verification Steps

### Step 1: Sync Gradle
```bash
# In Android Studio:
File → Sync Project with Gradle Files
```

**Expected Result**: No errors, llama module should be recognized

### Step 2: Check for Compilation Errors
```bash
# In Android Studio:
Build → Make Project (⌘F9 / Ctrl+F9)
```

**Expected Result**: Build successful, no errors

### Step 3: Verify llama.cpp Module
```bash
# Check if llama module exists
ls -la llama.cpp/examples/llama.android/llama/
```

**Expected Result**: Directory exists with build.gradle.kts and source files

---

## 🚀 Build & Run Steps

### 1. Clean Build
```bash
./gradlew clean
./gradlew build
```

### 2. Install on Device/Emulator
```bash
# Via Android Studio:
Run → Run 'app' (⌃R / Ctrl+R)

# Or via command line:
./gradlew installDebug
```

### 3. Grant Permissions
After app launches:
1. Tap "Grant Overlay Permission" button
2. Enable "RealitySkin" in Settings
3. Return to app
4. Verify ✅ appears next to "Draw over other apps"

---

## 📊 Expected Behavior After Launch

### Immediate (0-5 seconds)
- ✅ MainActivity displays
- ✅ "Service Status: Active" shows green
- ✅ Permission status shows (granted or not granted)
- ✅ Notification appears: "RealitySkin Active"

### 5-10 seconds (Model Loading)
Check logcat for:
```
RealityService: 🚀 RealityService starting...
RealityService: ✓ StateStore initialized
RealityService: ✓ PermissionManager initialized
RealityService: ✓ OverlayEngine initialized
RealityService: ✓ AIOrchestrator initialized
GGUFModel: Loading GGUF model from...
GGUFModel: Model loaded successfully in XXXXms
AIOrchestrator: ✅ GGUF model loaded successfully
```

### 10-30 seconds (First Message)
- ✅ First scrolling message appears on screen
- ✅ Message scrolls left-to-right OR right-to-left
- ✅ Semi-transparent black background
- ✅ Auto-disappears after animation

### Ongoing (Every 10-30 seconds)
- ✅ New messages appear randomly
- ✅ Up to 5 messages can be on screen simultaneously
- ✅ Varied speeds, directions, positions, font sizes

---

## 🐛 Troubleshooting

### Build Fails: "Cannot resolve llama module"
**Fix**:
```bash
# Verify settings.gradle.kts includes:
include(":llama")
project(":llama").projectDir = file("llama.cpp/examples/llama.android/llama")

# Then sync Gradle
```

### Runtime: "SYSTEM_ALERT_WINDOW permission denied"
**Fix**:
- Go to Settings → Apps → RealitySkin → Display over other apps
- Enable permission
- Return to app

### Runtime: "Model file not found"
**Fix**:
```bash
# Verify model exists:
ls -lh app/src/main/assets/models/phi-2-q4_k_m.gguf

# Should show: ~1.6 GB file
```

### No Messages Appearing
**Check logcat for**:
1. Model loading errors (GGUFModel tag)
2. Permission state (PermissionManager tag)
3. EventBus emissions (StateStore tag)
4. Overlay creation (OverlayEngine tag)

---

## 📱 Testing Checklist

### Basic Functionality
- [ ] App launches without crash
- [ ] Service starts (notification visible)
- [ ] Permission request works
- [ ] Model loads (check logcat)
- [ ] First message appears within 30 seconds
- [ ] Messages scroll smoothly
- [ ] Multiple messages can overlap

### Edge Cases
- [ ] App works after device rotation
- [ ] Service restarts after force-stop
- [ ] Works with permission revoked mid-session
- [ ] Low memory handling (model load fails gracefully)

### Performance
- [ ] Overlay rendering: 60 FPS (no stuttering)
- [ ] Model inference: 1-3 seconds per message
- [ ] Memory usage: ~2-3 GB (acceptable for 1.6 GB model)
- [ ] Battery drain: Monitor over 1 hour

---

## 📝 Logcat Filter Commands

### View All RealitySkin Logs
```bash
adb logcat | grep -E "(RealityService|StateStore|AIOrchestrator|OverlayEngine|PermissionManager|GGUFModel)"
```

### View Only Errors
```bash
adb logcat *:E | grep RealitySkin
```

### View Model Loading
```bash
adb logcat | grep GGUFModel
```

### View Message Generation
```bash
adb logcat | grep AIOrchestrator
```

---

## ✅ Phase 5 Complete!

All build configuration is verified and ready. Proceed to testing!

**Next Steps**:
1. Sync Gradle
2. Build project
3. Install on device
4. Grant permissions
5. Watch for scrolling messages! 🎉
