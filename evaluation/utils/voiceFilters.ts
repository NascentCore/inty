/**
 * CREATED_BY_AGENT
 * 关键步骤总结：先把性别归一化为 male/female/unknown，再统一复用到筛选与统计，避免组件内重复判断。
 */
import type { Voice } from "../types";

export type VoiceGenderFilter = "all" | "male" | "female" | "unknown";
type NormalizedVoiceGender = Exclude<VoiceGenderFilter, "all">;

export const normalizeVoiceGender = (gender?: string): NormalizedVoiceGender => {
  const normalizedGender = (gender ?? "").trim().toLowerCase();
  if (normalizedGender === "male") {
    return "male";
  }
  if (normalizedGender === "female") {
    return "female";
  }
  return "unknown";
};

export const filterVoicesByGender = (
  voices: Voice[],
  genderFilter: VoiceGenderFilter,
): Voice[] => {
  if (genderFilter === "all") {
    return voices;
  }
  return voices.filter(
    (voice) => normalizeVoiceGender(voice.gender) === genderFilter,
  );
};

export const getVoiceGenderStats = (voices: Voice[]) => {
  const stats: Record<NormalizedVoiceGender, number> = {
    male: 0,
    female: 0,
    unknown: 0,
  };
  voices.forEach((voice) => {
    stats[normalizeVoiceGender(voice.gender)] += 1;
  });

  return {
    ...stats,
    total: voices.length,
  };
};
