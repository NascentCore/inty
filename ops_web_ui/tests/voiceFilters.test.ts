/**
 * CREATED_BY_AGENT
 */
import { describe, expect, it } from "vitest";
import type { Voice } from "../types";
import {
  filterVoicesByGender,
  getNormalizedVoiceGender,
  getVoiceGenderStats,
  mapImateGenderToVoiceGenderFilter,
  normalizeVoiceGender,
} from "../utils/voiceFilters";

const buildVoice = (
  voiceId: string,
  gender?: string,
  labels?: Record<string, string>,
): Voice =>
  ({
    voice_id: voiceId,
    name: voiceId,
    gender,
    labels,
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

  it("falls back to unknown voices when strict male/female match is empty", () => {
    const voices = [
      buildVoice("v-unknown-1"),
      buildVoice("v-unknown-2", undefined, { age: "young" }),
    ];

    expect(
      filterVoicesByGender(voices, "male").map((voice) => voice.voice_id),
    ).toEqual(["v-unknown-1", "v-unknown-2"]);
    expect(
      filterVoicesByGender(voices, "female").map((voice) => voice.voice_id),
    ).toEqual(["v-unknown-1", "v-unknown-2"]);
  });

  it("uses labels.gender when top-level gender is missing", () => {
    const voices = [
      buildVoice("v-el-female", undefined, { gender: "female" }),
      buildVoice("v-el-male", undefined, { gender: "male" }),
      buildVoice("v-el-unknown", undefined, { age: "young" }),
    ];

    expect(getNormalizedVoiceGender(voices[0])).toBe("female");
    expect(getNormalizedVoiceGender(voices[1])).toBe("male");
    expect(getNormalizedVoiceGender(voices[2])).toBe("unknown");

    expect(
      filterVoicesByGender(voices, "female").map((voice) => voice.voice_id),
    ).toEqual(["v-el-female"]);
    expect(
      filterVoicesByGender(voices, "male").map((voice) => voice.voice_id),
    ).toEqual(["v-el-male"]);
  });

  it("maps iMate gender to voice gender filter", () => {
    expect(mapImateGenderToVoiceGenderFilter("MALE")).toBe("male");
    expect(mapImateGenderToVoiceGenderFilter("female")).toBe("female");
    expect(mapImateGenderToVoiceGenderFilter("OTHER")).toBe("unknown");
    expect(mapImateGenderToVoiceGenderFilter("")).toBe("all");
    expect(mapImateGenderToVoiceGenderFilter(undefined)).toBe("all");
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
