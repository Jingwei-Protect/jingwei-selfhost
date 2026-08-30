/** Jingwei Protocol - copy, glossary, story, limits, belief, and letters. */

import { SITE_URL } from '../../lib/site'

export const JW_PROTOCOL_CANONICAL = `${SITE_URL}/protocol`
export const JW_PROTOCOL_META_DESCRIPTION =
  'Jingwei Declaration (JW): machine-readable image attribution and usage intent, frequency-domain invisible watermarking, creation types, NO-TR/NO-ED restrictions, and relation to CC and C2PA.'
export const JW_PROTOCOL_DATE_MODIFIED = '2026-06-14'

// CC symbols and consensus language

export const JW_CC_SYMBOL_HISTORY = {
  kicker: 'Before JW',
  title: 'From Copyright Symbol to CC: How Symbols Changed Creative Use',
  lead: 'Before JW, creators had already used symbols for generations to define how work could be used.',
  paragraphs: [
    'The copyright symbol began in the print era. It tells readers that a page has an owner. But creators needed more than "all rights reserved." They also needed to say: "You may use this with attribution," or "You may share this but not modify it for commercial sale."',
    'In 2002, Creative Commons (CC) turned that intent into globally recognized markers: BY, NC, ND, SA, and others. People no longer needed to read full legal text to understand what was open or restricted.',
    'That symbol set changed the ecosystem quickly. Flickr enabled CC filtering, Wikipedia adopted open licensing by default, search engines began recognizing license types, and reposting gained a consistent attribution format. Once enough creators use the same symbols, platforms gain enforceable signals before infringement occurs.',
    'Consensus gains power through scale. A single statement on one image is fragile, but when thousands of works carry a shared language, tools, platforms, and users begin to treat that language as a default norm.',
    'In the AI era, a new gap appears: when images are screenshotted, transcoded, or absorbed into training pipelines, adjacent labels can vanish. We need a declaration embedded in pixels, machine-readable, and portable with the image itself. JW continues the same path: visible symbols build consensus, while invisible encoding helps that consensus survive redistribution.',
  ],
}

// Jingwei story (single source to avoid duplicate rendering)

export type JwStoryParagraph = { text: string; lead?: boolean }

export const JW_STORY_ZH: JwStoryParagraph[] = [
  {
    text: 'In Chinese legend, a young girl named Jingwei drowned in the vast East Sea and was reborn as a bird - tiny as a feather, yet unbreakable in will.',
  },
  {
    text: 'She vowed to fill the sea with mountain stones so it could never harm anyone again. Day after day, she carried one stone and cast it into roaring waves.',
  },
  {
    text: 'Today, the sea has changed form. It is now endless data flow: works copied, altered, and redistributed without consent, with attribution erased along the way. Facing this new sea, we may feel as small as Jingwei.',
  },
  {
    text: 'JW is your stone - a watermark and a machine-readable ownership declaration. One stone looks small. But if enough creators keep throwing stones together, this sea can regain boundaries, with room for every creator\'s name.',
    lead: true,
  },
]

/** One-line teaser for meta/cards. Do not render together with full story paragraphs. */
export const JW_STORY_TEASER_ZH = JW_STORY_ZH[0].text

export const JW_STORY = [
  'In Chinese legend, a young girl named Jingwei drowned in the vast East Sea and was reborn as a bird—tiny as a feather, yet unbreakable in will.',
  'She vowed to fill the sea with mountain stones so it could never harm anyone again. Day after day, she carried one stone and cast it into the roaring waves.',
  'Today the sea has changed form. It is now an endless flood of data: works copied, altered, and redistributed without consent, with attribution erased along the way. Facing this new sea, we may feel as small as Jingwei.',
  'JW is your stone—a watermark and a machine-readable ownership declaration. One stone looks small. But if enough creators keep throwing stones together, this sea can regain boundaries, with room for every creator\'s name.',
]

export const JW_STORY_TEASER = JW_STORY[0]

/** @deprecated Use JW_STORY_ZH. */
export const JW_STORY_FULL_ZH = JW_STORY_ZH

/** @deprecated Use JW_STORY_TEASER_ZH, and do not duplicate with JW_STORY_ZH. */
export const JW_STORY_SHORT_ZH = JW_STORY_TEASER_ZH

/** @deprecated Use JW_STORY. */
export const JW_STORY_FULL = JW_STORY

/** @deprecated Use JW_STORY_TEASER. */
export const JW_STORY_SHORT = JW_STORY_TEASER

// Creation type

export type JwCreationType = 'OC' | 'AI'

export const JW_CREATION_OPTIONS: { id: JwCreationType; label: string; labelZh: string; desc: string; descZh: string }[] = [
  {
    id: 'OC',
    label: 'OC - Original Creation',
    labelZh: 'Original Creation',
    desc: 'This work is originally created by the named human creator (any medium).',
    descZh: 'This work is originally created by the named human creator (any medium).',
  },
  {
    id: 'AI',
    label: 'AI - AI-Assisted',
    labelZh: 'AI-Assisted',
    desc: 'AI tools were used in the process; the human creator retains authorship and sets the restrictions.',
    descZh: 'AI tools were used in the process; the human creator retains authorship and sets the restrictions.',
  },
]

// Restriction flags

export const JW_RESTRICTION_FLAGS: {
  id: string
  bit: number
  abbrev: string
  label: string
  labelZh: string
  desc: string
  descZh: string
}[] = [
  {
    id: 'NO-TR',
    bit: 0,
    abbrev: 'NO-TR',
    label: 'No AI Training',
    labelZh: 'No AI Training',
    desc: 'The creator has not authorized this image for AI model training or fine-tuning.',
    descZh: 'The creator has not authorized this image for AI model training or fine-tuning.',
  },
  {
    id: 'NO-ED',
    bit: 1,
    abbrev: 'NO-ED',
    label: 'No AI Edit',
    labelZh: 'No AI Edit',
    desc: 'The creator has not authorized AI-based modification of this image (inpainting, img2img, full redraw, etc.). Human study or imitation is not covered by this flag.',
    descZh: 'The creator has not authorized AI-based modification of this image (inpainting, img2img, full redraw, etc.). Human study or imitation is not covered by this flag.',
  },
]

/** Legacy flag display labels, used for verification of older embedded payloads. */
export const JW_RESTRICTION_LEGACY_LABELS: Record<string, string> = {
  'NO-RM': 'No Watermark Removal (Legacy)',
  'NO-RX': 'No Derivative Works (Legacy)',
  'NO-NC': 'No Commercial Use (Legacy)',
}

/** Returns restriction labels in this English bundle (new + legacy compatible). */
export function jwRestrictionLabel(abbrev: string): string {
  const found = JW_RESTRICTION_FLAGS.find(f => f.abbrev === abbrev)
  if (found) return found.label
  return JW_RESTRICTION_LEGACY_LABELS[abbrev] || abbrev
}

// Intro copy

export const JW_PROTECT_INTRO =
  'Enable the Jingwei Declaration to embed your ownership and usage intent into images, including invisible frequency-domain watermarking and an optional visible badge. The creator name is read from the "Copyright Metadata" section below and written into the manifest and file metadata. PNG export is recommended to preserve invisible watermark layers.'

export const JW_PROTECT_PIXEL_REWARD = {
  title: 'Protect Works to Increase Jingwei Sea Daily Quota',
  bullets: [
    'After login, each image successfully protected with JW declaration counts toward your JW work total.',
    'First activation raises daily claim from 10 to 50 cells.',
    'Each additional protected work adds +5 cells per day, up to 150 cells/day.',
    'Go to Jingwei Sea and click "Claim today\'s quota" to receive it (once per day).',
  ],
  loginHint: 'You can protect images without login, but quota growth is not counted. Please sign in first.',
}

export const JW_PNG_HINT = 'When JW declaration is enabled, PNG format is recommended. JPEG compression may weaken invisible watermark layers.'

/** Protect page Manual mode hint (consistent wording: visible overlay). */
export const JW_STEALTH_MODE_HINT =
  'Turn each visible and invisible layer on yourself and set every parameter. No automatic recipe. Logo position, size, and strength stay under your control.'

// Protection limits

export const JW_PROTECT_LIMITS = {
  title: 'What This Protection Can and Cannot Do',
  paragraphs: [
    'The JW declaration embeds machine-readable ownership and usage intent into your image. Creator name, creation type, and usage preferences are written in the frequency domain with minimal visual impact. It is designed to survive common social compression, screenshots, and light edits so attribution can still be detected after redistribution.',
  ],
  bullets: [
    {
      strong: 'It is not an absolute lock.',
      body: 'Any invisible watermark can be weakened or removed by high-intensity redraw, deep inpainting, or specialized removal tools. We continuously improve robustness but cannot promise 100% persistence.',
    },
    {
      strong: 'If your goal is immediate deterrence,',
      body: 'invisible layers alone are not enough. Switch to Manual and add visible overlays (displacement watermarks, face emboss lock, emboss textures, etc.), especially layers that affect core subject contours, so unauthorized users must pay a high restoration cost.',
    },
  ],
}

export const JW_DWT_RELATION = {
  protectHint:
    'The JW declaration writes invisible data into detail-rich regions while preserving flat-color regions whenever possible; fallback methods are used when needed. PNG export is recommended.',
  verifyJwNote:
    'Frequency-domain ownership data was detected through the JW declaration. This image does not include a standalone DWT tracking layer.',
  verifyStandaloneDwtTitle: 'DWT Frequency Watermark',
  verifyStandaloneDwtHint:
    'A standalone machine-readable tracking-text layer configured separately from the JW declaration ownership manifest.',
}

export type JwImageKind = 'flat' | 'mixed' | 'rich'

export type JwWriteHint = {
  kind: JwImageKind
  flat_ratio: number
  texture_ratio: number
  summary: string
  suggest: string
}

export const JW_INVISIBLE_INTRO =
  'The system automatically writes Jingwei declaration data into areas where changes are harder to notice. For images with large flat color regions, consider adding a bottom white margin and exporting as PNG.'

/** @deprecated API always uses auto; kept for typing legacy responses. */
export type JwEmbedPriority = 'auto' | 'color' | 'balanced' | 'verify'

export const JW_EMBED_METHOD_LABEL: Record<string, string> = {
  invisible: 'Invisible Embedding',
  lsb: 'Fallback Embedding',
}

// Verification limits

export const JW_VERIFY_LIMITS = {
  title: 'How to Read Verification Confidence',
  paragraphs: [
    'This page attempts to extract all Jingwei protection layers from the uploaded image and read C2PA Content Credentials from file metadata when available. Positive detection indicates the image was processed with Jingwei declaration and/or contains verifiable provenance credentials, which can support attribution and ownership claims.',
  ],
  bullets: [
    {
      strong: 'Not detected does not mean never protected.',
      body: 'Strong full-image redraw (for example complete regeneration or deep inpainting) reconstructs pixel content and can remove most invisible watermark traces. We cannot preserve evidence once such operations occur.',
    },
    {
      strong: 'Detected results have different confidence levels.',
      body: 'High-confidence full decode (including checksum) is strongest. Cryptographically signed C2PA evidence is generally stronger than frequency-domain signals. Fuzzy matches are reference-only. In disputes, combine these outputs with metadata, creation records, and original files.',
    },
  ],
}

export const JW_C2PA_NOTE = {
  title: 'C2PA and Jingwei',
  bullets: [
    {
      strong: 'Complementary relationship.',
      body: 'C2PA is stored in metadata and can be stripped during social redistribution. JW is embedded in pixel frequency data. They can coexist and complement each other: prioritize C2PA when present, with JW as fallback evidence.',
    },
    {
      strong: 'Trusted certificates.',
      body: 'To display Content Credentials on Adobe/social platforms, you generally need trusted CA-issued C2PA or CAWG identity certificates. Developer test certificates are useful for internal testing but may not be trusted by public platforms.',
    },
  ],
}

// Core belief

export const JW_CORE_BELIEF = {
  title: 'Why It Is Still Worth Embedding the Jingwei Declaration',
  paragraphs: [
    'Invisible watermarks are not indestructible locks. AI redraw, deep inpainting, heavy compression, and removal tools can weaken or erase them. Invisible layers alone cannot guarantee persistence across every redistribution and secondary edit, which is why we recommend adding visible declaration layers.',
    'The deeper goal of Jingwei is a unified machine-readable creator declaration standard. If "no AI training" and "no AI editing" exist only in profile text or plain image captions, they are hard for platforms and models to detect and enforce at scale. We hope Jingwei symbols can become as recognizable as CC markers, eventually accepted by platforms, search engines, and AI systems as a readable and enforceable public signal.',
    'Jingwei declaration is our first stone thrown into the sea.',
  ],
}

/** Protect/Verify page summary; full version lives on /protocol. */
export const JW_CORE_BELIEF_SUMMARY = {
  title: 'Why It Is Still Worth Embedding the Jingwei Declaration',
  paragraphs: [
    'Invisible watermarks are not indestructible locks. AI redraw, deep inpainting, heavy compression, and removal tools can weaken or erase them. Invisible layers alone cannot guarantee persistence across every redistribution and secondary edit, which is why we recommend adding visible declaration layers.',
    'The deeper goal of Jingwei is a unified machine-readable creator declaration standard. If "no AI training" and "no AI editing" exist only in profile text or plain image captions, they are hard for platforms and models to detect and enforce at scale. We hope Jingwei symbols can become as recognizable as CC markers, eventually accepted by platforms, search engines, and AI systems as a readable and enforceable public signal.',
    'Jingwei declaration is our first stone thrown into the sea.',
  ],
  linkLabel: 'Read the full Jingwei declaration ->',
  linkTo: '/protocol',
}

// Tool commitments

export const JW_TOOL_PROMISE = {
  title: 'Our Tool Uses No AI Models',
  paragraphs: [
    'All watermarks in this tool - invisible frequency-domain marks (DWT / DCT / Block-DC), visible badges, displacement effects, and face emboss overlays - are implemented with classical digital signal processing only, with no AI inference dependency.',
    'Your image is uploaded from your browser and is used by our server only to embed watermark data and return results immediately.',
    'We never place your works into any AI training set, generative model, or machine-learning dataset - neither for ourselves nor any third party.',
    'Our role is simply to help you write a machine-readable statement of ownership into your work. How it may be used, and whether AI can learn from it, remains your decision.',
  ],
}

// Angie letters (three styles)

export type LetterStyle = 'narrative' | 'declaration' | 'poetic'

export interface JwLetter {
  id: LetterStyle
  styleLabel: string
  title: string
  paragraphs: string[]
  signature: string
}

export const JW_LETTER_VERSIONS: JwLetter[] = [
  {
    id: 'narrative',
    styleLabel: 'Narrative · Warm',
    title: 'A Final Note for You',
    paragraphs: [
      'I am Angie.',
      'When I started building Jingwei, I was not trying to fight anyone. I also use AI - for coding, organizing ideas, and even companionship.',
      'One day, I watched a friend\'s artwork get altered with AI: hairstyle changed, expression replaced, signature removed, reposted on another platform, then accused of "copying AI." She had spent three weeks on that piece.',
      'That moment made one thing clear to me: technology can move fast, but the sentence "someone spent real time making this" should not disappear on the way.',
      'The Jingwei declaration does something small. It leaves one machine-readable line in each image: "This is human-made. Please identify and respect it." It cannot stop everything, and it cannot defeat every aggressive restoration pipeline. It simply gives that sentence a chance to be heard.',
      'If you are willing to place it in your next work, I will treat that as another stone thrown together.',
      'No sea is ever fully filled. But every stone makes it retreat just a little.',
    ],
    signature: '- Angie, 2026, late night after a long reflection',
  },
  {
    id: 'declaration',
    styleLabel: 'Calm · Declaration',
    title: 'To Everyone Reading This',
    paragraphs: [
      'I built Jingwei not to oppose anyone.',
      'I recognize AI as one of the rare technologies that truly changed how everyone works, including me.',
      'But one thing should remain remembered: behind each image, paragraph, or song is a specific person who spent specific time creating it.',
      'The Jingwei declaration does one small thing: it leaves a machine-readable sentence in each image, "This is human creation. Please identify and respect it."',
      'It cannot block everything. But when enough images carry this sentence, nobody - including AI systems - can keep pretending they did not see it.',
      'One stone is small. Stone by stone, the sea remembers.',
    ],
    signature: '- Angie, 2026',
  },
  {
    id: 'poetic',
    styleLabel: 'Poetic · Metaphor',
    title: 'Stones',
    paragraphs: [
      'I often think of that bird.',
      'She never expected to defeat the sea. Each day, she carried one stone, flew over the water, released it, watched it fall, then turned back.',
      'I think she knew the sea could never be fully filled. What she practiced was not calculation. It was persistence - a posture of "I was here, I saw this, and I do not consent."',
      'Today\'s sea changed shape, but the sea remains the sea. Our time, choices, and intent are washed away, collected without asking, and regenerated elsewhere under different names.',
      'The Jingwei declaration is the closest thing I can build to that stone. It will not empty the sea, and it will not stop AI. It only writes your name into your work a little deeper, deep enough that the next wave is less likely to erase it.',
      'If you are willing to carry this stone too, we may never fill the sea, but every stone teaches the sea one more human name.',
    ],
    signature: '- Angie, a sleepless night in 2026',
  },
]

/** Letter version used on protocol page. */
export const JW_ACTIVE_LETTER_ID: LetterStyle = 'narrative'

export function getActiveLetter(): JwLetter {
  return JW_LETTER_VERSIONS.find(v => v.id === JW_ACTIVE_LETTER_ID) ?? JW_LETTER_VERSIONS[0]
}

// Badge string preview

/** Example badge strings (logo + abbrev placeholders, bottom-right). */
export function formatBadgePreview(creation: JwCreationType, restrictions: string[]): string {
  const parts = ['JW', creation, ...restrictions.slice(0, 3)]
  return parts.join(' · ')
}
