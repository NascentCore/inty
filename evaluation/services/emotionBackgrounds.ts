import type { Emotion } from "./gemini";

// 为每种情绪提供一个轻量级 SVG 背景（Data URI）
// 采用柔和渐变 + 半透明图形，确保文字仍可读

function svgData(svg: string): string {
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

function gradient(a: string, b: string) {
  return `<defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="${a}"/>
      <stop offset="100%" stop-color="${b}"/>
    </linearGradient>
  </defs>`;
}

function baseSvg(bgA: string, bgB: string, overlay = "#ffffff", alpha = 0.08) {
  return `<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1200 800'>
${gradient(bgA, bgB)}
<rect width='1200' height='800' fill='url(#g)'/>
<g fill='${overlay}' fill-opacity='${alpha}'>
  <circle cx='200' cy='150' r='120'/>
  <circle cx='1000' cy='200' r='160'/>
  <circle cx='400' cy='650' r='140'/>
  <rect x='800' y='520' width='220' height='140' rx='24'/>
</g>
</svg>`;
}

const map: Record<Emotion, string> = {
  Neutral: svgData(baseSvg("#e9edf1", "#dce3ea")),
  Happy: svgData(baseSvg("#ffe08a", "#ffd06b")),
  Sad: svgData(baseSvg("#a0c4ff", "#72a0e6")),
  Angry: svgData(baseSvg("#ff8a8a", "#ff5e5e")),
  Surprised: svgData(baseSvg("#b2f7ef", "#94e6de")),
  Fearful: svgData(baseSvg("#c7b8ea", "#a996e0")),
  Disgusted: svgData(baseSvg("#b8e994", "#9bd37a")),
  Shy: svgData(baseSvg("#ffd6e7", "#ffb3cf")),
  Confused: svgData(baseSvg("#e6e6fa", "#d1d1f6")),
  Excited: svgData(baseSvg("#ffcf99", "#ffb266")),
  Bored: svgData(baseSvg("#e0e0e0", "#c9c9c9")),
  Tired: svgData(baseSvg("#cfd8dc", "#b0bec5")),
  Loving: svgData(baseSvg("#ffb3c1", "#ff8faa")),
  Proud: svgData(baseSvg("#ffd280", "#ffbd4d")),
  Embarrassed: svgData(baseSvg("#ffc0cb", "#ff9db2")),
  Lonely: svgData(baseSvg("#b3cde0", "#8db3cc")),
  Anxious: svgData(baseSvg("#ffd1a1", "#ffb07a")),
  Calm: svgData(baseSvg("#b2f2bb", "#8fe3a8")),
  Curious: svgData(baseSvg("#c3f0ff", "#9de5ff")),
  Determined: svgData(baseSvg("#b5e48c", "#76c893")),
};

export function getEmotionBackgroundUrl(emotion: Emotion): string {
  return map[emotion] || map.Neutral;
}
