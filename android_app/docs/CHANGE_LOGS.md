# IntelliMate Change Logs

> CREATED_BY_AGENT
> This content is injected into the IntelliMate official assistant system message.
> Lines starting with ">" will be removed during injection.

Only user-visible changes are recorded

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

- Updated the middle icon in the bottom navigation bar: tapping it now opens chat with the IntelliMate official assistant.
- Moved the iMate creation entry point to the top of Explore with a horizontal banner button: **"Create your own iMate"**.

## 2026-02-11

- Added `2026 LUNAR NEW YEAR CHARS` Section, with 10 specially crafted Chinese and Aisan female characters.
