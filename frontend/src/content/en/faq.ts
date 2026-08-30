/** FAQ - single source for /faq SEO page + FAQPage JSON-LD */

import { CONTACT_EMAIL, SITE_NAME, SITE_URL } from '../../lib/site'

export const FAQ_META_TITLE = `FAQ | ${SITE_NAME} · Anti-AI Wash-out · Traceable Watermark`

export const FAQ_META_DESCRIPTION =
  'What is Jingwei? How does it differ from Glaze and Nightshade? Does it store your images? Can screenshots still verify? What is Quick Credit? Can you reuse the cat and dog samples? Updated August 2026.'

export const FAQ_DATE_MODIFIED = '2026-08-30'

export const FAQ_INTRO = {
  title: 'Frequently Asked Questions',
  lead: `${SITE_NAME} protects image attribution for illustrators, photographers, and designers. Before you post or deliver, open jwprotect.com/protect and write a JW declaration plus optional visible anti-theft layers. One image takes about 30 seconds. No deep-learning models. Files leave the server after processing. The questions below match how people actually search.`,
  updated: '30 August 2026',
}

export type FaqAnswerBlock =
  | string
  | { type: 'list'; items: string[] }

export interface FaqItem {
  id: string
  question: string
  answer: FaqAnswerBlock[]
  relatedLinks?: readonly { to: string; label: string }[]
}

export interface FaqCategory {
  id: string
  title: string
  items: FaqItem[]
}

export function faqPlainAnswer(blocks: FaqAnswerBlock[]): string {
  return blocks
    .map(b => {
      if (typeof b === 'string') return b
      return b.items.map(i => `- ${i}`).join('\n')
    })
    .join('\n')
}

export const FAQ_CATEGORIES: FaqCategory[] = [
  {
    id: 'what',
    title: 'What Jingwei Is',
    items: [
      {
        id: 'what-is-jingwei',
        question: 'What is Jingwei, and how do I protect an image?',
        answer: [
          `${SITE_NAME} is an image attribution tool for individual creators. You upload PNG, JPEG, or WebP at jwprotect.com, write a verifiable JW declaration, and can add visible anti-theft layers. One image takes about 30 seconds. You do not need an account.`,
          'Protect defaults to Quick Credit. Switch to Manual to toggle displacement, emboss, blur bars, and other layers yourself. Verify by uploading the PNG you just downloaded.',
        ],
        relatedLinks: [
          { to: '/protect', label: 'Open Protect' },
          { to: '/protocol', label: 'Read the JW Declaration' },
        ],
      },
      {
        id: 'why-jingwei-vs-glaze-nightshade',
        question: 'How is Jingwei different from Glaze and Nightshade?',
        answer: [
          'Glaze and Nightshade mainly target bulk scraping for AI training after you post online. Jingwei mainly targets someone who already has your file and runs AI edit, fusion, or local redraw on it. You can use all three.',
          {
            type: 'list',
            items: [
              'Glaze / Nightshade: local apps, often a strong GPU, slower per image, more visible perturbation',
              'Jingwei: browser, classical image processing, no deep-learning model files',
              'Shared limit: none of them can promise every future tool will fail. Keep your originals',
            ],
          },
        ],
        relatedLinks: [{ to: '/protect', label: 'Protect Your Work' }],
      },
      {
        id: 'no-retain-no-ai',
        question: 'Does Jingwei store my images or process them with AI?',
        answer: [
          'No long-term storage, and no AI processing. Images uploaded for Protect, Verify, or AI Inspect Assist are deleted from the server as soon as processing finishes. We do not keep an artwork library and we do not train on uploads or sell analytics on them.',
          'Embedding uses classical image processing and digital signal processing. No deep learning. No .pth, .onnx, or .ckpt files. See the privacy policy.',
        ],
        relatedLinks: [
          { to: '/privacy', label: 'Privacy Policy' },
          { to: '/terms', label: 'Terms of Service' },
        ],
      },
    ],
  },
  {
    id: 'effect',
    title: 'Effectiveness and Limits',
    items: [
      {
        id: 'ai-fusion-limits',
        question: 'Does a watermark permanently stop AI fusion and training?',
        answer: [
          'No. Heavy compression, repeated re-saves, and targeted removal can weaken or wipe invisible layers. Visible layers raise the cost of a clean restore. They do not guarantee every future tool will fail.',
          'The JW declaration aims to become a machine-readable intent mark, similar to Creative Commons, so platforms can recognize it. That is a long project. It does not replace the law.',
        ],
        relatedLinks: [{ to: '/protocol', label: 'Learn About JW' }],
      },
      {
        id: 'anti-ai-edit',
        question: 'Can Jingwei stop AI editing and image fusion?',
        answer: [
          'Jingwei targets the case where someone already has your file and runs AI edit or fusion on it. Layered perturbation and visible anti-theft overlays make a clean restore harder and dirtier, which raises abuse cost.',
          'Results vary with the source image, the toolchain, and post-processing. Side-by-side tests from August 2026 are on the watermark matrix page.',
        ],
        relatedLinks: [
          { to: '/protect', label: 'Choose Protection Options' },
          { to: '/guide/watermark-matrix', label: 'Open the test matrix' },
        ],
      },
      {
        id: 'quality-formats',
        question: 'Which formats does Jingwei support, and will quality drop?',
        answer: [
          'Upload accepts PNG, JPEG, and WebP. If you enable JW or other invisible frequency layers, export PNG. Lossy JPEG compression weakens invisible signals.',
          'JW, DWT, and LSB try to stay quiet in normal viewing. Stronger settings can add faint texture. Displacement, emboss, and blur bars change the picture on purpose. EXIF and C2PA usually do not change how the image looks. Preview at medium or light first.',
        ],
      },
    ],
  },
  {
    id: 'verify',
    title: 'Verification and Tracking',
    items: [
      {
        id: 'screenshot-verify',
        question: 'Can I still verify screenshots or files re-downloaded from social apps?',
        answer: [
          'Sometimes. JW declarations and tracking layers include redundancy for screenshots, social compression, and secondary saves. A common path: protect, screenshot, post, re-download, then verify.',
          'Attribution often still reads, but not every time. Verify reports confidence per layer for JW, DWT, LSB, and anchors. For disputes, keep the original export that never left your machine.',
        ],
        relatedLinks: [{ to: '/verify', label: 'Open Verify' }],
      },
      {
        id: 'how-to-verify',
        question: 'How do I check whether an image has Jingwei watermark data?',
        answer: [
          'Open jwprotect.com/verify and upload the file. No login. The system checks JW declaration data, DWT, LSB, EXIF/IPTC, and C2PA, then reports detection and confidence by layer.',
          'A miss does not prove the file was never processed. A hit can support that Jingwei protected it or that related metadata is present. Upload the PNG still. Do not upload a Holo-card video frame.',
        ],
        relatedLinks: [{ to: '/verify', label: 'Go to Verify' }],
      },
      {
        id: 'source-inspection',
        question: 'Can AI Inspect Assist tell me if an image was drawn by AI?',
        answer: [
          'It does not give a final verdict. AI Inspect Assist prints an ingredient list: AI-tool metadata, camera EXIF, C2PA credentials, and similar traces. You judge from that list.',
          'Social downloads and screenshots often strip those traces. "Not found" does not mean "a human drew this."',
        ],
        relatedLinks: [{ to: '/inspect', label: 'AI Inspect Assist (Beta)' }],
      },
    ],
  },
  {
    id: 'usage',
    title: 'Usage and Settings',
    items: [
      {
        id: 'quick-credit',
        question: 'What is Quick Credit, and how should I use it for daily posts?',
        answer: [
          'Quick Credit is the default Protect mode. After you enter a creator name, Jingwei writes a verifiable invisible JW claim and picks a faint character field or a light displacement signature. A logo becomes one faint stamp. Everyday posting takes about 30 seconds. No signup.',
          'Quick Credit and Manual do not share sliders. Switch to Manual to toggle every layer, place a logo, or stack tiled displacement, emboss, or face lock. Verify with the PNG you just downloaded.',
        ],
        relatedLinks: [
          { to: '/protect', label: 'Open Protect' },
          { to: '/blog/quick-credit-mode', label: 'Quick Credit guide' },
        ],
      },
      {
        id: 'holo-card',
        question: 'What is a Holo card? Can I verify with the video?',
        answer: [
          'A Holo card frames the protected still as a reflective foil card and exports an about-6-second MP4 for social or client previews. Rainbow and grain show only inside the shine band.',
          'Do not verify with the clip. Upload the PNG still. Hovering the on-site sample previews the foil without exporting.',
        ],
        relatedLinks: [
          { to: '/protect', label: 'Protect and download a Holo card' },
          { to: '/blog/jingwei-holo-card', label: 'Holo card explainer' },
        ],
      },
      {
        id: 'watermark-font',
        question: 'Can I change the watermark font?',
        answer: [
          'Only open-license fonts ship today. You cannot pick another family yet. You can still change size, position, and visible-layer styles. If more fonts land, Protect and this FAQ will say so.',
        ],
      },
      {
        id: 'jw-declaration',
        question: 'What is the JW declaration? Do I have to turn it on?',
        answer: [
          'JW (Jingwei Protocol) writes creation type (Original / AI-Assisted), usage limits (for example no unauthorized AI training or AI editing), and the creator name into the image in machine-readable form. An optional visible badge can show.',
          'We want JW, like CC markers, to become a public signal platforms can read. That needs ecosystem agreement. It is optional. Export PNG if you want invisible layers to survive.',
        ],
        relatedLinks: [{ to: '/protocol', label: 'Read Full JW Declaration' }],
      },
      {
        id: 'delivery-feature',
        question: 'What does Commission Delivery do?',
        answer: [
          'You upload the final, set a viewing password, and get an encrypted delivery package. The client opens it on this site, enters the password, and holds mouse or touch to reveal the image. Release and it scatters again.',
          'A slow-moving watermark shows viewer identity, which makes a clean high-resolution screenshot harder. Touch works on phones. Complex steps are still easier on a computer.',
        ],
        relatedLinks: [{ to: '/delivery', label: 'Commission Delivery' }],
      },
      {
        id: 'sample-images-license',
        question: 'Can I use the cat, dog, or matrix sample photos as my own art?',
        answer: [
          'No. Those files exist to explain protection. Code is MIT. Sample images stay copyrighted by their authors and Jingwei. Do not use them as covers, stock, training data, or a base for new work.',
          'A Save As click cannot be blocked. The license blocks the claim that MIT lets you take the photos commercially. Test Protect on your own files.',
        ],
        relatedLinks: [
          { to: '/guide/watermark-matrix', label: 'Open the test matrix' },
          { to: '/protect', label: 'Protect your own file' },
        ],
      },
    ],
  },
  {
    id: 'roadmap',
    title: 'Product Roadmap',
    items: [
      {
        id: 'open-source-and-app',
        question: 'Is Jingwei open source? Will there be a mobile app?',
        answer: [
          'The product website repository is not public yet. After Protect and Verify stabilize, the plan is a self-host package (Docker first) that the community can review. Community, donations, and Commission Delivery stay on the product site.',
          'A mobile app needs a new interaction design and app-store review. There is no app plan now. The web product comes first.',
        ],
      },
    ],
  },
]

export const FAQ_ALL_ITEMS: FaqItem[] = FAQ_CATEGORIES.flatMap(c => c.items)

export function buildFaqJsonLd(): Record<string, unknown> {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    url: FAQ_CANONICAL,
    dateModified: FAQ_DATE_MODIFIED,
    mainEntity: FAQ_ALL_ITEMS.map(item => ({
      '@type': 'Question',
      name: item.question,
      acceptedAnswer: {
        '@type': 'Answer',
        text: faqPlainAnswer(item.answer),
      },
    })),
  }
}

export const FAQ_CTA = {
  title: 'Still Have Questions?',
  body: `Leave a note on the feedback page or write ${CONTACT_EMAIL}. Protect a work on Protect. Check a file on Verify.`,
  links: [
    { to: '/protect', label: 'Start Protecting' },
    { to: '/verify', label: 'Verify Watermarks' },
    { to: '/about', label: "Read the Author's Note" },
    { to: '/protocol', label: 'Read the JW Declaration' },
    { to: '/feedback?from=faq', label: 'Send Feedback' },
  ] as const,
}

export const FAQ_CANONICAL = `${SITE_URL}/faq`
