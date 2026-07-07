const IMAGE_FEEDBACK_TARGET_PREFIX = "IMAGE_FEEDBACK_";

function fnv1aHashHex(input: string): string {
  let hash = 0x811c9dc5;
  for (let i = 0; i < input.length; i += 1) {
    hash ^= input.charCodeAt(i);
    hash = Math.imul(hash, 0x01000193);
  }
  return (hash >>> 0).toString(16).padStart(8, "0");
}

export function buildImageFeedbackTargetId(imageUrl: string): string {
  return `${IMAGE_FEEDBACK_TARGET_PREFIX}${fnv1aHashHex(imageUrl)}`;
}
