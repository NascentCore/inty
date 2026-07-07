/**
 * CREATED_BY_AGENT
 * 关键步骤总结：先把性别归一化为 male/female/unknown，再统一复用到筛选与统计，避免组件内重复判断。
 */
import type { Voice } from "../types";

export type VoiceGenderFilter = "all" | "male" | "female" | "unknown";
type NormalizedVoiceGender = Exclude<VoiceGenderFilter, "all">;

export const normalizeVoiceGender = (
  gender?: string,
): NormalizedVoiceGender => {
  const normalizedGender = (gender ?? "").trim().toLowerCase();
  if (normalizedGender === "male") {
    return "male";
  }
  if (normalizedGender === "female") {
    return "female";
  }
  return "unknown";
};

const getVoiceGenderFromLabels = (
  labels?: Record<string, string>,
): string | undefined => {
  if (!labels) {
    return undefined;
  }
  return labels.gender ?? labels.Gender ?? labels.sex ?? labels.Sex;
};

export const getNormalizedVoiceGender = (
  voice: Voice,
): NormalizedVoiceGender => {
  return normalizeVoiceGender(
    voice.gender ?? getVoiceGenderFromLabels(voice.labels),
  );
};

export const mapImateGenderToVoiceGenderFilter = (
  imateGender?: string,
): VoiceGenderFilter => {
  const normalizedImateGender = (imateGender ?? "").trim().toUpperCase();
  if (normalizedImateGender === "MALE") {
    return "male";
  }
  if (normalizedImateGender === "FEMALE") {
    return "female";
  }
  if (normalizedImateGender === "OTHER") {
    return "unknown";
  }
  return "all";
};

export const filterVoicesByGender = (
  voices: Voice[],
  genderFilter: VoiceGenderFilter,
): Voice[] => {
  if (genderFilter === "all") {
    return voices;
  }

  const strictlyMatchedVoices = voices.filter(
    (voice) => getNormalizedVoiceGender(voice) === genderFilter,
  );
  if (strictlyMatchedVoices.length > 0 || genderFilter === "unknown") {
    return strictlyMatchedVoices;
  }

  // ElevenLabs 音色常存在缺失性别标签的情况：
  // 当 male/female 严格匹配为空时，回退到 unknown，避免“有音色但列表全空”。
  return voices.filter(
    (voice) => getNormalizedVoiceGender(voice) === "unknown",
  );
};

export const getVoiceGenderStats = (voices: Voice[]) => {
  const stats: Record<NormalizedVoiceGender, number> = {
    male: 0,
    female: 0,
    unknown: 0,
  };
  voices.forEach((voice) => {
    stats[getNormalizedVoiceGender(voice)] += 1;
  });

  return {
    ...stats,
    total: voices.length,
  };
};
