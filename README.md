# Jingwei self-host

**English first.** Chinese install: [README_zh.md](README_zh.md).

Run **Protect** and **Verify** on your own computer. Uploaded images stay local; they are not sent to [jwprotect.com](https://jwprotect.com). That site is the maintained product (community, billing, latest UX). This repository is **not** the official website.

## What you get

| Page | What it does |
|------|----------------|
| **Protect** | Embeds attribution and anti-wash layers into your image, then you download the result. No account. |
| **Verify** | Reads those layers back so you can check a file you already protected. |

Default Docker has **no** PyTorch. Optional adversarial protection is a separate stack (see the last section). It is **not** on the Protect page.

## Quick start

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows / macOS) with the engine running, or Docker Engine on Linux.

```bash
git clone https://github.com/Jingwei-Protect/jingwei-selfhost.git
cd jingwei-selfhost
docker compose up --build
```

First build downloads base images and compiles the frontend; later starts are faster.

Open **http://127.0.0.1:8080** — Protect and Verify, no login.

Processing is CPU-heavy. A large file on a laptop can take a while. Leave this terminal open while you use the app; `Ctrl+C` stops it.

If port 8080 is already in use, stop the other program or change the port mapping in `compose.yaml`.

## What it looks like

These are **documentation samples** (not MIT). Do not use them as your own art. License: [SAMPLES-LICENSE.md](SAMPLES-LICENSE.md).

### Puppy — textured art, Quick Credit

Fur and petals count as texture, so Protect nudges host pixels into the name instead of pasting a color stamp.

<p>
<img src="frontend/public/showcase/credit/credit-dog-before.png" width="280" alt="Puppy before protection">
<img src="frontend/public/showcase/credit/credit-dog-after.png" width="280" alt="Puppy after protection">
</p>

<p><img src="frontend/public/showcase/credit/credit-dog-where.png" width="200" alt="Where the credit mark sits on the puppy"></p>

### Cat — flat illustration, Quick Credit

Flat color fields get a light full-frame speckle and a faint dotted name. From far away it still reads as the painting.

<p>
<img src="frontend/public/showcase/credit/credit-cat-before.png" width="280" alt="Cat before protection">
<img src="frontend/public/showcase/credit/credit-cat-after.png" width="280" alt="Cat after protection">
</p>

<p><img src="frontend/public/showcase/credit/credit-cat-where.png" width="200" alt="Where the credit mark sits on the cat"></p>

After compose is up, more protected vs AI-repair pairs: http://127.0.0.1:8080/guide/watermark-matrix (files under `frontend/public/showcase/guide/`).

## License

- **Code:** [MIT](LICENSE) © 精卫 Jingwei
- **Sample images:** **not MIT.** See [SAMPLES-LICENSE.md](SAMPLES-LICENSE.md). Documentation only — not stock, merch, portfolio, or training data.

## Optional AdvProtect

Not on the Protect page. Default image has **no** PyTorch.

We ran **multiple rounds** of tests against Doubao and similar closed-source editors. Success is **low**; protection is often invisible. Experimental; may help some open diffusion pipelines; **not a promise against Doubao or Jimeng.**

Same port **8080** — stop the default stack first:

```bash
docker compose down
docker compose -f compose.yaml -f compose.adv.yaml up --build
```

The nav link appears only when the flag is on. Details: [docs/adv-protect-local.md](docs/adv-protect-local.md).
