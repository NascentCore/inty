export const IMAGE_FEEDBACK_PROMPT_LAST_DATE_KEY =
  "chat_image_feedback_prompt_last_local_date";

export function toLocalCalendarDateKey(now: Date): string {
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function shouldShowImageFeedbackPrompt(
  lastShownDateKey: string | null,
  now: Date,
): boolean {
  return lastShownDateKey !== toLocalCalendarDateKey(now);
}
