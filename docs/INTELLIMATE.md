# IntelliMate Resource Guide

> CREATED_BY_AGENT

> Content should be copied to https://www.notion.so/IntelliMate-Help-Center-2b88c199b74b808a985bcaa64e36c322

This guide gives IntelliMate users a clear, plain-language map of where to find help when they feel lost. It consolidates the Android client documentation and reorganizes it for non-technical readers.

## TL;DR

- **Install or update**: Prefer the [Google Play internal testing channel](https://play.google.com/store/apps/details?id=com.ai.intellimate&hl=en-US&ah=EmlT1IB-9hWsv_1I4B8Go9FEIFc). For the very latest QA builds, grab the APK from the [daily release page](https://github.com/NascentCore/inty-app/releases).
- **Sign in**: You can explore as a guest, but linking your Google account keeps chats and VIP benefits synced across devices. (Phones in China must install Google services first.)
- **Main flow**: Discover agents on Explore → open a Chat → use extras like voice playback, image generation, or Keep Talking → adjust Profile or Settings as needed.
- **Need help?**
  - In-app: Settings → Help & Feedback (placeholder entry; use tester channels for now).
  - Test/ops escalation: see “Contact & Escalation” near the end of this doc.

## App Overview (placeholder)

### Bottom navigation bar

Bottom navigation bar host entry points of IntelliMate App's primary features. The icons are (from left to right):

<img width="480" height="96" alt="image" src="https://github.com/user-attachments/assets/349658de-d749-40af-a3cc-4e9613fcf6ac" />

**Chats** for you to chat and interact with IntelliMate, and the main portal to IntelliMate's long-term AI companionship experience

**Messages** for you to return to your IntelliMate AI companions

**Create IntelliMate** for you to create your own IntelliMate for long-term AI companionship

**Explore IntelliMates** for you to explore and find your IntelliMates

**Me** for your account and general settings of the app

### Chat page

Click the 

<img width="480" height="2207" alt="image" src="https://github.com/user-attachments/assets/2dd7c9b6-d6c4-4fc4-b26d-885bf8541c01" />

## Where do I go to…?

| Task | App path | Tips & references |
| --- | --- | --- |
| Try the app or switch backend | Settings → Debug Backend Endpoint (debug builds only) | Swap between local/dev/prod servers without reinstalling; see `android_app/APP_DYNAMIC_TEST.md`. |
| Find or follow agents | Bottom nav → Explore | Double-tap the top bar to jump back to page 1 and refresh recommendations. Images are preloaded for smooth scrolling. |
| Chat with an agent | Tap any agent card → Chat | Text + voice playback (openers are preloaded) + instant image generation. |
| Create or edit an agent | Explore → “Create/+” or Profile → My Agents | Guided flow with image upload and text-to-image background (`POST /api/v1/ai/agents/text-to-image`). |
| Subscribe or restore | Profile → VIP / Subscription | Uses Google Play Billing; see Troubleshooting if charges succeed but perks stay locked. |
| Manage notifications & privacy | Settings → Notifications / Privacy | Push powered by Firebase Cloud Messaging; toggle anytime. |
| Check version info | Settings → About | Version code comes from git commit count. If Play build lags behind, install the QA APK. |
| Send feedback or report | Chat → ⋮ → Report, or Profile → Feedback | Reports go through the Report Service; attach screenshots when possible. |

## Feature Deep Dive

### 1. Explore
- Double-tap the header to rewind to the top and refresh.
- Avatars/backgrounds preload so cards stay visible even on slow networks.
- Switch between Recommended, Favorites, Created by Me.
- *Screenshot placeholder:*
  
  ![Explore screenshot placeholder](<ADD_EXPLORE_SCREENSHOT_URL_HERE>)

### 2. Chats
- Every message supports voice playback; audio is cached locally (`AudioCacheManager`).
- Buttons such as Keep Talking and Message to Image fire Firebase events, helping support diagnose issues.
- “Network error” alerts usually clear after checking connectivity or switching back to the default backend on debug builds.
- *Screenshot placeholder:*
  
  ![Chat screenshot placeholder](<ADD_CHAT_SCREENSHOT_URL_HERE>)

### 3. Agents
- Follow/unfollow directly on Explore cards.
- Creation/editing supports uploads plus AI-generated art; failures surface clear error states (`AvatarManager`).
- Agent detail pages show AI-Generated media pulled from recent chats, with explicit labeling.

### 4. VIP / Subscription
- Plans run through Google Play Billing; benefits refresh automatically after purchase.
- If a transaction is stuck in “processing,” open Play Store → Account → Subscriptions to confirm payment status.
- “Restore Purchase” revalidates receipts. If that fails, capture the GPA order ID before contacting support.

### 5. Settings
- **Debug Backend Endpoint** (debug builds only): Change the API base URL at runtime; cache clears automatically so the next request uses the new server.
- **Help & Feedback**: Add your FAQ or form link here so end users can submit issues without leaving the app.
- **Remote Config**: Features such as auto-enabling Keep Talking are controlled centrally. Sudden UI changes may come from new Remote Config values.

## Troubleshooting

### Network / Sign-in
- **Google sign-in missing**: Install Google Play Services (GMS). Mainland China devices usually require manual GMS installation.
- **Blank screens / failed loads**: Clear IntelliMate storage in Android Settings and relaunch, or switch back to the default backend in debug builds.

### Chat & Media
- **Voice playback issues**: Check system volume. If playback keeps failing, clear cache or restart the app; audio will re-cache automatically.
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
