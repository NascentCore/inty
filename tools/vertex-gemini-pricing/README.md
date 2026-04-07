# Vertex Gemini pricing estimator

Static page that estimates USD cost from input/output token counts using the public [Vertex AI Generative AI pricing](https://cloud.google.com/vertex-ai/generative-ai/pricing) tables.

## Use

1. Install and build the bundled script:

```bash
cd tools/vertex-gemini-pricing
yarn install
yarn build
```

2. Open `index.html` in a browser (file URL or any static server). The page loads `dist/app.js`.

For a quick local server from the repo root:

```bash
cd tools/vertex-gemini-pricing
yarn build
python3 -m http.server 8765
```

Then open `http://127.0.0.1:8765/index.html`.

## Develop

```bash
yarn typecheck
yarn build   # esbuild bundle to dist/app.js
```
