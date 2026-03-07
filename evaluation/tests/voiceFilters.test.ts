/**
 * CREATED_BY_AGENT
 */
import { describe, expect, it } from "vitest";
import type { Voice } from "../types";
import {
  filterVoicesByGender,
  getVoiceGenderStats,
  normalizeVoiceGender,
} from "../utils/voiceFilters";

const buildVoice = (voiceId: string, gender?: string): Voice =>
  ({
    voice_id: voiceId,
    name: voiceId,
    gender,
  }) as Voice;

describe("voiceFilters", () => {
  it("normalizes voice gender to male/female/unknown", () => {
    expect(normalizeVoiceGender("male")).toBe("male");
    expect(normalizeVoiceGender("FEMALE")).toBe("female");
    expect(normalizeVoiceGender("")).toBe("unknown");
    expect(normalizeVoiceGender(undefined)).toBe("unknown");
    expect(normalizeVoiceGender("non-binary")).toBe("unknown");
  });

  it("filters voices by gender", () => {
    const voices = [
      buildVoice("v-male", "male"),
      buildVoice("v-female", "female"),
      buildVoice("v-unknown"),
    ];

    expect(filterVoicesByGender(voices, "all")).toEqual(voices);
    expect(
      filterVoicesByGender(voices, "male").map((voice) => voice.voice_id),
    ).toEqual(["v-male"]);
    expect(
      filterVoicesByGender(voices, "female").map((voice) => voice.voice_id),
    ).toEqual(["v-female"]);
    expect(
      filterVoicesByGender(voices, "unknown").map((voice) => voice.voice_id),
    ).toEqual(["v-unknown"]);
  });

  it("counts gender stats with unknown fallback", () => {
    const voices = [
      buildVoice("voice-1", "male"),
      buildVoice("voice-2", "female"),
      buildVoice("voice-3", "other"),
      buildVoice("voice-4"),
    ];

    expect(getVoiceGenderStats(voices)).toEqual({
      male: 1,
      female: 1,
      unknown: 2,
      total: 4,
    });
  });
});
