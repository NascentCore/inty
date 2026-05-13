# Create or update Kotlin API DTOs from Pydantic schemas

## Overview

Keep Android API DTOs aligned with backend Pydantic schemas that cross the wire boundary.

Primary target:

- `android_app/core/data/src/main/kotlin/ai/sxwl/android/data/api/model`

Source of truth:

- `app/schemas/`

When chat wire models change, also check the legacy iMate chat DTO surface:

- `imate_android_app/app/src/main/java/com/inty/imate/chat/data/bean/ChatApiModels.kt`

## Steps

1. **Read local guidance first**
   - Read `AGENTS.md`.
   - Read `app/schemas/AGENTS.md`.
   - Read `android_app/AGENTS.md`.

2. **Understand the schema delta**
   - Inspect current changes in `app/schemas/` and any backend API code using those schemas.
   - Identify only request/response DTOs, WebSocket frames, wire enums, and serialized `meta_data` fields that the Android client consumes or sends.
   - Do not mirror backend-only orchestration, persistence internals, prompts, or service types.

3. **Find the Kotlin owner**
   - Search existing DTOs before creating a new file.
   - Update the nearest existing `*Beans.kt`, `*Bean.kt`, or constants file when the schema already belongs there.
   - Create a new DTO file only when the backend schema represents a distinct API surface not already represented in the model package.

4. **Map Pydantic to Kotlin deliberately**
   - `BaseModel` -> Kotlin `data class`.
   - Pydantic field aliases / snake_case JSON names -> camelCase Kotlin property with `@Json(name = "...")`.
   - Optional or nullable Python fields -> nullable Kotlin types with existing local defaults.
   - Python lists and dicts -> `List<T>` and `Map<String, T>`.
   - `datetime` wire fields -> `String` unless nearby code already uses a stronger date type.
   - Stable wire enums -> constants or enums following nearby Kotlin convention; volatile backend strings should remain `String`.
   - Opaque JSON payloads -> `Map<String, Any?>` or `Any?` only when the schema is intentionally open-ended.

5. **Follow Android data-layer conventions**
   - Use Moshi annotations already used by the package: `@JsonClass(generateAdapter = true)` and `@Json(name = "...")`.
   - Match the surrounding file's `@Serializable` usage; do not add serialization frameworks or networking stacks.
   - Keep DTOs as wire shapes. Put UI state, formatting, and repository behavior outside API model classes unless the file already owns that local helper.
   - Preserve Android's forward-compatible behavior for backend expansion: unknown server fields must not break parsing.

6. **Validate**
   - For DTO-only changes, run the smallest relevant Android data-module check, usually:
     - `cd android_app && ./gradlew :core:data:testDebugUnitTest`
   - When constructor signatures, annotations, or Retrofit payloads changed, also run:
     - `cd android_app && ./gradlew :core:data:compileDebugKotlin`
   - Do not use the Android emulator for this command.

7. **Report**
   - List each backend schema and its Kotlin DTO counterpart.
   - Mention any intentionally unmapped backend fields and why Android does not consume them.
   - Provide exact validation commands and outcomes.

## Checklist

- [ ] Relevant `AGENTS.md` files read
- [ ] Backend schema delta understood
- [ ] Existing Kotlin DTO owners searched
- [ ] JSON names and nullability aligned with Pydantic schema
- [ ] Chat changes checked against both Android DTO surfaces when relevant
- [ ] Targeted Gradle validation run or limitation explained
