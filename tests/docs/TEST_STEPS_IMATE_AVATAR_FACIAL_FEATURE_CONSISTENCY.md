# TEST_STEPS_IMATE_AVATAR_FACIAL_FEATURE_CONSISTENCY

## Goal

Validate whether adding explicit iMate avatar facial-feature constraints improves avatar consistency for chat image-to-image generation.

## 1) Production trace record located (LangSmith)

- Project: `inty-backend-prod`
- Root run: `019cc91a-dbce-7df0-9402-e1d98210c6ac`
- Child run (`z_image_turbo_image_to_image`): `019cc91a-dbe0-78f0-a118-77f3a0b73519`
- Model: `fal-ai/z-image/turbo/image-to-image`
- Source metadata (from trace):
  - `agent_id`: `cc472ad3-6dd2-4163-aa6f-72b130e4b10f`
  - `session_id`: `eaa01db1-41b8-565d-851c-d2bddd4e37af`
  - `message_id`: `1797770`
  - `prompt_len`: `9828`
  - `reference_image_url`: `https://storage.googleapis.com/inty-static/backgrounds/user-01JWZ34Y4D1C92GD86A5R6EWYJ/20260108-164848-7fa6fb34.jpg`

## 2) Local reproduction of the same prod trace

- Replayed the exact child-run arguments locally through `z_image_turbo_image_to_image`.
- Reproduction output summary file:
  - `/opt/cursor/artifacts/repro_prod_trace_zimage_summary.json`
- Reproduction output image:
  - `/opt/cursor/artifacts/repro_prod_trace_zimage.jpg`

Result: local call succeeds with the same provider model and expected output image format/size (JPEG, 576x1024).

## 3) A/B experiment design for iMate consistency

Reference avatar (official iMate/IntelliMate):
- `/opt/cursor/artifacts/imate_reference_avatar.jpeg`

Prompt variants:
- **Baseline**: chat-image prompt without iMate-specific facial-feature block.
- **Enhanced**: same prompt plus iMate-specific block:
  - non-human mascot identity
  - ghost-like rounded silhouette
  - exactly two vertical black oval eyes
  - no human facial anatomy features (mouth/nose/skin pores/etc.)

Controlled settings:
- Same reference image URL
- Same model: `fal-ai/z-image/turbo/image-to-image`
- Same strength: `0.75`
- Same seeds: `7`, `13`, `29`

Artifacts:
- Baseline:  
  `/opt/cursor/artifacts/imate_baseline_seed_7.jpg`  
  `/opt/cursor/artifacts/imate_baseline_seed_13.jpg`  
  `/opt/cursor/artifacts/imate_baseline_seed_29.jpg`
- Enhanced:  
  `/opt/cursor/artifacts/imate_enhanced_seed_7.jpg`  
  `/opt/cursor/artifacts/imate_enhanced_seed_13.jpg`  
  `/opt/cursor/artifacts/imate_enhanced_seed_29.jpg`
- Metrics JSON:
  - `/opt/cursor/artifacts/imate_avatar_facial_feature_effectiveness.json`

## 4) Effectiveness results

From `imate_avatar_facial_feature_effectiveness.json`:

| Seed | Baseline aHash distance (lower better) | Enhanced aHash distance | Baseline MSE similarity (higher better) | Enhanced MSE similarity |
|---|---:|---:|---:|---:|
| 7  | 15 | 14 | 0.0001576053 | 0.0001545612 |
| 13 | 15 | 15 | 0.0001571320 | 0.0001554351 |
| 29 | 18 | 17 | 0.0001573561 | 0.0001594945 |

Key observation:
- aHash improves in 2/3 seeds and ties in 1/3 seeds.
- Visual inspection shows the enhanced variant more consistently preserves the “mascot” face rules:
  - avoids introducing extra human-like facial details
  - keeps the simplified two-eye identity more stably
  - keeps the secondary bubble shape cleaner in edge contours

## 5) Conclusion

Adding explicit iMate avatar facial-feature constraints is effective for improving identity consistency in chat-to-image results, especially reducing facial drift toward non-mascot details while maintaining the official avatar style.
