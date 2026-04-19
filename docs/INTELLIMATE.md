# IntelliMate User Guide

> CREATED_BY_AGENT

> Content should be copied to https://www.notion.so/IntelliMate-Help-Center-2b88c199b74b808a985bcaa64e36c322

> 这里的内容被拷贝到 IntelliMate 官方助手 Inty 系统消息（成为提示词的一部分）
> 拷贝时，以 > 开头的文本行会被删除掉

This guide gives IntelliMate users a clear, plain-language map of where to find help when they feel lost. It consolidates the Android client documentation and reorganizes it for non-technical readers.

Terminology used in this guide:
- **IntelliMate** = the app product
- **iMate** = the AI companion in the IntelliMate app

## TL;DR

- **Install or update**: Prefer the [Google Play internal testing channel](https://play.google.com/store/apps/details?id=com.ai.intellimate&hl=en-US&ah=EmlT1IB-9hWsv_1I4B8Go9FEIFc). For the very latest QA builds, grab the APK from the [daily release page](https://github.com/NascentCore/inty-app/releases).
- **Sign in**: You can explore as a guest, but linking your Google account keeps chats and VIP benefits synced across devices. (Phones in China must install Google services first.)
- **Main flow**: Discover iMates on Explore → open a Chat → use extras like voice playback, image generation, Keep Talking, or Hype actions → adjust Profile or Settings as needed.
- **Need help?**
  - In-app: Settings → Help & Feedback (placeholder entry; use tester channels for now).
  - Test/ops escalation: see “Contact & Escalation” near the end of this doc.

## App Overview (placeholder)

### Bottom navigation bar

Bottom navigation bar host entry points of IntelliMate App's primary features. The icons are (from left to right):
- **Chats** for you to chat and interact with your iMates, and the main portal to IntelliMate's long-term AI companionship experience
- **Messages** for you to return to your iMates
- **Official Assistant Chat** (middle icon) for you to quickly open a chat with the Inty official assistant
- **Explore iMates** for you to explore and find your desired iMate
- **Me** for managing your **Premium subscription** and general settings of the app

<img width="480" height="96" alt="image" src="https://github.com/user-attachments/assets/349658de-d749-40af-a3cc-4e9613fcf6ac" />

We'll go through each of these pages one by one as follows:

### Chats page

Click the **Chats** or the **left-most** icon to open the chat page. Below is an overview of the functionality on the page.

<img width="480" height="2207" alt="image" src="https://github.com/user-attachments/assets/2dd7c9b6-d6c4-4fc4-b26d-885bf8541c01" />

### Messages page

Click the **Messages** or the **2nd** icon from the left

### Official Assistant Chat entry

Tap the **middle** icon to open the chat screen with the Inty official assistant.
In this official chat page, you can use the FAQ quick-question buttons near the top to prefill common long-form questions into the input box (they are not auto-sent).
You can also tap **Test my MBTI type** above the input box to send a structured MBTI interview starter prompt immediately, so the assistant begins a step-by-step type discovery conversation for you.
You can also tap **+ Create your own iMate** above the input box to jump straight to the iMate creation page. This button hides automatically while the keyboard is open. After creation succeeds from this entry, IntelliMate opens the new iMate chat directly.

### Explore iMates page

Click the **Explore** icon to open the Explore iMates page.
To create your own iMate, go to Profile → My iMates.

### Me page

Click the **Me** or the **right-most** icon

Top-right quick actions currently include **Help**, **Daily Check-in**, and **Settings**.

## Where do I go to…?

| Task | App path | Tips & references |
| --- | --- | --- |
| Try the app or switch backend | Settings → Debug Backend Endpoint (debug builds only) | Swap between local/dev/prod servers without reinstalling; see `android_app/APP_DYNAMIC_TEST.md`. |
| Find or follow iMates | Bottom nav → Explore | Double-tap the top bar to jump back to page 1 and refresh recommendations. Images are preloaded for smooth scrolling. |
| Chat with an iMate | Tap any iMate card → Chat | Text + voice playback (openers are preloaded) + instant image generation + send one selected image together with text in the same message. The app may send your **local time and time zone** with chat traffic so replies can match the time of day; debug builds can disable this under Settings → Debug Backend Endpoint → **User time context reporting**. |
| Hype an iMate | iMate profile → **Hype this iMate** or Explore → **Top Hyped iMates** | Spend Credits to hype an iMate and raise their Hype Score on the leaderboard. |
| Upscale an AI image in fullscreen view | Open any generated/gallery image → Fullscreen viewer → **Upscale** (next to Share) | VIP users can use it directly. Non-VIP users can unlock once by spending **10 credits**, then choose **1x / 2x / 4x**. |
| Start an MBTI test chat | Official Assistant Chat → **Test my MBTI type** | Sends a structured MBTI interview starter prompt immediately, then continue by answering each follow-up question. |
| Create or edit an iMate | Official Assistant Chat → **+ Create your own iMate**, or Profile → My iMates | Guided flow with image upload and text-to-image background generation. |
| Subscribe or restore | Profile → VIP / Subscription | Uses Google Play Billing; see Troubleshooting if charges succeed but perks stay locked. |
| Update personal profile info | Me → Settings | Personal info edits live in Me page settings (not in Chat settings). |
| Manage notifications & privacy | Settings → Notifications / Privacy | Push powered by Firebase Cloud Messaging; toggle anytime. Tapping a “Heartbeat Journal” (festival memory) notification opens that iMate’s Love Journal and the related memory entry. When opened from chat or a notification, that entry is highlighted with a glow and the rest of the screen is dimmed; tap outside the glowing card to return to the normal list. |
| Check version info | Settings → About | Version code comes from git commit count. If Play build lags behind, install the QA APK. |
| Send feedback or report | Chat → ⋮ → Report, Profile → Feedback, or Image Viewer → Report | Reports go through the Report Service; when reporting from Image Viewer, the current image is attached automatically and you can add more evidence images. |

## Feature Deep Dive

### 1. Explore
- Double-tap the header to rewind to the top and refresh.
- Avatars/backgrounds preload so cards stay visible even on slow networks.
- The top banner section includes **Newly iMates** with subtitle **“Newly crafted based on your preference”**, showing up to 10 most recently created iMates.
- Switch between Recommended, Favorites, Created by Me.

  <img width="300" height="1200" alt="image" src="https://github.com/user-attachments/assets/526e12a9-f0ef-4735-9ec9-ec32da978639" />

### 2. Chats
- Every message supports voice playback; audio is cached locally (`AudioCacheManager`).
- Chat settings now include a VIP-gated per-chat **Voice** selector (Gemini voices). Non-subscribed users see the same upgrade popup as the Models row when tapping Voice; subscribed users can apply the selected voice to both auto-play and tap-to-play generation in that same chat.
- For MALE/FEMALE iMates, the **Voice** selector now only shows same-gender Gemini voices to avoid cross-gender voice mismatch.
- The **Voice** selector uses a compact scrollable menu with 9 visible options at a time.
- Buttons such as Keep Talking and Message to Image fire Firebase events, helping support diagnose issues.
- “Network error” alerts usually clear after checking connectivity or switching back to the default backend on debug builds.
- Chat input supports **image + text** multimodal sending: tap the image button, pick one photo, optionally type text, then send both together.
- After selecting a local chat image, IntelliMate now compresses it to JPEG and rescales it to about 57,600 total pixels before upload; the UI keeps showing the original image while compressing, then switches to the compressed one, and after upload the outgoing bubble reuses that compressed local cache instead of re-downloading the remote URL.
- Chat message bubbles can render multimodal replies from `/api/v1/chat/completions/{agent_id}` when the assistant returns both text and image content.
- You can enable **Send UX/UI gesture signals** in Me → Settings (default off); when enabled, tapping/swiping the visible character background auto-sends an action message with coordinates mapped to the original background image so the AI can understand the touched region.
- After you tap 👍/👎 on a generated chat image, IntelliMate may show a once-per-local-day feedback popup; choosing **Send Suggestions** opens Feedback with the image auto-attached and image-quality options prefilled for faster reporting.
- **文本流式显示**：聊天页设置抽屉中可关闭该开关，关闭后 AI 回复一次性显示，不再逐字出现。
- VIP-tagged iMates deduct **1 credit per message** for non-subscribed users. Subscribed users are exempt; insufficient credits block sending.
- If a subscribed user reaches the daily chat quota, IntelliMate shows a dedicated dialog (**“Daily Premium Chat Limit Reached”**) instead of the upgrade-to-premium prompt.
- Fullscreen image viewer includes a VIP **Upscale** action (next to Share) with **1x / 2x / 4x** options. Non-subscribed users can still use it by spending **10 credits** once per open viewer session.

  <img width="300" height="1200" alt="image" src="https://github.com/user-attachments/assets/0326fd90-1bbe-4207-9e9f-1c71c4608847" />

**Voice call** (from Chat): Voice calls require microphone permission. The centre circle shows connection status (e.g. Connecting / Connected), **listening** when the AI is waiting for you, or **speaking** when the AI is talking—then you see “tap to interrupt AI” and a wave animation; tap the circle to interrupt and speak. Use mute and end-call as needed. If the voice call screen stays blank, grant microphone permission when prompted or in system Settings → App → IntelliMate → Permissions.

### 3. iMates
- iMate creation/editing supports uploads plus AI-generated art; failures surface clear error states (`AvatarManager`).
- iMate detail pages show AI-generated media pulled from recent chats, with explicit labeling.
- iMate detail pages include **Hype this iMate**, which lets you spend Credits to increase that iMate's Hype Score.

### 4. VIP / Subscription
- Plans run through Google Play Billing; benefits refresh automatically after purchase.
- If a transaction is stuck in “processing,” open Play Store → Account → Subscriptions to confirm payment status.
- “Restore Purchase” revalidates receipts. If that fails, capture the GPA order ID before contacting support.

### 5. Settings
- **Debug Backend Endpoint** (debug builds only): Change the API base URL at runtime; cache clears automatically so the next request uses the new server.
- **User time context reporting** (debug builds only, under Debug Backend Endpoint): When enabled, the app includes device local time and IANA time zone in chat API/WebSocket payloads so the assistant can use time-of-day context; release builds include this by default without a toggle.
- **Help & Feedback**: Add your FAQ or form link here so end users can submit issues without leaving the app.
- **Remote Config**: Features such as auto-enabling Keep Talking are controlled centrally. Sudden UI changes may come from new Remote Config values.

## Troubleshooting

### Network / Sign-in
- **Google sign-in missing**: Install Google Play Services (GMS). Mainland China devices usually require manual GMS installation.
- **Google sign-in fails after choosing an account**: Usually means the device cannot reach Google through Play services—check Wi‑Fi or VPN so traffic to Google isn’t blocked, wait and retry, or install/update Play services when the system prompts.
- **Blank screens / failed loads**: Clear IntelliMate storage in Android Settings and relaunch, or switch back to the default backend in debug builds.

### Chat & Media
- **Voice playback issues**: Check system volume. If playback keeps failing, clear cache or restart the app; audio will re-cache automatically.
- **Voice call screen stays blank**: Allow microphone permission when the app asks, or open Settings → Apps → IntelliMate → Permissions and enable Microphone.
- **Daily premium chat limit reached**: If you are already subscribed and hit your daily quota, you should see a dedicated limit dialog. The quota refreshes automatically the next day.
- **Image generation errors**: `IMAGE_GENERATION_LIMIT_REACHED` means you hit the quota. Try again later.

### Subscription
- **Charged but perks locked**:
  1. Open Profile → VIP → Restore Purchase.
  2. Still stuck? Send support the GPA order code screenshot.
- **Multiple devices**: Benefits sync by Google account, but Keep Talking/image quotas are enforced server-side, so heavy usage on one device affects others.

### Crashes & Performance
- Crash reports flow into Firebase Crashlytics automatically. To speed up investigations, provide device model, OS version, and the steps leading to the crash.

## Reference Library

- **Release & rollout**
  - Google Play process (`android_app/GOOGLE_PLAY_RELEASE.md`).
  - Release notes template (`android_app/devops/GOOGLE_PLAY_RELEASE_NOTES.md`).
- **Network / SDK**
  - API architecture (`android_app/API_ARCH.md`).
  - Dual-stack explainer (`android_app/core/data/NETWORK_MANAGERS_EXPLAINED.md`).
- **Quality & testing**
  - Hermetic test targets (`android_app/HERMETIC_TESTS.md`).
  - High-priority TODOs & critiques (`android_app/TODOS.md`, `android_app/ARCH_CRITIQUES.md`).
- **UGC & compliance**
  - Sensitive word list (`android_app/doc/ugc/README.md`).
  - AI labeling requirements (`android_app/AGENTS.md`).

> Before sharing the internal docs above with customers, scrub sensitive content or create a public-friendly excerpt.

## Contact & Escalation

- **In-app feedback**: Settings → Feedback (placeholder). Until that ships, users can leave store reviews or reply to onboarding emails.
- **Testers**:
  - File GitHub issues or team docs with logs/screenshots.
  - Use Debug builds plus the Backend Endpoint switcher when verifying fixes against local servers.
- **End users**:
  - Include this guide link in welcome emails or community posts.
  - For common questions (sign-in, subscription, media playback), respond with the relevant sections above.

## Items You Need to Fill In

1. **Latest UI screenshots**: Replace the three placeholders (home, Explore, Chat) with production-ready images.
2. **Support email or form**: Add the official contact info inside “Contact & Escalation.”
3. **Help-center / FAQ links**: If you have public tutorials or videos, list them in “Reference Library” so users can self-serve faster.

Once the placeholders are filled, the document can be published directly to your international user base as a quick-start help center entry.
