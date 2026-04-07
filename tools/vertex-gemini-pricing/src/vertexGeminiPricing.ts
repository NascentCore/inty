/**
 * Vertex AI Generative AI pricing helpers for Gemini token estimates.
 * Source: https://cloud.google.com/vertex-ai/generative-ai/pricing (USD per 1M tokens unless noted).
 * Long-context rule (Gemini 2.5 / 3 Standard and Priority): when input context exceeds the threshold,
 * input and output tokens are billed at the "long" per-1M rates per Google footnote on that page.
 */

/** USD per 1 million tokens */
export interface IVertexGeminiRates {
  /** Price per 1M input tokens when input is within context threshold */
  inputPerMShort: number;
  /** Price per 1M input tokens when input exceeds context threshold */
  inputPerMLong: number;
  /** Price per 1M output tokens when input is within context threshold */
  outputPerMShort: number;
  /** Price per 1M output tokens when input exceeds context threshold */
  outputPerMLong: number;
  /** Input token count above which long rates apply (0 = always use short column only) */
  contextThresholdTokens: number;
}

export interface IVertexGeminiModelOption {
  id: string;
  label: string;
  group: string;
  rates: IVertexGeminiRates;
  /** Extra disclaimer shown under the form */
  footnote?: string;
}

/**
 * @param inputTokens - billable input tokens for one request
 * @param outputTokens - billable output tokens for one request
 * @param rates - model rates
 * @returns USD cost for one successful request (excluding tax, discounts, grounding, etc.)
 */
export function estimateVertexGeminiCallUsd(
  inputTokens: number,
  outputTokens: number,
  rates: IVertexGeminiRates,
): number {
  const long =
    rates.contextThresholdTokens > 0 && inputTokens > rates.contextThresholdTokens;
  const inRate = long ? rates.inputPerMLong : rates.inputPerMShort;
  const outRate = long ? rates.outputPerMLong : rates.outputPerMShort;
  return (inputTokens * inRate + outputTokens * outRate) / 1_000_000;
}

const K200 = 200_000;

/** Flat rate: same price regardless of input size (short and long columns equal). */
function flat(inputPerM: number, outputPerM: number): IVertexGeminiRates {
  return {
    inputPerMShort: inputPerM,
    inputPerMLong: inputPerM,
    outputPerMShort: outputPerM,
    outputPerMLong: outputPerM,
    contextThresholdTokens: 0,
  };
}

/** Tiered by input context length (Vertex footnote for 2.5 / 3 families). */
function tier200k(
  inShort: number,
  inLong: number,
  outShort: number,
  outLong: number,
): IVertexGeminiRates {
  return {
    inputPerMShort: inShort,
    inputPerMLong: inLong,
    outputPerMShort: outShort,
    outputPerMLong: outLong,
    contextThresholdTokens: K200,
  };
}

/**
 * Models and rate cards aligned to the public pricing tables (Standard / Priority / Flex-Batch where listed).
 * Image-only, audio-only, and grounding surcharges are out of scope for this token calculator.
 */
export const VERTEX_GEMINI_MODEL_OPTIONS: IVertexGeminiModelOption[] = [
  // Gemini 3 - Standard
  {
    id: 'g3.1-pro-standard',
    label: 'Gemini 3.1 Pro Preview (Standard)',
    group: 'Gemini 3 - Standard',
    rates: tier200k(2, 4, 12, 18),
  },
  {
    id: 'g3.1-flash-image-standard',
    label: 'Gemini 3.1 Flash Image Preview (Standard, text I/O)',
    group: 'Gemini 3 - Standard',
    rates: flat(0.5, 3),
    footnote: 'Image output is priced separately on the official page.',
  },
  {
    id: 'g3.1-flash-lite-standard',
    label: 'Gemini 3.1 Flash-Lite Preview (Standard, text/image/video in)',
    group: 'Gemini 3 - Standard',
    rates: flat(0.25, 1.5),
    footnote: 'Audio input uses a higher input rate on the official page.',
  },
  {
    id: 'g3-pro-standard',
    label: 'Gemini 3 Pro Preview (Standard)',
    group: 'Gemini 3 - Standard',
    rates: tier200k(2, 4, 12, 18),
  },
  {
    id: 'g3-pro-image-standard',
    label: 'Gemini 3 Pro Image Preview (Standard, text I/O)',
    group: 'Gemini 3 - Standard',
    rates: tier200k(2, 4, 12, 18),
    footnote: 'Image output is priced separately on the official page.',
  },
  {
    id: 'g3-flash-standard',
    label: 'Gemini 3 Flash Preview (Standard, text/image/video in)',
    group: 'Gemini 3 - Standard',
    rates: flat(0.5, 3),
    footnote: 'Audio input uses a higher input rate on the official page.',
  },
  // Gemini 3 - Priority
  {
    id: 'g3.1-pro-priority',
    label: 'Gemini 3.1 Pro Preview (Priority)',
    group: 'Gemini 3 - Priority',
    rates: tier200k(3.6, 7.2, 21.6, 32.4),
  },
  {
    id: 'g3.1-flash-lite-priority',
    label: 'Gemini 3.1 Flash-Lite Preview (Priority, text/image/video in)',
    group: 'Gemini 3 - Priority',
    rates: flat(0.45, 2.7),
  },
  {
    id: 'g3-pro-priority',
    label: 'Gemini 3 Pro Preview (Priority)',
    group: 'Gemini 3 - Priority',
    rates: tier200k(3.6, 7.2, 21.6, 32.4),
  },
  {
    id: 'g3-flash-priority',
    label: 'Gemini 3 Flash Preview (Priority, text/image/video in)',
    group: 'Gemini 3 - Priority',
    rates: flat(0.9, 5.4),
  },
  // Gemini 3 - Flex / Batch
  {
    id: 'g3.1-pro-flex',
    label: 'Gemini 3.1 Pro Preview (Flex / Batch)',
    group: 'Gemini 3 - Flex / Batch',
    rates: tier200k(1, 2, 6, 9),
  },
  {
    id: 'g3.1-flash-image-flex',
    label: 'Gemini 3.1 Flash Image Preview (Flex / Batch, text I/O)',
    group: 'Gemini 3 - Flex / Batch',
    rates: flat(0.25, 1.5),
  },
  {
    id: 'g3.1-flash-lite-flex',
    label: 'Gemini 3.1 Flash-Lite Preview (Flex / Batch, text/image/video in)',
    group: 'Gemini 3 - Flex / Batch',
    rates: flat(0.13, 0.75),
  },
  {
    id: 'g3-pro-flex',
    label: 'Gemini 3 Pro Preview (Flex / Batch)',
    group: 'Gemini 3 - Flex / Batch',
    rates: tier200k(1, 2, 6, 9),
  },
  {
    id: 'g3-flash-flex',
    label: 'Gemini 3 Flash Preview (Flex / Batch, text/image/video in)',
    group: 'Gemini 3 - Flex / Batch',
    rates: flat(0.25, 1.5),
  },
  // Gemini 2.5 - Standard
  {
    id: 'g2.5-pro-standard',
    label: 'Gemini 2.5 Pro (Standard)',
    group: 'Gemini 2.5 - Standard',
    rates: tier200k(1.25, 2.5, 10, 15),
  },
  {
    id: 'g2.5-pro-computer-standard',
    label: 'Gemini 2.5 Pro Computer Use Preview (Standard)',
    group: 'Gemini 2.5 - Standard',
    rates: tier200k(1.25, 2.5, 10, 15),
  },
  {
    id: 'g2.5-flash-standard',
    label: 'Gemini 2.5 Flash (Standard, text/image/video in)',
    group: 'Gemini 2.5 - Standard',
    rates: flat(0.3, 2.5),
    footnote: 'Audio input uses a higher input rate on the official page.',
  },
  {
    id: 'g2.5-flash-image-standard',
    label: 'Gemini 2.5 Flash Image (Standard, text I/O)',
    group: 'Gemini 2.5 - Standard',
    rates: flat(0.3, 2.5),
    footnote: 'Image output is priced separately on the official page.',
  },
  {
    id: 'g2.5-live-standard',
    label: 'Gemini 2.5 Flash Live API (Standard, text only)',
    group: 'Gemini 2.5 - Standard',
    rates: flat(0.5, 2),
    footnote: 'Audio and video/image tokens use different rates on the official page.',
  },
  {
    id: 'g2.5-flash-lite-standard',
    label: 'Gemini 2.5 Flash-Lite (Standard, text/image/video in)',
    group: 'Gemini 2.5 - Standard',
    rates: flat(0.1, 0.4),
    footnote: 'Audio input uses a different input rate on the official page.',
  },
  // Gemini 2.5 - Priority
  {
    id: 'g2.5-pro-priority',
    label: 'Gemini 2.5 Pro (Priority)',
    group: 'Gemini 2.5 - Priority',
    rates: tier200k(2.25, 4.5, 18, 27),
  },
  {
    id: 'g2.5-flash-priority',
    label: 'Gemini 2.5 Flash (Priority, text/image/video in)',
    group: 'Gemini 2.5 - Priority',
    rates: flat(0.54, 4.5),
  },
  {
    id: 'g2.5-flash-lite-priority',
    label: 'Gemini 2.5 Flash-Lite (Priority, text/image/video in)',
    group: 'Gemini 2.5 - Priority',
    rates: flat(0.18, 0.72),
  },
  // Gemini 2.5 - Flex / Batch
  {
    id: 'g2.5-pro-flex',
    label: 'Gemini 2.5 Pro (Flex / Batch)',
    group: 'Gemini 2.5 - Flex / Batch',
    rates: tier200k(0.625, 1.25, 5, 7.5),
  },
  {
    id: 'g2.5-flash-flex',
    label: 'Gemini 2.5 Flash (Flex / Batch, text/image/video in)',
    group: 'Gemini 2.5 - Flex / Batch',
    rates: flat(0.15, 1.25),
  },
  {
    id: 'g2.5-flash-image-flex',
    label: 'Gemini 2.5 Flash Image (Flex / Batch, text I/O)',
    group: 'Gemini 2.5 - Flex / Batch',
    rates: flat(0.15, 1.25),
  },
  {
    id: 'g2.5-flash-lite-flex',
    label: 'Gemini 2.5 Flash-Lite (Flex / Batch, text/image/video in)',
    group: 'Gemini 2.5 - Flex / Batch',
    rates: flat(0.05, 0.2),
  },
  // Gemini 2.0 - token table
  {
    id: 'g2-flash',
    label: 'Gemini 2.0 Flash (Standard)',
    group: 'Gemini 2.0',
    rates: flat(0.15, 0.6),
    footnote: 'Batch API uses lower rates on the official page.',
  },
  {
    id: 'g2-flash-batch',
    label: 'Gemini 2.0 Flash (Batch API)',
    group: 'Gemini 2.0',
    rates: flat(0.075, 0.3),
  },
  {
    id: 'g2-live',
    label: 'Gemini 2.0 Flash Live API (text only)',
    group: 'Gemini 2.0',
    rates: flat(0.5, 2),
    footnote: 'Audio and video/image tokens use different rates on the official page.',
  },
  {
    id: 'g2-flash-lite',
    label: 'Gemini 2.0 Flash-Lite (Standard)',
    group: 'Gemini 2.0',
    rates: flat(0.075, 0.3),
  },
  {
    id: 'g2-flash-lite-batch',
    label: 'Gemini 2.0 Flash-Lite (Batch API)',
    group: 'Gemini 2.0',
    rates: flat(0.0375, 0.15),
  },
];

export function getVertexGeminiModelById(id: string): IVertexGeminiModelOption | undefined {
  return VERTEX_GEMINI_MODEL_OPTIONS.find((m) => m.id === id);
}

/** @returns unique group labels in display order */
export function getVertexGeminiGroups(): string[] {
  const seen = new Set<string>();
  const ordered: string[] = [];
  for (const m of VERTEX_GEMINI_MODEL_OPTIONS) {
    if (!seen.has(m.group)) {
      seen.add(m.group);
      ordered.push(m.group);
    }
  }
  return ordered;
}
