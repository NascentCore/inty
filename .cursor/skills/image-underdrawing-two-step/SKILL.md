---
name: image-underdrawing-two-step
description: >-
  Two-pass image generation for accurate text, numbers, and topology: Layer 1
  deterministic underdrawing (SVG, code-to-raster, or grid YAML) then Layer 2
  image+text-to-image "painting". Triggers: spiral paths, counted steps, charts,
  repeating shape sequences, any layout where generative models garble math or
  glyphs; user asks for underdrawing, i2i refinement, or Sam Collins method.
---

# Image generation via underdrawing (two steps)

## When to use

- The brief requires **correct digits or short text** *and* a **non-trivial layout** (paths, grids, counts, adjacency).
- A single text-to-image pass is likely to **break numbering, order, or geometry** (spirals, boards, "N identical items in a pattern").
- The toolchain supports **image + text → image** for a second pass (often called image-to-image or multimodal edit).

## When not to use

- Pure mood / portrait / landscape with **no structural contract** (single-pass is enough).
- Only a text-to-image API is available and **no** reliable way to feed the underdrawing raster into the model.
- Strict pixel-perfect output is required: treat model output as **approximate**; verify by eye or regenerate.

## Core idea

Use **deterministic tools** for what they excel at (math, placement, vector text) and **generative image models** for what they excel at (materials, lighting, atmosphere). Outline first, paint second. Primary reference: [Using "underdrawings" for accurate text and numbers](https://samcollins.blog/underdrawings).

## Agent checklist

1. **Clarify the contract** (counts, direction, start/end labels, shape cycle if any). Write it in plain language the Layer-2 prompt will repeat verbatim.
2. **Produce Layer 1 (underdrawing)** as something you can rasterize or already is a clean diagram image:
   - **SVG** (default for arbitrary 2D layout: paths, polygons, spiral placement, centered labels).
   - **Matrices / labeled grids**: use [draw-grid-diagram](/.cursor/skills/draw-grid-diagram/SKILL.md) (YAML → matplotlib PNG) instead of reinventing layout code.
   - **HTML/CSS** is acceptable when faster for the author; still export to a **flat raster** before Layer 2 if the product pipeline expects pixels.
3. **Optional raster export** (local sanity check, no repo script required): if `rsvg-convert` is installed, `rsvg-convert -w WIDTH -h HEIGHT in.svg -o under.png`; otherwise use any trusted SVG→PNG path (browser, design tool).
4. **Layer 2 prompt**: attach the underdrawing image; describe the **target look** *and* **re-state topology** (same step count, same winding, same start/finish semantics, preserve legible numbers). Keep stylistic flourishes in separate sentences so constraints stay scannable.
5. **Verify**: zoom the result and read every critical label; if wrong, tighten Layer-2 preservation language or regenerate Layer 1 with higher contrast / larger type / fewer occluding decorative strokes.

## Prompt templates

Replace `{{...}}` placeholders; keep topology sentences even if they feel redundant.

### Step 1 — structured underdrawing (example: SVG via model or hand-authored)

```text
Make an SVG of {{N}} stepping stones arranged in a spiral, winding {{counter-clockwise|clockwise}} inward from start at the outside (1) to finish at the centre ({{N}}), each stone numbered consecutively from 1 to {{N}}. Each stone is a different shape, repeating this cycle: {{shape1}}, {{shape2}}, {{shape3}}, {{shape4}}. Use a clear light background; numbers must be high-contrast and centered in each stone; optional thin dashed connectors between consecutive stones. Title: "{{title}}". Subtitle: "{{subtitle}}".
```

### Step 2 — image + text → image (paint on top of the underdrawing)

```text
Transform this image into {{style_and_materials}}, arranged along the same spiral path winding {{counter-clockwise|clockwise}} inward from start (1) at the outside to finish ({{N}}) at the centre. Preserve the exact count, order, and positions of the numbered items; keep every number from 1 to {{N}} readable and correct. {{camera_and_lighting}}.
```

### Minimal spiral candy example (concrete)

**Step 1**

```text
Make an SVG of 50 stepping stones arranged in a spiral, winding counter-clockwise inward from start at the outside (1) to finish at the centre (50), each stone numbered consecutively from 1 to 50. Each stone is a different shape: circle, square, triangle, hexagon.
```

**Step 2**

```text
Transform this image into a photographed claymation diorama of assorted artisan chocolates and candies, arranged in a spiral path winding counter-clockwise inward from start (1) at the outside to finish (50) at the centre, viewed from a low-angle tilted perspective.
```

## Quality notes

- **Underdrawing**: prefer large numerals, simple fills, and strong figure/ground contrast so the second pass can "lock on" without smearing glyphs.
- **Painting pass**: explicitly forbid changing topology ("do not add or remove stones", "do not reorder numbers"). If the model still drifts, shorten the style paragraph and strengthen preservation sentences.
- **Expectation**: the method is **much better** than single-pass for this class of problem; it is **not** a mathematical proof—spot-check results.

## Model capability

Layer 2 requires a workflow where the model accepts **an input image plus a text prompt** and returns a **new image**. Vendor names and model IDs change; pick any current product that supports that interface. The blog author used a Gemini-class pipeline as a worked example; mirror that shape of API in your environment.
