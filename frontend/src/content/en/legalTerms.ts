/** Legal terms - consent summary + /terms full text (single source). */

export const LEGAL_CONSENT_SESSION_KEY = 'jw-legal-consent-session'

export const LEGAL_TERMS_TITLE =
  '"Jingwei" User Service Agreement, Privacy Protection, and Disclaimer'
export const LEGAL_TERMS_UPDATED = 'Last updated: June 2026'
export const LEGAL_TERMS_DATE_MODIFIED = '2026-06-14'
export const LEGAL_TERMS_LINK_LABEL = 'Terms & Disclaimer'
export const LEGAL_PRIVACY_LINK_LABEL = 'Privacy Policy'
export const LEGAL_TERMS_PRIVACY_LINK_LABEL = 'Privacy Policy (Data Handling Details)'
export const LEGAL_TERMS_PROTOCOL_LINK_LABEL = 'JW Declaration (Product Overview)'
export const LEGAL_TERMS_FINAL_CONFIRMATION_TITLE = 'Final Confirmation'
export const LEGAL_TERMS_CONTACT_PREFIX = 'If you have questions, contact:'

/** Four required summary items in the consent modal. */
export const LEGAL_CONSENT_SUMMARY: { title: string; body: string }[] = [
  {
    title: 'Copyright',
    body: 'You may only upload works you created yourself or are legally authorized to use. Infringement disputes are the uploader\'s sole responsibility. The platform provides technical processing only.',
  },
  {
    title: 'Privacy',
    body: 'Images are processed temporarily on the server and deleted immediately after completion. They are never used for AI training. See the privacy policy for details.',
  },
  {
    title: 'Non-AI',
    body: 'All watermark embedding uses classical digital signal processing. This tool does not use any AI model.',
  },
  {
    title: 'Technical Limits',
    body: 'Invisible watermarks are not guaranteed to survive in all cases. AI redraw, deep inpainting, or professional watermark removal may weaken or erase them.',
  },
]

export const LEGAL_TERMS_INTRO = [
  'Welcome to Jingwei (the "Tool" or "Platform"). This statement is a legally binding agreement between you (the "User") and the developers of this tool regarding your use of image protection services.',
  'Before uploading any artwork or using the tool, please read and fully understand all terms in this statement. By checking consent or starting to use the tool, you acknowledge that you have fully read, understood, and accepted all terms without reservation. These terms apply globally to all users who access and use the tool.',
]

export interface LegalTermsSection {
  title: string
  intro?: string
  bullets?: string[]
  paragraphs?: string[]
}

export const LEGAL_TERMS_SECTIONS: LegalTermsSection[] = [
  {
    title: 'Article 1: User Content and Copyright Commitments (Full Disclaimer)',
    intro:
      'This tool provides only technical image processing services and performs no substantive manual or automated copyright review of uploaded content. By using the tool, users make the following irrevocable commitments:',
    bullets: [
      'Absolute originality and legality: The user represents and warrants that all works uploaded are either fully original creations by the user or used with lawful, complete, and sufficient prior authorization.',
      'Non-infringement commitment: The user guarantees uploaded works do not infringe any third-party legal rights, including but not limited to copyright, trademark, patent, portrait rights, reputation, and privacy.',
      'User bears disputes; platform disclaimer: If uploaded content directly or indirectly causes copyright disputes, infringement claims, or other legal conflicts, all legal liabilities and related compensation are borne solely by the uploader, with no relation to the Jingwei platform or developers. Upon receiving lawful rights-protection requests, the platform may suspend service and cooperate with relevant authorities.',
    ],
  },
  {
    title: 'Article 2: Technical Purity and Explicit Non-AI Statement',
    intro:
      'To address creators\' concerns about misuse of their data, this tool makes the following highest-level transparency commitments in architecture and operation:',
    bullets: [
      'Pure classical digital signal processing: This tool does not use any AI model (Artificial Intelligence Models). All watermark embedding and protection mechanisms rely on classical digital signal processing, including but not limited to DWT, DCT, frequency-domain analysis, and spatial-shift algorithms.',
      'Data isolation and zero training use: Uploaded images are used only for watermark computation and embedding, then returned as processing results. Your artwork is never sent to AI training sets, generative models, or any machine-learning workflow.',
      'No third-party sharing: Under no circumstance or commercial consideration will the tool provide, sell, or share your source artwork files or processed outputs with any third-party organization or individual.',
    ],
  },
  {
    title: 'Article 3: Core Image Data and Privacy Protection',
    intro:
      'This tool follows a "minimum processing" principle and applies strict controls to image lifecycle and privacy handling:',
    bullets: [
      'Ultra-short retention with irreversible deletion: Uploaded images remain in server memory and temporary queues only for a few seconds. Once processing is completed and results are returned to the frontend, the system immediately performs irreversible deletion from server disks and all caches.',
      'Absolute zero long-term storage: The platform does not retain original uploads long term and does not retain processed watermarked outputs. We do not maintain any cloud artwork repository or archival history of user works.',
      'Basic network data collection (supplementary): To maintain normal service operation, mitigate malicious attacks (such as DDoS), and measure basic availability, the backend may collect routine operational logs, including IP address, browser type/version, operating-system indicators, access timestamps, and runtime cookies. These data are used only for security/risk control and internal troubleshooting, are not tied to specific image processing tasks, and are never used for commercial marketing or cross-domain tracking. See the Privacy Policy for complete details.',
    ],
  },
  {
    title: 'Article 4: Technical Limitations and Protection-Effect Disclaimer',
    intro:
      'This tool is designed to help creators resist unauthorized AI use and image fusion. As a technology provider, we must objectively state current technical boundaries:',
    bullets: [
      'Not an absolute lock: Invisible watermarks and protective measures are not a 100% guaranteed "universal lock."',
      'Adversarial weakening risk: Under high-intensity redraw (img2img), deep inpainting, extreme compression, targeted professional watermark-removal tools, or rewrite attacks, invisible watermark signals may still be substantially weakened or fully removed.',
      'No 100% persistence guarantee: The development team will continue improving robustness, but in modern image-processing and AI-generation environments, the platform cannot and does not guarantee 100% persistence or interception rates. If watermark signals are maliciously removed and subsequent infringement occurs, the tool does not bear direct or indirect compensation liability.',
    ],
  },
]

export const LEGAL_TERMS_CONFIRMATION =
  'I have carefully read the "Jingwei" User Service Agreement, Privacy Protection, and Disclaimer above. I fully understand and accept all terms regarding sole copyright responsibility, non-100% technical protection, and data-handling rules. I commit to using this tool lawfully and in compliance with regulations.'
