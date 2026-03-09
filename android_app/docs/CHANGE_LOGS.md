# IntelliMate Change Logs

> CREATED_BY_AGENT
> This content is injected into the Inty official assistant system message.
> Lines starting with ">" will be removed during injection.

- Only user-visible changes are recorded.
- Changes only affect debug build type's app is not listed.
- Each feature 1 sentence, be very concise.


## 2026-03-09

- Chat settings **Voice** picker now enforces gender matching for MALE/FEMALE iMates, so only same-gender Gemini voices are shown in the dropdown.

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
