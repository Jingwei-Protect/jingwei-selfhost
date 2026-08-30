# Jingwei self-host

**English first.** Chinese: [README_zh.md](README_zh.md).

This repository runs **Protect**, **Verify**, and the **layer matrix** on your computer. Images you upload stay local; they are not sent to [jwprotect.com](https://jwprotect.com). That site is the maintained product (community, billing, latest UI). This repo is **not** the official website.

Jingwei is a layered attribution tool: invisible claims you can read back on Verify, plus optional visible layers that make AI wash-out and casual theft more expensive. Nothing here is a guarantee against a given editor.

## What you get

| Open | Purpose |
|------|---------|
| [Protect](http://127.0.0.1:8080/protect) | Upload a file, choose a base mode, preview, download a protected copy. No account. |
| [Verify](http://127.0.0.1:8080/verify) | Upload a protected file and read JW, DWT, LSB, tracking anchors, and metadata. |
| [Layer matrix](http://127.0.0.1:8080/guide/watermark-matrix) | The same visible-layer pairs as in this README, with a slider. Live after Docker is up. |

Default Docker has **no** PyTorch. Optional AdvProtect is a separate stack at the end of this file. It is **not** on the Protect page.

## Install

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS) with the engine running, or Docker Engine on Linux.

```bash
git clone https://github.com/Jingwei-Protect/jingwei-selfhost.git
cd jingwei-selfhost
docker compose up --build
```

The first build pulls base images and compiles the frontend. Open **http://127.0.0.1:8080**. Leave the terminal open; `Ctrl+C` stops the stack.

Processing is CPU-heavy. Large files on a laptop are slow. Long edges above 2560px are resized before upload. If port 8080 is taken, stop the other program or change the mapping in `compose.yaml`.

## How to protect a file

1. Open http://127.0.0.1:8080/protect and upload your work (PNG, JPEG, or WebP).
2. Enter the **creator name** you want on the claim (required when JW is on).
3. Pick a **base mode** (below). Generate a preview on the right. Drag placement boxes, use the eraser or brush if you need to spare a face or logo, then **Start protection**.
4. Download PNG (lossless, needed for LSB) or JPEG. Keep your original; the server deletes the upload after processing.

### Base modes

**Credit · Quick** — Everyday publish. Filling the creator name writes a verifiable invisible JW declaration. The on-image mark is **Auto** (flat art → faint character grid; textured photos → displacement), or you force **Faint characters** or **Displacement**. An optional logo is only a small faint stamp. Extra visible layers sit under **More options**.

**Manual** — You turn each invisible and visible layer on and set every parameter. Independent of Credit · Quick. Logo size, position, and strength are yours to set.

**Ultimate · Color** / **Ultimate · Grayscale** — Stronger stacked recipes for colour or grey art. Open **Ultimate mode settings** after you pick them. Still preview before you download.

### Credit · Quick examples

Same display size as the matrix pairs below. Samples are documentation only ([SAMPLES-LICENSE.md](SAMPLES-LICENSE.md)).

Textured art (fur, petals) → Auto usually picks **displacement**: the name is written by shifting host pixels, not by pasting a colour stamp.

| Before | After Credit · Quick |
|:---:|:---:|
| <img src="frontend/public/showcase/credit/credit-dog-before.png" width="400" alt="Puppy before Credit Quick"> | <img src="frontend/public/showcase/credit/credit-dog-after.png" width="400" alt="Puppy after Credit Quick"> |

Flat illustration → Auto usually picks **faint characters**: a light full-frame speckle and a dotted name. From far away it still reads as the painting.

| Before | After Credit · Quick |
|:---:|:---:|
| <img src="frontend/public/showcase/credit/credit-cat-before.png" width="400" alt="Cat before Credit Quick"> | <img src="frontend/public/showcase/credit/credit-cat-after.png" width="400" alt="Cat after Credit Quick"> |

### Invisible and tracking layers

These do not show as a stamp. Check them on **Verify**. Strength below is a lab summary, not a promise.

| Layer | On the picture | After typical AI wash / re-save | Verify |
|-------|----------------|----------------------------------|--------|
| **JW Declaration** | Invisible. Verify reads the footer strip and claim fields (creator, restrictions, optional timestamp). | Light compression and screenshots often keep it; a full AI repaint may wipe it. | Medium–strong |
| **DWT** | Invisible frequency payload (letters, digits, symbols, max 24 characters). Separate from JW. | Local repaint may weaken it; heavy repaint may erase it. Survives JPEG better than LSB. | Medium |
| **LSB** | Invisible bits. **PNG original only.** | JPEG re-save and screenshots usually break it. | Weak–medium |
| **Tracking anchors** | Four very faint corner anchors. After a screenshot, Verify can still try a short author + year-month code if you type the **same signature** you used at protect time. Short edge under 512px cannot embed. | Full repaint may fail; a crop may still match. | Medium |

Copyright **EXIF/IPTC** metadata is optional and often stripped by social platforms. Enable it if you hand files directly.

### Visible layers (from the in-app matrix)

Visible layers raise the cost of theft and wash-out. They are **not** a substitute for JW/DWT when you need to prove a claim. A common stack is **displacement or halftone + JW + DWT**. Portraits can add a blur bar or face-emboss lock.

Left column: after Jingwei. Right column: after an AI watermark-removal / local-repair attempt. Red boxes on the right are from the user guide: smears, blocks, leftover marks, or broken structure.

Pairs match http://127.0.0.1:8080/guide/watermark-matrix (use the slider there). **Moire** and **face-emboss lock** have no matrix stills yet — preview those on Protect.

All pictures below are shown at the **same width**.

#### Displacement · tiled repeat

Pixels under the repeated name are shifted, colour kept. When an editor tries to erase the text, the warped structure is hard to restore cleanly.

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/disp-repeat-protected.png" width="400" alt="Displacement tiled repeat — protected"> | <img src="frontend/public/showcase/guide/disp-repeat-ai-restored.png" width="400" alt="Displacement tiled repeat — after AI repair"> |

#### Displacement · scattered characters

Marks are spread apart so a local inpaint cannot line up with the original texture.

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/disp-scatter-protected.png" width="400" alt="Displacement scatter — protected"> | <img src="frontend/public/showcase/guide/disp-scatter-ai-restored.png" width="400" alt="Displacement scatter — after AI repair"> |

#### Displacement · grouped word

One (or a few) concentrated word plates. On Protect, in centered-words mode you can drag boxes on the preview.

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/disp-tile-protected.png" width="400" alt="Displacement grouped word — protected"> | <img src="frontend/public/showcase/guide/disp-tile-ai-restored.png" width="400" alt="Displacement grouped word — after AI repair"> |

#### Tiled text overlay

Repeated readable text on top of the image. More obvious than displacement; higher visual cost, higher theft friction.

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/text-tile-protected.png" width="400" alt="Tiled text — protected"> | <img src="frontend/public/showcase/guide/text-tile-ai-restored.png" width="400" alt="Tiled text — after AI repair"> |

#### Emboss texture

A light full-frame bevel / hatch. Poor fit for very flat colour fields; useful when you want local repair to look wrong.

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/emboss-protected.png" width="400" alt="Emboss texture — protected"> | <img src="frontend/public/showcase/guide/emboss-ai-restored.png" width="400" alt="Emboss texture — after AI repair"> |

#### Blur bar

Horizontal translucent bands. Typical uses: faces, delivery previews, covering a line of text. On Protect you get dashed boxes to drag (up to five).

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/ascii-protected.png" width="400" alt="Blur bar — protected"> | <img src="frontend/public/showcase/guide/ascii-ai-restored.png" width="400" alt="Blur bar — after AI repair"> |

#### Blur block

Brush-painted patches. Not the same layer as a blur bar. Paint on the right preview, undo mistakes, then generate preview.

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/dots-protected.png" width="400" alt="Blur block — protected"> | <img src="frontend/public/showcase/guide/dots-ai-restored.png" width="400" alt="Blur block — after AI repair"> |

#### ASCII characters

A faint full-frame character grid (and an optional signature). Distinct from displacement.

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/moire-protected.png" width="400" alt="ASCII watermark — protected"> | <img src="frontend/public/showcase/guide/moire-ai-restored.png" width="400" alt="ASCII watermark — after AI repair"> |

#### Halftone dots

Fine dots in high-frequency areas. Flattening in an editor often leaves unnatural patches.

| After Jingwei protection | After AI repair attempt |
|:---:|:---:|
| <img src="frontend/public/showcase/guide/halftone-protected.png" width="400" alt="Halftone dots — protected"> | <img src="frontend/public/showcase/guide/halftone-ai-restored.png" width="400" alt="Halftone dots — after AI repair"> |

**Also on Protect (preview there):** face-emboss lock on portraits; jumping moire; optional displacement **logo** (silhouette shifts host pixels; it is not a pasted colour plate).

## How to verify

1. Open http://127.0.0.1:8080/verify and upload the **protected file you downloaded** (for LSB, the PNG, not a screenshot).
2. Detection starts on upload. Panels cover C2PA (if present), JW, tracking anchors, DWT, LSB, and EXIF/IPTC.
3. For tracking after a screenshot, type the **same signature** used at protect time (creator name / DWT / LSB / emboss / ASCII signature). Case and spaces are ignored; the exact words must match.

Visible layers will not appear as “verified claims.” They are meant to be seen on the picture.

## License

- **Code:** [MIT](LICENSE) © 精卫 Jingwei
- **Sample images** (credit photos and matrix pairs): **not MIT.** [SAMPLES-LICENSE.md](SAMPLES-LICENSE.md). Documentation only — not stock, merch, portfolio, or training data.

Matrix stills come from 2026 guide material and internal tests. Editors change. Preview and verify **your** files. Do not treat red boxes as a score against a named product.

## Optional AdvProtect

Not on the Protect page. Default image has **no** PyTorch.

We ran **multiple rounds** of tests against Doubao and similar closed-source editors. Success is **low**; protection is often invisible. Experimental; may help some open diffusion pipelines; **not a promise against Doubao or Jimeng.**

Same port **8080** — stop the default stack first:

```bash
docker compose down
docker compose -f compose.yaml -f compose.adv.yaml up --build
```

Nav shows AdvProtect only when the flag is on. [docs/adv-protect-local.md](docs/adv-protect-local.md).
