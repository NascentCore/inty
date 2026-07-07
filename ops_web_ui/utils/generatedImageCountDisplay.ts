/**
 * Antd Badge 默认超过 99 会显示为 99+，这里将上限抬高以展示真实数量。
 */
export const GENERATED_IMAGE_COUNT_BADGE_OVERFLOW_COUNT =
  Number.MAX_SAFE_INTEGER;

export const normalizeGeneratedImageCount = (
  count: number | undefined,
): number => {
  if (typeof count !== "number" || !Number.isFinite(count)) {
    return 0;
  }

  if (count <= 0) {
    return 0;
  }

  return Math.floor(count);
};
