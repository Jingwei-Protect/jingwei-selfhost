import { SITE_URL } from '../../../lib/site'
import type { BlogIndexCopy, BlogPost } from '../types'

const G = '/showcase/guide'
const L_PROTECTED = 'After Jingwei protection'
const L_AI = 'After AI repair attempt'

export const BLOG_CANONICAL = `${SITE_URL}/blog`

export const BLOG_INDEX: BlogIndexCopy = {
  canonical: BLOG_CANONICAL,
  metaTitle: 'Blog · Anti-AI wash-out & attribution | Jingwei',
  metaDescription:
    'Why do old watermarks fail? How to choose visible layers? Full reads for illustrators, designers, and photographers—with test matrix and user guide.',
  title: 'Blog',
  lead: 'How Quick Credit works, how to download a Holo clip, plus the layer guide and test matrix.',
}

const C = '/showcase/credit'
const H = '/showcase/holo'

export const BLOG_POSTS: BlogPost[] = [
  {
    slug: 'quick-credit-mode',
    datePublished: '2026-08-29',
    dateModified: '2026-08-29',
    metaTitle: 'What is Quick Credit? Watermark a file in 30 seconds | Jingwei Blog',
    metaDescription:
      'Jingwei’s default Quick Credit mode writes a verifiable JW claim from your name and auto-picks a faint mark. About 30 seconds, no signup.',
    intro: {
      kicker: 'How to use',
      title: 'What is Quick Credit? A verifiable ID for your image in 30 seconds',
      lead:
        'Quick Credit is Jingwei’s default Protect mode (jwprotect.com): you type a creator name, and the tool writes a machine-readable JW claim plus a faint on-image mark. Everyday posting takes about 30 seconds, no account, files deleted after processing.',
      updated: 'August 2026',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${C}/credit-dog-before.png?v=upload1`,
      aiRestoredSrc: `${C}/credit-dog-after.png?v=upload1`,
      protectedAlt: 'Puppy illustration before watermark',
      aiRestoredAlt: 'Puppy after Quick Credit displacement',
      protectedLabel: 'Original',
      aiRestoredLabel: 'Quick Credit · displacement',
      caption: 'Textured pictures get a light displacement signature. The full frames look almost identical (about 1% of pixels change). Scroll to the face crop: Jingwei sits across the muzzle.',
    },
    paragraphs: [
      'Searches like “free watermark” or “stop AI from removing my watermark” usually fail on friction, not theory. Quick Credit is the short path: write the ID first, keep the picture clean enough to post.',
    ],
    sections: [
      {
        heading: 'What is Quick Credit mode?',
        paragraphs: [
          'Quick Credit is the default mode on Jingwei’s Protect page. After you enter a creator name, Jingwei turns on the JW declaration: name, creation type, and usage limits written in a machine-readable form. It also adds a very light visible mark so people can tell the file was protected, without a corner logo that inpainting tools treat as a separate object.',
        ],
      },
      {
        heading: 'How is it different from Manual mode?',
        paragraphs: [
          'Quick Credit and Manual do not share sliders. Quick Credit is not “Manual with the knobs hidden.”',
          'Quick Credit: entering a name writes JW. The visible mark is a fixed faint recipe — faint characters or light displacement, chosen from the picture (or forced by you). A logo becomes one faint stamp. There are no toggles for tiled displacement, emboss, blur bars, or face lock, and you cannot place or darken a logo by hand. The point is a ~30-second post, with a clean picture.',
          'Manual: every layer on or off, every slider yours. Put a logo in a chosen corner, tile displacement, stack emboss or face lock against the test matrix — that is Manual. The faint characters / displacement you see in Quick Credit are not the Manual strength sliders.',
        ],
      },
      {
        heading: 'How do I use it? Three steps',
        paragraphs: [
          'Open Protect, leave Quick Credit selected, upload PNG / JPEG / WebP (export iPhone photos to JPG first). Type the creator name; optionally add on-image text or a logo. Click Start protect and download the PNG. About 30 seconds. No AI models touch the upload; the server deletes it afterward.',
        ],
      },
      {
        heading: 'Displacement example: the textured puppy',
        paragraphs: [
          'Auto sees fur and petals as texture, so it usually applies light displacement (about 7% font, 3 px shift, soft shadow — the c024 test rung). The letters are not a pasted color block: host pixels are nudged into “Jingwei”. The red box marks where that mark sits across the puppy’s face.',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-dog-face-before.png?v=upload1`,
            aiRestoredSrc: `${C}/credit-dog-face-after.png?v=upload1`,
            protectedAlt: 'Clean puppy face crop, fur not displaced',
            aiRestoredAlt: 'c024 face crop, fur nudged into Jingwei',
            protectedLabel: 'Original · face crop',
            aiRestoredLabel: 'c024 · face crop',
            caption: 'This is the test-dog signature: not a stamp on the blue flower. Host pixels on the face are nudged into Jingwei.',
          },
          {
            kind: 'single',
            src: `${C}/credit-dog-where.png?v=upload1`,
            alt: 'Puppy displacement locator: red box on Jingwei across the face',
            caption: 'Locator: the red box is where the mark sits on the face.',
          },
        ],
      },
      {
        heading: 'Faint-character example: the flat cat',
        paragraphs: [
          'Flat illustration and large color fields take the other path: a very light full-frame speckle/character layer, plus one dotted signature in the middle. This is the real Protect faint-character output, not the Manual contrast sliders.',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-cat-before.png?v=siga1`,
            aiRestoredSrc: `${C}/credit-cat-after.png?v=siga1`,
            protectedAlt: 'Cat illustration original',
            aiRestoredAlt: 'Cat after real faint-character protect',
            protectedLabel: 'Original (flat art)',
            aiRestoredLabel: 'After faint characters',
            caption: 'From far away it still reads as the painting. The faint mark covers the frame and does not steal the cat or the shark.',
          },
          {
            kind: 'compare',
            protectedSrc: `${C}/credit-cat-zoom-before.png?v=siga1`,
            aiRestoredSrc: `${C}/credit-cat-zoom-after.png?v=siga1`,
            protectedAlt: 'Cat face crop of the original, no faint characters',
            aiRestoredAlt: 'Cat face crop after protect, tiny crosses and dots visible',
            protectedLabel: 'Original · face crop',
            aiRestoredLabel: 'Protected · face crop',
            caption: 'This is the real faint recipe: zoom and you get tiny crosses and dots, not a loud letter sheet.',
          },
          {
            kind: 'single',
            src: `${C}/credit-cat-where.png?v=siga1`,
            alt: 'Cat locator: red box on the dotted Jingwei on the face',
            caption: 'Locator: the red box is the dotted signature. The rest of the frame has an even fainter speckle.',
          },
        ],
      },
      {
        heading: 'How do I verify the file afterward?',
        paragraphs: [
          'Upload the PNG you just downloaded on the Verify page. No login. Jingwei reports JW, frequency-domain, LSB, metadata, and tracking anchors separately. “Not found” does not prove the file was never processed. “Found” is supporting evidence that Jingwei touched it. Keep the uncompressed export if a dispute starts.',
        ],
      },
      {
        heading: 'When should I not stop at Quick Credit?',
        paragraphs: [
          'If you need to raise the cost of targeted wipe, face swap, or inpainting, switch to Manual and add tiled displacement, emboss, blur bars, or face lock — then use the test matrix. Quick Credit optimizes for “verifiable and not ugly,” not maximum anti-wash strength.',
          'Export PNG when you can. JPEG can weaken invisible layers. Do not flatten transparency to JPEG.',
        ],
      },
    ],
    relatedLinks: [
      { to: '/protect', label: 'Open Protect and try Quick Credit' },
      { to: '/verify', label: 'Verify the file you just downloaded' },
      { to: '/blog/jingwei-holo-card', label: 'What is a Holo card?' },
      { to: '/blog/how-to-use-jingwei-visible-layers', label: 'How to pick visible layers' },
    ],
  },
  {
    slug: 'jingwei-holo-card',
    datePublished: '2026-08-29',
    dateModified: '2026-08-29',
    metaTitle: 'What is a Jingwei Holo card? Download the foil clip | Jingwei Blog',
    metaDescription:
      'A Jingwei Holo card turns a protected still into a reflective foil card and a ~6s MP4. Fingerprint moiré appears only inside the shine band.',
    intro: {
      kicker: 'New',
      title: 'What is a Holo card? Turn a protected still into a foil clip',
      lead:
        'A Holo card is Jingwei’s display layer: the protected still is framed as a tilting foil card and exported as an about-6-second, 8 fps MP4. Use it for social teasers and commission showcases. It is not an iPhone Live Photo, and it is not the file you should upload to Verify.',
      updated: 'August 2026',
    },
    heroMedia: {
      kind: 'holo',
      cardSrc: `${H}/home-card.jpg?v=credit-faint-2`,
      videoSrc: `${H}/holo-card-demo.mp4`,
      alt: 'Finished Jingwei Holo card: hover for foil, clip below',
      caption: 'Same frame for both: the hoverable card above, the ~6-second MP4 below.',
    },
    paragraphs: [
      'After protect finishes, click Download Holo card. The filename follows your original, e.g. `cat_holo.mp4`. What people see is a card that moves, not a flat preview JPEG.',
    ],
    sections: [
      {
        heading: 'What is a Holo card versus a watermarked PNG?',
        paragraphs: [
          'The Holo card is presentation, not a new watermark algorithm. JW and the visible mark are already in the still. The clip only wraps that still in foil: a rainbow sweep, same-direction dense moiré, and sparse sparkle. Off-angle you see the clear picture; the foil does not recolor the whole painting.',
        ],
      },
      {
        heading: 'How do I download a Holo card?',
        paragraphs: [
          'Finish Protect (Quick Credit or Manual) and save the PNG. In the result panel, click Download Holo card and wait for capture (Chrome is required on a self-hosted box). You get an about-6-second MP4 for Weibo, Xiaohongshu, X, or Discord. Hovering the on-site sample also previews the foil without exporting.',
        ],
      },
      {
        heading: 'What is actually on the foil?',
        paragraphs: [
          'Three things live inside the shine band: a cyan–gold–pink sweep; same-direction sub-pixel gratings that beat into fingerprint ridges; and sparse glitter dots. A mask keeps grain inside the band. The rim is silver, not charcoal. Watch the finished card and clip — there are no still breakdowns on this page.',
        ],
      },
      {
        heading: 'Where should I post it — and what must I not use it for?',
        paragraphs: [
          'Good as a teaser, a portfolio card, or a commission showcase. Bad as your only archive: Verify wants the PNG, not a video screenshot. Re-encoding on social apps will soften the foil; that is compression, not a failed protect.',
        ],
      },
    ],
    relatedLinks: [
      { to: '/protect', label: 'Protect a file and download a Holo card' },
      { to: '/blog/quick-credit-mode', label: 'Read Quick Credit first' },
      { to: '/guide/watermark-matrix', label: 'Visible layers vs AI wash-out' },
    ],
  },
  {
    slug: 'why-ai-image-theft-is-easy',
    datePublished: '2026-07-05',
    dateModified: '2026-07-06',
    metaTitle: 'How to make your watermark survive AI wash-out | Jingwei Blog',
    metaDescription:
      'Why corner logos fail against AI. What inpainting does. How Jingwei visible and invisible layers work together, with guide test pairs.',
    intro: {
      kicker: 'For creators',
      title: 'How to make your watermark survive AI wash-out',
      lead: '',
      updated: 'July 2026',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${G}/disp-repeat-protected.png`,
      aiRestoredSrc: `${G}/disp-repeat-ai-restored.png`,
      protectedAlt: 'Tile-repeat displacement after Jingwei protection',
      aiRestoredAlt: 'Tile-repeat displacement after AI repair attempt',
      protectedLabel: L_PROTECTED,
      aiRestoredLabel: L_AI,
      caption: 'Tile-repeat displacement: red boxes mark smears and blocks after AI tries to erase the signature.',
    },
    paragraphs: [
      'Many creators have been there: you added a watermark, but someone stripped it and reused the work. In the past that meant hours in Photoshop, channels, masks, and a real learning curve. Now drop the image into an AI tool and one prompt can remove and refill in seconds.',
      'The issue is not whether you watermarked, but whether the watermark still follows old rules: pasted on, regular, sharp, separate from the image. AI wash-out exploits exactly that.',
    ],
    sections: [
      {
        heading: 'Why old watermarks fail',
        paragraphs: [
          'Too regular: corner logos, copyright bars, repeated small marks at fixed positions. AI has seen millions of these and can batch-detect and batch-remove them.',
          'Too sharp and separate: watermarks meant to be visible sit apart from the content. AI treats them as foreign objects, inpaints the hole, and moves on.',
          'Too little pixel information: a few letters or a small icon. After removal, AI fills from surrounding texture and color trends and the gap looks natural.',
        ],
      },
      {
        heading: 'Wash-out is AI "repairing" your work',
        paragraphs: [
          'The core is inpainting: mask unwanted regions, regenerate from context. Common moves include local logo removal, full-image touch-up on tiled marks, and crop-then-outpaint on edge watermarks.',
          'The hero image above is a tile-repeat displacement test: protected on the left, AI repair on the right. Red boxes are not a perfect restore—they are the failures that remain.',
        ],
      },
      {
        heading: 'Jingwei: two layers',
        paragraphs: [
          'Visible anti-theft layers micro-perturb pixels so changes merge with structure. Forced AI cleanup often warps, blurs, or leaves noise. Emboss, blur bars, face emboss lock, and more are on the test matrix; layer choice is in the next post.',
          'Invisible JW declarations and frequency watermarks stay verifiable after compression or screenshots. Use visible layers when you fear clean theft; use JW + DWT when you fear proving ownership.',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/emboss-protected.png`,
            aiRestoredSrc: `${G}/emboss-ai-restored.png`,
            protectedAlt: 'Emboss texture after protection',
            aiRestoredAlt: 'Emboss after AI repair',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'Emboss texture: subtle diagonal lines; flattening often leaves repair artifacts.',
          },
        ],
      },
    ],
    relatedLinks: [
      { to: '/guide/watermark-matrix', label: 'Test matrix' },
      { to: '/blog/how-to-use-jingwei-visible-layers', label: 'Choose visible layers' },
      { to: '/protect', label: 'Protect a work' },
    ],
  },
  {
    slug: 'how-to-use-jingwei-visible-layers',
    datePublished: '2026-07-05',
    dateModified: '2026-08-28',
    metaTitle: 'How to use Jingwei: choosing visible layers | Jingwei Blog',
    metaDescription:
      'Displacement, halftone, emboss, blur bar, face emboss lock: usage, scenes, stacking with JW invisible layers, and guide test pairs.',
    intro: {
      kicker: 'User guide',
      title: 'How to use Jingwei: choosing visible layers',
      lead:
        'Do not rely on corner logos alone. Jingwei is usually two layers: visible anti-theft plus invisible attribution. Each effect below has a guide test pair.',
      updated: 'July 2026',
    },
    heroMedia: {
      kind: 'compare',
      protectedSrc: `${G}/disp-tile-protected.png`,
      aiRestoredSrc: `${G}/disp-tile-ai-restored.png`,
      protectedAlt: 'Grouped-word displacement after protection',
      aiRestoredAlt: 'Grouped-word displacement after AI repair',
      protectedLabel: L_PROTECTED,
      aiRestoredLabel: L_AI,
      caption: 'Displacement · grouped word',
    },
    paragraphs: [
      'Upload on Protect. Credit · Quick is the default; switch to Manual to set each layer yourself. Drag dashed boxes in preview, generate preview, refine with eraser, export. About half a minute; files deleted after processing.',
    ],
    sections: [
      {
        heading: 'Displacement watermark',
        paragraphs: [
          'Slightly shifts pixels under text so the signature merges with the image. Three layouts: grouped word, random scatter, tile repeat. Place signatures on subject edges or contours.',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/disp-tile-protected.png`,
            aiRestoredSrc: `${G}/disp-tile-ai-restored.png`,
            protectedAlt: 'Grouped-word displacement',
            aiRestoredAlt: 'Grouped word after AI repair',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'Grouped word',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/disp-scatter-protected.png`,
            aiRestoredSrc: `${G}/disp-scatter-ai-restored.png`,
            protectedAlt: 'Random scatter displacement',
            aiRestoredAlt: 'Random scatter after AI repair',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'Random scatter',
          },
        ],
      },
      {
        heading: 'Halftone and ASCII',
        paragraphs: [
          'Halftone embeds fine grains into high frequencies; ASCII covers the frame with character texture. Both look acceptable at normal viewing; AI flattening often leaves blocks or breaks.',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/halftone-protected.png`,
            aiRestoredSrc: `${G}/halftone-ai-restored.png`,
            protectedAlt: 'Halftone after protection',
            aiRestoredAlt: 'Halftone after AI repair',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'Halftone',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/moire-protected.png`,
            aiRestoredSrc: `${G}/moire-ai-restored.png`,
            protectedAlt: 'ASCII visible layer',
            aiRestoredAlt: 'ASCII after AI repair',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'ASCII characters',
          },
        ],
      },
      {
        heading: 'Emboss texture',
        paragraphs: [
          'Light global diagonal lines changing edges and grain. Less suited to flat minimal art; better for illustration, photos, and character art.',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/emboss-protected.png`,
            aiRestoredSrc: `${G}/emboss-ai-restored.png`,
            protectedAlt: 'Emboss after protection',
            aiRestoredAlt: 'Emboss after AI repair',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'Emboss texture',
          },
        ],
      },
      {
        heading: 'Blur bar and blur block',
        paragraphs: [
          'A blur bar is a horizontal translucent band. Use it for delivery previews and to cover key information. The pair below is a blur-bar test.',
          'A blur block is a brush-painted patch. It is not the same layer as a single blur strip. Preview face-emboss lock on Protect in Manual mode.',
        ],
        media: [
          {
            kind: 'compare',
            protectedSrc: `${G}/ascii-protected.png`,
            aiRestoredSrc: `${G}/ascii-ai-restored.png`,
            protectedAlt: 'Blur bar after protection',
            aiRestoredAlt: 'Blur bar after AI repair',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'Blur bar',
          },
          {
            kind: 'compare',
            protectedSrc: `${G}/dots-protected.png`,
            aiRestoredSrc: `${G}/dots-ai-restored.png`,
            protectedAlt: 'Blur block after protection',
            aiRestoredAlt: 'Blur block after AI repair',
            protectedLabel: L_PROTECTED,
            aiRestoredLabel: L_AI,
            caption: 'Blur block',
          },
        ],
      },
      {
        heading: 'How to stack layers',
        paragraphs: [
          'Common: displacement or halftone + JW declaration + frequency watermark. Quiet: invisible layers + tracking anchors.',
          'Full guide pairs are on the test matrix page. The first blog post explains why AI wash-out is easy; this one explains how to pick layers.',
        ],
      },
    ],
    relatedLinks: [
      { to: '/guide/watermark-matrix', label: 'Full test matrix' },
      { to: '/protect', label: 'Open Protect' },
      { to: '/verify', label: 'Verify watermark' },
    ],
  },
]

export function getBlogPost(slug: string): BlogPost | undefined {
  const id = BLOG_SLUG_ALIASES[slug] ?? slug
  return BLOG_POSTS.find(p => p.slug === id)
}

export function postCanonical(slug: string): string {
  return `${SITE_URL}/blog/${slug}`
}

export const BLOG_SLUG_ALIASES: Record<string, string> = {
  'how-jingwei-visible-layers-work': 'how-to-use-jingwei-visible-layers',
}
