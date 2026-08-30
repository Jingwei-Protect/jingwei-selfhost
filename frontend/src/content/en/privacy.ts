import { CONTACT_EMAIL } from '../../lib/site'
import type { PrivacySection, PrivacySectionBody } from '../privacy'

export type { PrivacySection, PrivacySectionBody }

export const PRIVACY_TITLE = 'Privacy Policy'
export const PRIVACY_UPDATED = 'Last updated: June 2026'
export const PRIVACY_DATE_MODIFIED = '2026-06-14'

export const PRIVACY_SECTIONS: PrivacySection[] = [
  {
    id: 'relation',
    title: 'Relationship to Legal Terms',
    body: {
      type: 'termsLink',
      before:
        'This page explains how we process your data. For full legal terms on copyright commitments, technical limitations, and the non-AI statement, please read',
      linkLabel: 'User Service and Disclaimer',
      linkTo: '/terms',
      after: '.',
    },
  },
  {
    id: 'summary',
    title: 'One-Sentence Summary',
    paragraphs: [
      'Images you upload for Protect / Verify / Inspection remain only for a few seconds in server memory during processing, and are deleted from disk immediately after completion. They are not archived, not retained as a gallery, and not used for any model training. If you use account features and community features such as Jingwei Sea, we keep your account profile and publicly created community content until you delete them.',
    ],
  },
  {
    id: 'controller',
    title: 'Data Controller and Storage Location',
    paragraphs: [
      'This service is operated by the Jingwei team, which acts as the controller of your personal information. Our servers are hosted in Hong Kong. For users in mainland China, data storage and processing occur outside mainland China (Hong Kong), which constitutes cross-border processing. By using this service, you acknowledge and agree to this arrangement. If you have questions, please contact us using the email at the bottom of this page.',
    ],
  },
  {
    id: 'collect',
    title: 'What We Collect',
    bullets: [
      'Account profile: email, password (stored as PBKDF2-SHA256 hash; plaintext is never stored), nickname/username (for public display on the site).',
      'Support records: order ID, amount, and raw callback payload returned by Stripe, used to grant and reconcile quotas.',
      'Community creations: Jingwei Sea pixels, artwork archives (draft/final), and thank-wall nameplate images, all linked to your account and retained until you delete them.',
      'Messages and feedback: feedback title, content, optional contact email, and optional screenshot filename that you voluntarily submit.',
      'Site visit statistics: the home page shows aggregate total visits (anonymous aggregate numbers only; no identification of individual visitors; not linked to accounts or uploaded images; no separate IP logging or cookie usage for this statistic).',
      'Network logs: to prevent abuse and troubleshoot issues, server access logs may record request IP, timestamp, and endpoint, retained for up to 30 days then automatically deleted.',
      'Uploaded images: used only to complete your current Protect / Verify / Inspection request, then deleted immediately and not retained.',
    ],
  },
  {
    id: 'not',
    title: 'What We Do Not Do',
    bullets: [
      'We do not keep long-term copies of original uploads, processed outputs, or comparison images used for Protect/Verify/Inspection.',
      'We do not use your artworks or images for any AI model training.',
      'We do not sell or provide your artworks or account data to any third party (except lawful requests by law enforcement authorities).',
      'We do not embed third-party tracking or advertising scripts on webpages; fonts are self-hosted and do not call external CDNs such as Google.',
    ],
  },
  {
    id: 'retention',
    title: 'Data Retention and Deletion',
    bullets: [
      'Uploaded images: deleted immediately after processing; not retained.',
      'Network logs (including IP): retained for up to 30 days and then automatically deleted.',
      'Accounts and community content: retained until you actively delete them.',
      'Account cancellation means complete deletion: when you delete your account, we permanently remove your account profile, nameplate, Jingwei Sea pixels and archives, feedback records, and claimed sponsorship order records, without retaining or anonymizing copies.',
    ],
  },
  {
    id: 'third',
    title: 'Third Parties',
    bullets: [
      'Stripe: when support occurs, Stripe pushes order webhooks to us, including order ID and amount.',
    ],
  },
  {
    id: 'minors',
    title: 'Minors',
    paragraphs: [
      'This service is intended for adult creators. If you are under 14, please use the service only with guardian consent and guidance. We do not knowingly collect personal information from children under 14. If a guardian discovers such information, please contact us via the email on this page for deletion.',
    ],
  },
  {
    id: 'rights',
    title: 'Your Rights',
    paragraphs: [
      'You may access, correct, or delete your personal information at any time. You may also delete your account to remove all associated data described above. To exercise these rights, please contact us via the email at the bottom of this page.',
    ],
  },
  {
    id: 'contact',
    title: 'Contact',
    body: {
      type: 'contact',
      before: 'If you have questions about this policy or our data processing practices, contact:',
      email: CONTACT_EMAIL,
    },
  },
]
