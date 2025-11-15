# Flanergide Codebase Cleanup TODO

## Issue: Duplicate Package Paths
The codebase has two parallel package structures:
- `com.realityskin.*` (old/renamed package)
- `com.flanergide.*` (current/active package)

This creates duplicate implementations and dead code.

---

## Cleanup Tasks

### Phase 1: Audit & Map Duplicates
- [ ] Find all files in `com.realityskin.*` packages
- [ ] For each file, determine if it's:
  - **DEAD CODE**: Not imported/used anywhere → DELETE
  - **ACTIVE**: Used by the app → KEEP in `com.flanergide.*` only
  - **DUPLICATE**: Exists in both packages with same code → DELETE realityskin version
- [ ] Document which modules are in which package

### Phase 2: Identify What Can Be Deleted
Known candidates for deletion (currently unused):
- [ ] `com.realityskin.data.*` - Duplicate of `com.flanergide.data.*`
  - `TextCaptureEngine.kt` - DUPLICATE (already in flanergide)
  - `KeyloggerAccessibilityService.kt` - DUPLICATE (already in flanergide)
  - `SensitiveDataRedactor.kt` - Check if duplicate
  - `CapturedText.kt` - Check if duplicate

Likely ACTIVE (keep):
- [ ] `com.realityskin.core.*` - Check if used
- [ ] `com.realityskin.overlay.*` - Check if used
- [ ] `com.realityskin.ai.*` - Check if used
- [ ] `com.realityskin.permissions.*` - Check if used

### Phase 3: Delete Dead Code
- [ ] Remove unused `com.realityskin.*` directories
- [ ] Verify build still works
- [ ] Search codebase for any remaining imports from deleted packages

### Phase 4: Unify Package Names (Optional)
If keeping RealitySkin code:
- [ ] Rename all `com.realityskin.*` → `com.flanergide.*`
- [ ] Update all imports
- [ ] Update `AndroidManifest.xml`
- [ ] Update `build.gradle.kts`

---

## Why This Matters
- **Confusion**: Two implementations of the same thing (which one gets used?)
- **Maintenance**: Bug fixes need to be applied in two places
- **APK Size**: Dead code increases app size
- **Complexity**: Harder to understand the codebase

---

## Steps to Execute Cleanup

1. Run `grep -r "com\.realityskin" app/src/main --include="*.kt" --include="*.xml"` to see all imports
2. For each file, trace if it's actually imported anywhere
3. Delete files with zero imports
4. Build and test to ensure nothing broke
5. Commit cleanup with message: "chore: remove duplicate realityskin package code"

---

## Current Status
- ❌ INCOMPLETE - Both packages still exist and are causing confusion
