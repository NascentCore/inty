/**
 * Vertex AI Gemini token cost estimator (USD) from published list prices.
 * Route: /vertex-gemini-pricing
 */

import React, { useMemo, useState } from 'react';
import {
  estimateVertexGeminiCallUsd,
  getVertexGeminiGroups,
  getVertexGeminiModelById,
  VERTEX_GEMINI_MODEL_OPTIONS,
} from '@/utils/vertexGeminiPricing';
import './index.less';

const PRICING_DOC_URL =
  'https://cloud.google.com/vertex-ai/generative-ai/pricing';

const DEFAULT_MODEL_ID = 'g2.5-pro-standard';

function parseNonNegativeInt(raw: string, fallback: number): number {
  const n = Number.parseInt(raw.replaceAll(/\s/g, ''), 10);
  if (!Number.isFinite(n) || n < 0) {
    return fallback;
  }
  return n;
}

/**
 * @param raw - user text for number of calls
 * @returns integer call count; invalid input falls back to 1; 0 is allowed
 */
function parseCallCount(raw: string): number {
  const n = Number.parseInt(raw.replaceAll(/\s/g, ''), 10);
  if (!Number.isFinite(n) || n < 0) {
    return 1;
  }
  return n;
}

function formatUsd6(value: number): string {
  return value.toLocaleString('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 6,
  });
}

/**
 * Standalone pricing calculator page
 */
const VertexGeminiPricingPage: React.FC = () => {
  const [modelId, setModelId] = useState<string>(DEFAULT_MODEL_ID);
  const [inputTokensStr, setInputTokensStr] = useState<string>('1000');
  const [outputTokensStr, setOutputTokensStr] = useState<string>('500');
  const [callCountStr, setCallCountStr] = useState<string>('1');

  const model = getVertexGeminiModelById(modelId);
  const inputTokens = parseNonNegativeInt(inputTokensStr, 0);
  const outputTokens = parseNonNegativeInt(outputTokensStr, 0);
  const callCount = parseCallCount(callCountStr);

  const perCallUsd = model
    ? estimateVertexGeminiCallUsd(inputTokens, outputTokens, model.rates)
    : 0;
  const totalUsd = perCallUsd * callCount;

  const longContext =
    model &&
    model.rates.contextThresholdTokens > 0 &&
    inputTokens > model.rates.contextThresholdTokens;

  const groups = useMemo(() => getVertexGeminiGroups(), []);

  return (
    <div className="vertex-gemini-pricing-page">
      <header className="vertex-gemini-pricing-page__header">
        <h1 className="vertex-gemini-pricing-page__title">
          Vertex AI Gemini pricing estimator
        </h1>
        <p className="vertex-gemini-pricing-page__subtitle">
          Estimate USD cost from token counts using the public Vertex AI
          Generative AI pricing tables. This is not an invoice; actual billing
          may differ (currency, discounts, free tiers, grounding, modality
          splits, failed requests, and rounding).
        </p>
        <a
          className="vertex-gemini-pricing-page__doc-link"
          href={PRICING_DOC_URL}
          target="_blank"
          rel="noreferrer"
        >
          Open official pricing page
        </a>
      </header>

      <section className="vertex-gemini-pricing-page__card" aria-label="Calculator">
        <div className="vertex-gemini-pricing-page__field">
          <label className="vertex-gemini-pricing-page__label" htmlFor="vgp-model">
            Model and price tier
          </label>
          <select
            id="vgp-model"
            className="vertex-gemini-pricing-page__select"
            value={modelId}
            onChange={(e) => setModelId(e.target.value)}
          >
            {groups.map((g) => (
              <optgroup key={g} label={g}>
                {VERTEX_GEMINI_MODEL_OPTIONS.filter((m) => m.group === g).map(
                  (m) => (
                    <option key={m.id} value={m.id}>
                      {m.label}
                    </option>
                  ),
                )}
              </optgroup>
            ))}
          </select>
        </div>

        <div className="vertex-gemini-pricing-page__row">
          <div className="vertex-gemini-pricing-page__field">
            <label className="vertex-gemini-pricing-page__label" htmlFor="vgp-in">
              Input tokens (per call)
            </label>
            <input
              id="vgp-in"
              className="vertex-gemini-pricing-page__input"
              type="text"
              inputMode="numeric"
              value={inputTokensStr}
              onChange={(e) => setInputTokensStr(e.target.value)}
              autoComplete="off"
            />
          </div>
          <div className="vertex-gemini-pricing-page__field">
            <label className="vertex-gemini-pricing-page__label" htmlFor="vgp-out">
              Output tokens (per call)
            </label>
            <input
              id="vgp-out"
              className="vertex-gemini-pricing-page__input"
              type="text"
              inputMode="numeric"
              value={outputTokensStr}
              onChange={(e) => setOutputTokensStr(e.target.value)}
              autoComplete="off"
            />
          </div>
        </div>

        <div className="vertex-gemini-pricing-page__field">
          <label className="vertex-gemini-pricing-page__label" htmlFor="vgp-n">
            Number of calls (N)
          </label>
          <input
            id="vgp-n"
            className="vertex-gemini-pricing-page__input vertex-gemini-pricing-page__input--narrow"
            type="text"
            inputMode="numeric"
            value={callCountStr}
            onChange={(e) => setCallCountStr(e.target.value)}
            autoComplete="off"
          />
        </div>

        {!model && (
          <p className="vertex-gemini-pricing-page__warn" role="alert">
            Unknown model selection.
          </p>
        )}

        {model && longContext && (
          <p className="vertex-gemini-pricing-page__note">
            Long-context rates apply because input tokens exceed{' '}
            {model.rates.contextThresholdTokens.toLocaleString('en-US')} (per
            Google footnote on the pricing page for this model family).
          </p>
        )}

        {model?.footnote && (
          <p className="vertex-gemini-pricing-page__note">{model.footnote}</p>
        )}

        <div className="vertex-gemini-pricing-page__results" aria-live="polite">
          <div className="vertex-gemini-pricing-page__result-row">
            <span className="vertex-gemini-pricing-page__result-label">
              Estimated cost per call
            </span>
            <span className="vertex-gemini-pricing-page__result-value">
              {formatUsd6(perCallUsd)}
            </span>
          </div>
          <div className="vertex-gemini-pricing-page__result-row vertex-gemini-pricing-page__result-row--total">
            <span className="vertex-gemini-pricing-page__result-label">
              Total for {callCount.toLocaleString('en-US')} call
              {callCount === 1 ? '' : 's'}
            </span>
            <span className="vertex-gemini-pricing-page__result-value">
              {formatUsd6(totalUsd)}
            </span>
          </div>
        </div>
      </section>
    </div>
  );
};

export default VertexGeminiPricingPage;
