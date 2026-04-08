/**
 * Binds the static HTML in index.html to vertexGeminiPricing helpers.
 */

import {
  estimateVertexGeminiCallUsd,
  getVertexGeminiGroups,
  getVertexGeminiModelById,
  VERTEX_GEMINI_MODEL_OPTIONS,
} from './vertexGeminiPricing';

const DEFAULT_MODEL_ID = 'g2.5-pro-standard';

function parseNonNegativeInt(raw: string, fallback: number): number {
  const n = Number.parseInt(raw.replace(/\s/g, ''), 10);
  if (!Number.isFinite(n) || n < 0) {
    return fallback;
  }
  return n;
}

function parseCallCount(raw: string): number {
  const n = Number.parseInt(raw.replace(/\s/g, ''), 10);
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

function fillModelSelect(select: HTMLSelectElement): void {
  const groups = getVertexGeminiGroups();
  for (const g of groups) {
    const og = document.createElement('optgroup');
    og.label = g;
    for (const m of VERTEX_GEMINI_MODEL_OPTIONS.filter((x) => x.group === g)) {
      const opt = document.createElement('option');
      opt.value = m.id;
      opt.textContent = m.label;
      og.appendChild(opt);
    }
    select.appendChild(og);
  }
  select.value = DEFAULT_MODEL_ID;
}

function render(): void {
  const select = document.getElementById('vgp-model') as HTMLSelectElement | null;
  const inputIn = document.getElementById('vgp-in') as HTMLInputElement | null;
  const inputOut = document.getElementById('vgp-out') as HTMLInputElement | null;
  const inputN = document.getElementById('vgp-n') as HTMLInputElement | null;
  const warn = document.getElementById('vgp-warn') as HTMLParagraphElement | null;
  const longNote = document.getElementById('vgp-long') as HTMLParagraphElement | null;
  const footEl = document.getElementById('vgp-footnote') as HTMLParagraphElement | null;
  const perCallEl = document.getElementById('vgp-per-call') as HTMLSpanElement | null;
  const totalEl = document.getElementById('vgp-total') as HTMLSpanElement | null;
  const totalLabel = document.getElementById('vgp-total-label') as HTMLSpanElement | null;

  if (
    !select ||
    !inputIn ||
    !inputOut ||
    !inputN ||
    !warn ||
    !longNote ||
    !footEl ||
    !perCallEl ||
    !totalEl ||
    !totalLabel
  ) {
    return;
  }

  const modelId = select.value;
  const model = getVertexGeminiModelById(modelId);
  const inputTokens = parseNonNegativeInt(inputIn.value, 0);
  const outputTokens = parseNonNegativeInt(inputOut.value, 0);
  const callCount = parseCallCount(inputN.value);

  if (!model) {
    warn.hidden = false;
    longNote.hidden = true;
    footEl.hidden = true;
    perCallEl.textContent = formatUsd6(0);
    totalEl.textContent = formatUsd6(0);
    totalLabel.textContent = `Total for ${callCount.toLocaleString('en-US')} call${callCount === 1 ? '' : 's'}`;
    return;
  }

  warn.hidden = true;

  const longContext =
    model.rates.contextThresholdTokens > 0 &&
    inputTokens > model.rates.contextThresholdTokens;
  if (longContext) {
    longNote.hidden = false;
    longNote.textContent = `Long-context rates apply because input tokens exceed ${model.rates.contextThresholdTokens.toLocaleString('en-US')} (per Google footnote on the pricing page for this model family).`;
  } else {
    longNote.hidden = true;
  }

  if (model.footnote) {
    footEl.hidden = false;
    footEl.textContent = model.footnote;
  } else {
    footEl.hidden = true;
  }

  const perCallUsd = estimateVertexGeminiCallUsd(
    inputTokens,
    outputTokens,
    model.rates,
  );
  const totalUsd = perCallUsd * callCount;

  perCallEl.textContent = formatUsd6(perCallUsd);
  totalEl.textContent = formatUsd6(totalUsd);
  totalLabel.textContent = `Total for ${callCount.toLocaleString('en-US')} call${callCount === 1 ? '' : 's'}`;
}

function main(): void {
  const select = document.getElementById('vgp-model') as HTMLSelectElement | null;
  if (!select) {
    return;
  }
  fillModelSelect(select);

  const inputs: Element[] = [
    select,
    document.getElementById('vgp-in') as HTMLInputElement,
    document.getElementById('vgp-out') as HTMLInputElement,
    document.getElementById('vgp-n') as HTMLInputElement,
  ].filter(Boolean);

  for (const el of inputs) {
    el.addEventListener('input', render);
    el.addEventListener('change', render);
  }

  render();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', main);
} else {
  main();
}
