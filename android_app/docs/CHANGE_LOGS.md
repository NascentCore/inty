# IntelliMate Change Logs

> CREATED_BY_AGENT
> This content is injected into the Inty official assistant system message.
> Lines starting with ">" will be removed during injection.

- Only user-visible changes are recorded.
- Changes only affect debug build type's app is not listed.
- Write 1 sentence summary, this is for filling in Google Play release notes. And then nested with detailed description.


## 2026-04-12

- Chat always uses the standard HTTP chat completions API for sending messages.

## 2026-04-10

- Deleting your account from Settings now keeps the confirmation dialog open with a progress bar until the server confirms deletion.

## 2026-04-07

- Chat sends your **device local time and time zone** by default so AI replies can match the time of day.
- Debug builds only: turn this off under Settings → Debug Backend Endpoint → **User time context reporting** if you prefer not to send it.

## 2026-03-24

- Official Assistant quick actions above the chat input (**Test my MBTI type** and **Create my own iMate**) now sit on one horizontally scrollable row instead of stacking vertically.
- Those quick-action buttons now use the same translucent purple background and corner style as the chat input bar (replacing the previous gradient CTA look).
- Official Assistant FAQ suggestion chips now stack vertically and use the same semi-transparent dark bubble background style as AI chat messages.
- The Official Assistant FAQ intro line now uses the same white assistant-message text style and is localized via a new English string resource.
- Official Assistant FAQ suggestions now show only before the first user message in Official Assistant chat; after the first send, they stay hidden until the app is restarted.
- In the chat more-menu, tapping **Call** now also marks Official Assistant as "user has sent", while tapping **Reset** clears that flag back to false.

## 2026-03-23

- Explore page now shows a **重新加载** button under the network failure message, so users can retry loading iMates directly from the error state.

## 2026-03-12

- Chat image sending now preprocesses selected photos to a JPEG at ~57,600 total pixels before upload, keeps showing the original thumbnail during compression, switches to the compressed thumbnail when ready, and reuses that compressed local cache after upload to avoid an immediate re-download flicker.
- Added a new Me → Settings toggle, **Send UX/UI gesture signals** (default off), that controls whether chat background taps/swipes are sent to AI as original-image coordinate action messages.

## 2026-03-09

- Chat settings **Voice** picker now enforces gender matching for MALE/FEMALE iMates, so only same-gender Gemini voices are shown in the dropdown.
- After you react with 👍/👎 to a generated chat image, IntelliMate can show a once-per-local-day feedback prompt that opens a prefilled image-quality feedback form with the image attached.

## 2026-03-06

- Subscription (Premium) page layout and copy updated: title/subtitle now show **Upgrade to Premium** / **Premium enabled** and **Unlock 12 perks now!** / **12 perks Unlocked!** depending on subscription status; billing notice **Will charge [price] in the next billing cycle, cancel at any time** appears below plan cards; a **Benefit Details** table compares Free vs Premium (Daily Chat, Chat Memory, Voice, HD Voice, Voice Call Time, etc.); purchase button shows selected plan price and **Get Premium**; **Membership & Renewal Terms** link added at bottom.
- Subscription page background image (AI character) removed; page uses solid theme background. All subscription UI (plan cards, benefit table, purchase button, discount tags) now use **MaterialTheme** for colors, typography, and shapes.

## 2026-03-04

- Chat settings now include a VIP-gated **Voice** picker for Gemini voices. Non-subscribed users now see the same upgrade popup as **Models** when tapping Voice; subscribed users can select and save a per-chat voice for both auto-play and tap-to-play TTS.
- The chat settings **Voice** dropdown now shows a compact, scrollable list with 9 visible entries for easier browsing.
- Official Assistant chat now has a dedicated **Test my MBTI type** quick-action button above the input. Tapping it sends a structured MBTI interview starter prompt immediately, so users can begin guided type discovery in one tap.

## 2026-03-03

- After creating an iMate from Official Assistant chat (**+ Create your own iMate**), the app now opens the newly created iMate chat directly instead of switching to the Me tab.
- Chat image sending now starts uploading immediately after you pick a local photo in the input box, and while waiting for AI reply the outgoing bubble shows your local photo as a placeholder to avoid blank waiting states.

## 2026-03-02

- Official Assistant chat now includes a **"+ Create your own iMate"** button above the input box. It opens the iMate creation page, and auto-hides while the keyboard is open.
- Removed the **Create your own iMate** banner from the top of the Explore page; create iMate via Profile → My iMates.
- Chat input now supports sending **one selected image + text** in a single message, and chat bubbles can render **text + image** replies returned by `/api/v1/chat/completions/{agent_id}`.

## 2026-02-28

- Explore page now applies a gender preference filter in **New iMates for you**: users with `MALE`/`FEMALE` profiles see newly created iMates of the opposite gender, while `OTHER`/`NON_BINARY` profiles keep the existing unfiltered behavior.
- Official Assistant chat now shows up to 9 FAQ quick-question buttons near the top area; tapping a button fills the full question into the chat input box without sending it automatically.

## 2026-02-26

- Standardized chat bubble spacing on the chat page: user message bubbles now use the same vertical spacing as AI messages to improve readability.

## 2026-02-24

- Updated the middle icon in the bottom navigation bar: tapping it now opens chat with the Inty official assistant.
- Moved the iMate creation entry point to the top of Explore with a horizontal banner button: **"Create your own iMate"**.

## 2026-02-11

- Added `2026 LUNAR NEW YEAR CHARS` Section, with 10 specially crafted Chinese and Aisan female characters.
