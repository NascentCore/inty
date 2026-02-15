# Love Journal screen UI improvements

## Design theme (must follow)

All UI changes **must use the existing design theme** in the repo ([android_app/AGENTS.md](android_app/AGENTS.md) Design + 一般指示):

- **Colors:** Only `MaterialTheme.colorScheme` (e.g. `surfaceContainerHigh`, `tertiaryContainer`, `onSurface`, `onSurfaceVariant`). No raw `Color(0x...)` or hardcoded hex.
- **Shapes:** Only `MaterialTheme.shapes` (e.g. `MaterialTheme.shapes.medium` = 12dp, `MaterialTheme.shapes.large` = 20dp). No ad-hoc `RoundedCornerShape(12.dp)` unless a named value is added to theme/dimens and referenced.
- **Typography:** Only `MaterialTheme.typography` (e.g. `bodyMedium`, `titleMedium`, `bodySmall`). Use `.copy(lineHeight = ...)` only if needed for readability; do not introduce new font sizes or weights outside the theme.
- **Dimensions:** All dp/sp values must come from [dimens.xml](android_app/app/src/main/res/values/dimens.xml) via `dimensionResource(R.dimen.xxx)`. No raw `8.dp`, `16.dp`, etc. Add new entries (e.g. `heartbeat_card_padding`, `heartbeat_list_spacing`) for any new magic numbers.

Theme sources: [Theme.kt](android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Theme.kt), [Color.kt](android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Color.kt), [Shapes.kt](android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Shapes.kt).

---

## Current issues (from screen + code)

- **Flat, low-contrast cards:** Journal entries use `Surface(..., color = MaterialTheme.colorScheme.surface)` with `MaterialTheme.shapes.small` (4dp) and only 8dp inner padding. Cards blend into the background.
- **No depth:** No shadow or elevation; `memory_bg` drawable is loaded but never used ([Heartbeat.kt](android_app/app/src/main/kotlin/com/ai/intellimate/agent/heartbeat/Heartbeat.kt) line 158).
- **Dense body text:** Body uses plain `Text(it.memory)` with no explicit line height.
- **Hardcoded spacing:** Uses `8.dp` / `16.dp` instead of dimens.
- **Subtitle:** Same visual weight as content; no hierarchy.
- **Tiny corner radius:** `shapes.small` (4dp) feels boxy; theme already has `shapes.medium` (12dp) and `shapes.large` (20dp).

---

## Recommended changes (theme-only)

### 1. Card container (journal entry item)

- **Color:** Use a theme token that separates cards from background, e.g. `MaterialTheme.colorScheme.surfaceContainerHigh` or `MaterialTheme.colorScheme.tertiaryContainer.copy(alpha = 0.5f)` (aligned with Chat Love Journal notify which uses `tertiaryContainer`).
- **Shape:** Use `MaterialTheme.shapes.medium` (12dp) instead of `MaterialTheme.shapes.small`.
- **Elevation:** Add `Modifier.shadow(...)`; elevation value must come from dimens (e.g. add `heartbeat_card_elevation`).
- **Padding:** Add `heartbeat_card_padding_*` in dimens and use `dimensionResource`; remove all raw `8.dp` / `16.dp` in this screen.

Optional: If `R.drawable.memory_bg` is a subtle texture, use it as card background; otherwise remove the unused `itemBg` variable.

### 2. Typography (theme only)

- **Date/title:** Keep `MaterialTheme.typography.titleMedium`; optionally use `MaterialTheme.colorScheme.onSurfaceVariant` for a secondary look.
- **Body:** Use `MaterialTheme.typography.bodyMedium`; add `lineHeight` via `.copy()` only if theme allows or add a single dimen for line height and use it in one place.

### 3. Subtitle and list spacing

- **Subtitle:** Use `MaterialTheme.typography.bodySmall` and `MaterialTheme.colorScheme.onSurfaceVariant`; spacing below from dimens.
  - When agent name is present: use string **"%1$d Love Journals from %2$s about you"** (params: count, agent first name). Placeholder is `%2$s` (Android format).
  - When agent name is null: keep existing **"%1$d Love Journals about you"** (param: count).
- **List:** Vertical spacing between cards from dimens (e.g. `heartbeat_list_spacing`).

### 4. Dimens to add (in dimens.xml)

- `heartbeat_card_elevation` (e.g. 4dp for shadow)
- `heartbeat_card_padding_horizontal` / `heartbeat_card_padding_vertical` (e.g. 12dp)
- `heartbeat_list_spacing` (e.g. 12dp)
- `heartbeat_subtitle_bottom` (e.g. 16dp)  
Replace any remaining raw dp in Heartbeat.kt with these.

### 5. Love Journal design colors (match mock)

Match the design spec from the Love Journal screen mock:

| Role | Hex | Usage |
|------|-----|--------|
| Screen background | `#FCF7F0` | Scaffold / content area background (warm beige) |
| Card background | `#FAF8F5` | Journal entry card Surface (lighter creamy beige) |
| Primary text | `#241F1A` | Title, subtitle, journal body (dark gray) |
| Accent | `#EC725B` | Top bar title underline, journal entry date (reddish-orange) |

**Implementation (theme-only, no raw hex in app):**

- **Define in design module** [Color.kt](android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Color.kt): add an object (e.g. `LoveJournalColors`) with the four colors, same pattern as `AppColors` / `HolidayCelebrationColors`. Hex values live only here.
- **Expose via ColorScheme** in [Theme.kt](android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Theme.kt): add extension properties on `ColorScheme` (e.g. `loveJournalBackground`, `loveJournalCardBackground`, `loveJournalOnBackground`, `loveJournalAccent`) that return these colors, same pattern as `ColorScheme.textOnLightSurface`.
- **Use in Heartbeat** [Heartbeat.kt](android_app/app/src/main/kotlin/com/ai/intellimate/agent/heartbeat/Heartbeat.kt): use only `MaterialTheme.colorScheme.loveJournal*` — set Scaffold/Box background, TopAppBar title and subtitle text, card Surface color, card date and title underline to the corresponding tokens; empty state text to `loveJournalOnBackground`. No `Color(0x...)` in the app module.

---

## Files to touch

| File | Change |
|------|--------|
| [Color.kt](android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Color.kt) | Add `LoveJournalColors` object with background `#FCF7F0`, cardBackground `#FAF8F5`, onBackground `#241F1A`, accent `#EC725B`. |
| [Theme.kt](android_app/core/design/src/main/kotlin/ai/sxwl/android/design/theme/Theme.kt) | Add `ColorScheme` extension properties for the four Love Journal colors so app uses `MaterialTheme.colorScheme.loveJournal*`. |
| [Heartbeat.kt](android_app/app/src/main/kotlin/com/ai/intellimate/agent/heartbeat/Heartbeat.kt) | Card: theme color + `shapes.medium` + shadow (dimen); body/date/subtitle from `MaterialTheme.typography` and `colorScheme`; all spacing via `dimensionResource`. Use `colorScheme.loveJournal*` for screen background, card color, title/subtitle/body text, accent (underline + date). Remove or use `itemBg`. |
| [dimens.xml](android_app/app/src/main/res/values/dimens.xml) | Add heartbeat_* entries; use them in Heartbeat.kt. |

---

## Out of scope (optional later)

- Left accent bar or icon (would still use theme colors/shapes).
- Human-friendly date format (e.g. “Feb 7, 2026”).
- Empty state illustration.

---

## Summary

Improvements are limited to: **theme tokens only** (colors from `colorScheme`, shapes from `MaterialTheme.shapes`, typography from `MaterialTheme.typography`) and **dimens-based spacing**. No new colors, no raw shapes or font sizes; optional shadow elevation and new padding/spacing dimens so the Love Journal screen stays consistent with the rest of the app.
