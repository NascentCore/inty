# FR Chat-to-Video (Seedance) Investigation Summary

CREATED_BY_AGENT

## Scope

This document summarizes the investigation results for:

1. Chat-to-video implementation direction in this repository.
2. Seedance (Seedance 2.0 / v2) availability and pricing status on fal.ai.
3. Whether Chinese domestic providers have both text-to-video and image-to-video models.
4. Runtime validation status for:
   - Seedance via Python (`fal_client`)
   - ByteDance Volcengine Ark API

---

## TL;DR

- `Seedance 2.0` on fal.ai is currently in a "coming soon / launch soon" state on the landing page.
- fal model routes for `seedance/v2/*` are reachable (`HTTP 200`), but billing metadata indicates `enterprise_status=pending` and `price=0` (not production-stable for pricing decisions yet).
- For predictable cost planning right now, `seedance/v1.5/pro` (and fallback to `v1/lite`) is more reliable than directly betting on `v2`.
- Chinese providers with text+image to video are confirmed: ByteDance (Seedance), Kuaishou (Kling), Alibaba (Wan2.1), Tencent (HunyuanVideo + HunyuanVideo-I2V).
- Python runtime test for Seedance in this environment failed at credential stage (missing `FAL_KEY`), not at SDK or route stage.
- Volcengine Ark endpoint is reachable and OpenAI-compatible path works, but current environment has no valid Ark credential; requests stop at `401 AuthenticationError`.

---

## 1) fal.ai Seedance Investigation

### 1.1 Naming and route status

- "Seedance 2.0" landing page exists.
- Landing page wording still indicates pre-launch style statements:
  - "Coming soon to fal.ai."
  - "launches on fal.ai soon..."
  - commercial usage details to be confirmed at launch.

### 1.2 Endpoint status and billing metadata snapshot

Observed endpoint metadata (API page embedded `endpointBilling`) shows:

| Endpoint | Billing unit | Price | Enterprise status | Interpretation |
|---|---:|---:|---|---|
| `fal-ai/bytedance/seedance/v2/text-to-video` | compute seconds | 0 | pending | v2 route is up, commercial/pricing status not finalized |
| `fal-ai/bytedance/seedance/v2/image-to-video` | compute seconds | 0 | pending | same |
| `fal-ai/bytedance/seedance/v2/reference-to-video` | compute seconds | 0 | pending | same |
| `fal-ai/bytedance/seedance/v1.5/pro/text-to-video` | 1m tokens | 1.2 | ready | usable for production planning |
| `fal-ai/bytedance/seedance/v1/pro/text-to-video` | 1m tokens | 2.5 | ready | available but higher cost |
| `fal-ai/bytedance/seedance/v1/lite/text-to-video` | 1m tokens | 1.8 | ready | cheaper/faster baseline |

### 1.3 Public pricing snippets (model pages)

- v1 lite t2v:
  - "5 second video costs $0.18..."
  - "...1 million video tokens costs $1.8"
- v1 pro t2v:
  - "5 second video costs roughly $0.62..."
  - "...1 million video tokens costs $2.5"
- v1.5 pro t2v:
  - "720p 5 second video with audio costs roughly $0.26..."
  - "...1 million video tokens with audio costs $2.4"
  - "Without audio ... 1.2 per million tokens"

### 1.4 Practical model choice recommendation

- **P0 (production-safe):** `seedance/v1.5/pro/text-to-video` (audio optional).
- **P1 (gray rollout):** test `seedance/v2/*` behind feature flag only.
- **P2 (promote v2):** switch default when v2 billing and enterprise status become stable.

---

## 2) Repository Current-State Assessment (for Chat-to-Video)

### 2.1 What already exists

- Chat image generation is already productionized:
  - endpoint
  - model routing
  - subscription limit checks
  - usage recording
  - fallback behavior
- Backend has a video generation service (`Veo3`) currently used for agent background animation generation.

### 2.2 Main gap to chat-to-video

- Message metadata pipeline currently handles `generated_image`, but no equivalent `generated_video` merge + CDN transform path.
- Android chat message DTO/UI currently renders generated images, not generated videos in message meta.

### 2.3 Minimal implementation direction

1. Add chat-video endpoint (parallel to chat-image endpoint design).
2. Add `generated_video` metadata schema handling in history retrieval path.
3. Add `video_generation` usage type tracking.
4. Extend Android message metadata DTO + render path for generated video.

---

## 3) Chinese Domestic Providers with Text+Image to Video

Confirmed providers:

1. **ByteDance Seedance**
   - official page mentions multi-shot video generation from both text and image.
2. **Kuaishou Kling**
   - official API docs include both:
     - `POST /v1/videos/text2video`
     - `POST /v1/videos/image2video`
3. **Alibaba Wan2.1**
   - official README explicitly lists Text-to-Video and Image-to-Video.
4. **Tencent Hunyuan**
   - HunyuanVideo (T2V) + HunyuanVideo-I2V (I2V) official repositories.

---

## 4) Runtime Validation Results

### 4.1 Seedance via Python (`fal_client`)

Validation sequence:

1. `fal_client` import in project venv: success.
2. Real calls attempted:
   - `fal-ai/bytedance/seedance/v1/lite/text-to-video`
   - `fal-ai/bytedance/seedance/v1.5/pro/text-to-video`
3. Result:
   - both fail with `MissingCredentialsError`
   - root cause: missing `FAL_KEY` in environment/config.
4. Additional control test with fake key:
   - reached server and failed with authentication error, indicating route is valid.

Conclusion:

- SDK/runtime path is ready.
- Full end-to-end success requires a valid `FAL_KEY`.

### 4.2 Volcengine Ark API validation

Validation sequence:

1. Environment variable scan for Volc/Ark credentials: none found.
2. Probed Ark endpoint directly:
   - `POST https://ark.cn-beijing.volces.com/api/v3/chat/completions` (fake key)
   - response: `401 AuthenticationError`
3. Probed OpenAI-compatible SDK path:
   - `OpenAI(base_url="https://ark.cn-beijing.volces.com/api/v3", api_key="...")`
   - response: `401 AuthenticationError`
4. `GET /api/v3/models` also returns `401`.

Conclusion:

- API endpoint/network path is valid.
- Compatibility path is valid.
- Production verification is blocked by missing valid Ark credentials and target endpoint/model id.

---

## 5) Suggested Next Steps

1. Prepare credentials:
   - `FAL_KEY` (for Seedance validation)
   - `ARK_API_KEY` + target model endpoint id (for Ark success call)
2. Run one successful generation call for each platform and store:
   - request payload
   - response schema
   - latency
   - cost field behavior
3. Start backend MVP:
   - add chat-video endpoint + `generated_video` metadata path
4. Add Android minimal support:
   - parse and display `generated_video` in chat message UI

